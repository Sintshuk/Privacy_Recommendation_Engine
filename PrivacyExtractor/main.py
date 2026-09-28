"""
MAIN - the single entry point for extraction.

    python3 main.py                    -> runs every file in policies/
    python3 main.py policies/tesla.pdf -> runs just that one file

Each policy writes its own file the moment it finishes:

    output/policies/<PolicyName>.json

At the START of each policy, if that file already exists, the policy
is skipped - so a batch run is idempotent. Interrupt it, fix
something, rerun the exact same command, and it picks up where it
stopped. There is no separate checkpoint file: the per-policy files
ARE the checkpoint, always current.

After EVERY policy (not just at the end), the combined output, the
HTML report, and the clean exports are all rebuilt from whatever
per-policy files exist on disk. This is cheap - a fraction of a
second - so there's no cost to doing it after each one instead of
only once at the end, and it means every file under output/ is never
more than one policy stale, crash or no crash.

To reprocess a policy that already has output, delete its file under
output/policies/ (or the whole folder, to redo everything) and rerun.
"""

from __future__ import annotations

import json
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import time

from extractor.prompt import MODEL
from extractor.pipeline import extract_rights
from extractor.cross_segment import resolve_cross_segment_channels
from extractor.segmenter import segment_policy_file
from extractor.report import generate_combined_report
from export.export_clean import export_all


POLICIES_FOLDER = Path("policies")
OUTPUT_FOLDER = Path("output")
PER_POLICY_FOLDER = OUTPUT_FOLDER / "policies"

# No version number in these names. Every file under OUTPUT_FOLDER is
# rebuilt from scratch after each policy, so it's always the current,
# complete state of the corpus - never a stale snapshot a "_v3" would
# imply.
CORPUS_NAME = "ipn101"
ARCHITECTURE = "docling_multi_format_v1"

MAX_WORKERS_PER_POLICY = 1
SUPPORTED_SUFFIXES = {".html", ".htm", ".pdf"}


# --------------------------------------------------------------------
# Discovery and naming
# --------------------------------------------------------------------

def discover_policies() -> list[Path]:
    """Every supported file in policies/, in a stable order."""
    return sorted(p for p in POLICIES_FOLDER.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)


def policy_name_from_path(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").strip().title()


def result_has_content(result: dict | None) -> bool:
    if not result:
        return False
    return any([
        result.get("right_type", []),
        result.get("choice_type", []),
        result.get("request_channel", []),
        result.get("references", []),
        result.get("rejected", []),
    ])


# --------------------------------------------------------------------
# The single-policy unit of work
# --------------------------------------------------------------------

def build_segments_with_context(segments: list[dict]) -> list[dict]:
    """Attaches previous-segment text and a short lookback window to every segment, for the rights-framing check."""
    prepared = []
    for index, segment in enumerate(segments):
        segment = dict(segment)
        segment["previous_segment_text"] = segments[index - 1].get("text", "") if index > 0 else ""
        lookback = segments[max(0, index - 3):index]
        segment["extended_context"] = " ".join(s.get("text", "") for s in lookback)
        prepared.append(segment)
    return prepared


def run_one_policy(path: Path, policy_name: str | None = None) -> list[dict]:
    """
    Segments and extracts a single policy. This is the real unit of
    work - run_batch() is just a loop that calls this once per file.

    Concurrency is WITHIN this policy only, across its segments.
    Policies run one after another in run_batch(), not against each
    other, to keep rate-limit behaviour simple to reason about.
    """
    policy_name = policy_name or policy_name_from_path(path)

    raw_segments = segment_policy_file(str(path))
    segments = build_segments_with_context(raw_segments)
    print(f"{policy_name}: {len(segments)} segments")

    rows: list[dict | None] = [None] * len(segments)

    def work(index_and_segment: tuple[int, dict]) -> None:
        index, segment = index_and_segment
        result = extract_rights(segment=segment, policy_name=policy_name)

        if result is None:
            raise RuntimeError(f"{segment['id']} returned no result")

        rows[index] = {"segment": segment, "result": result}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_PER_POLICY) as pool:
        list(pool.map(work, enumerate(segments)))

    completed = [row for row in rows if row is not None]
    triggered = sum(1 for row in completed if result_has_content(row["result"]))
    print(f"  {triggered}/{len(completed)} segments contained rights/choices info")

    return resolve_cross_segment_channels(completed)


# --------------------------------------------------------------------
# Per-policy persistence (this is the checkpoint mechanism)
# --------------------------------------------------------------------

def per_policy_output_path(policy_name: str) -> Path:
    return PER_POLICY_FOLDER / f"{policy_name.replace(' ', '_')}.json"


def write_policy_output(policy_name: str, rows: list[dict]) -> None:
    payload = {"policy": policy_name, "rows": rows}
    per_policy_output_path(policy_name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def load_completed_policies() -> dict[str, list[dict]]:
    """Reads every per-policy file already on disk - this is what makes a rerun skip finished work."""
    results: dict[str, list[dict]] = {}
    if not PER_POLICY_FOLDER.exists():
        return results
    for path in PER_POLICY_FOLDER.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        results[data["policy"]] = data["rows"]
    return results


# --------------------------------------------------------------------
# Combined output - rebuilt from disk after every policy
# --------------------------------------------------------------------

def rebuild_combined_outputs(all_results: dict[str, list[dict]]) -> None:
    """Rebuilds the combined JSON, HTML report, and clean exports from whatever has completed so far."""
    metadata = {
        "model": MODEL,
        "temperature": 0.0,
        "architecture": ARCHITECTURE,
        "run_updated_utc": datetime.now(timezone.utc).isoformat(),
        "policies_completed": sorted(all_results.keys()),
    }
    items = [
        {"policy": name, "segment": row["segment"], "result": row["result"]}
        for name, rows in all_results.items() for row in rows
    ]
    combined = {"metadata": metadata, "items": items}

    json_path = OUTPUT_FOLDER / f"{CORPUS_NAME}_extractions.json"
    json_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = OUTPUT_FOLDER / f"{CORPUS_NAME}_report.html"
    generate_combined_report(all_results=all_results, output_path=str(report_path), run_metadata=metadata)

    export_all(combined, OUTPUT_FOLDER / f"{CORPUS_NAME}_extractions")


# --------------------------------------------------------------------
# Batch entry point
# --------------------------------------------------------------------

def run_batch() -> None:
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    PER_POLICY_FOLDER.mkdir(parents=True, exist_ok=True)

    policy_files = discover_policies()
    print(f"found {len(policy_files)} policy files in {POLICIES_FOLDER}/")

    all_results = load_completed_policies()
    if all_results:
        print(f"{len(all_results)} already completed, will be skipped: {sorted(all_results.keys())}")

    failed: list[str] = []

    for position, path in enumerate(policy_files, start=1):
        policy_name = policy_name_from_path(path)

        if policy_name in all_results:
            continue

        print(f"\n[{position}/{len(policy_files)}] {policy_name}")

        try:
            rows = run_one_policy(path, policy_name)
            write_policy_output(policy_name, rows)
            all_results[policy_name] = rows
        except Exception:
            print(f"  SKIPPED - {policy_name} failed:", file=sys.stderr)
            traceback.print_exc()
            failed.append(policy_name)
            continue

        rebuild_combined_outputs(all_results)

    print(f"\ndone: {len(all_results)} completed, {len(failed)} failed")
    if failed:
        print("failed:", ", ".join(failed))
    print(f"combined output: {OUTPUT_FOLDER}/{CORPUS_NAME}_extractions.json")
    print(f"clean exports:   {OUTPUT_FOLDER}/{CORPUS_NAME}_extractions_clean.json / .csv / .xlsx")
    print(f"report:          {OUTPUT_FOLDER}/{CORPUS_NAME}_report.html")


def run_single(path: Path) -> None:
    """CLI path for `python main.py <file>` - runs one policy and writes just its own outputs, no combined rebuild."""
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    policy_name = policy_name_from_path(path)

    rows = run_one_policy(path, policy_name)

    report_path = OUTPUT_FOLDER / f"{policy_name.replace(' ', '_')}_report.html"
    generate_combined_report(
        all_results={policy_name: rows},
        output_path=str(report_path),
        run_metadata={"model": MODEL, "temperature": 0.0, "architecture": ARCHITECTURE},
    )

    json_path = OUTPUT_FOLDER / f"{policy_name.replace(' ', '_')}_extractions.json"
    payload = {"metadata": {"model": MODEL}, "items": [{"policy": policy_name, "segment": r["segment"], "result": r["result"]} for r in rows]}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    export_all(payload, OUTPUT_FOLDER / f"{policy_name.replace(' ', '_')}_extractions")

    print(f"\nreport: {report_path}")
    print(f"json:   {json_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single(Path(sys.argv[1]))
    else:
        run_batch()