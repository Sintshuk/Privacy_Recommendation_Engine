from __future__ import annotations

import argparse
import json
from pathlib import Path

from candidate_generator import build_candidates
from scoring import recommend_for_persona


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "Data"
DEFAULT_EXTRACTIONS = DATA_DIR / "ipn101_extractions_clean.json"

REPORT_CACHE_PATH = HERE / "report_cache.json"
REPORT_HTML_PATH = HERE / "recommendations_demo.html"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy_blocks(path: Path, policy_name: str) -> list[dict]:
    blocks = load_json(path)
    return [
        block for block in blocks
        if str(block.get("policy", "")).lower() == policy_name.lower()
    ]


def list_policies(path: Path) -> list[str]:
    return sorted({
        block.get("policy")
        for block in load_json(path)
        if block.get("policy")
    })


def get_persona(personas: dict, name: str) -> dict:
    for persona in personas["personas"].values():
        if persona["name"].lower() == name.lower():
            return persona
    available = ", ".join(p["name"] for p in personas["personas"].values())
    raise ValueError(f"Unknown persona: {name}. Available: {available}")


def print_candidate(item: dict, index: int, explain: bool = False) -> None:
    print(f"{index}. {item['title']}")
    print(f"   utility: {item['utility']:.2f}/100")
    print(f"   mapping confidence: {item['mapping_confidence']}")
    print(f"   actionability: {item['actionability']}")
    print(f"   policy support: {item['policy_support']} ({item['evidence_count']} evidence item(s))")

    if item.get("channels"):
        print("   how to act:")
        for channel in item["channels"]:
            detail = channel.get("email") or channel.get("label") or channel.get("evidence")
            print(f"      - {channel.get('type') or 'Action'}: {detail}")
            if channel.get("url"):
                print(f"        link: {channel['url']}")

    if item.get("evidence"):
        print(f"   policy evidence: {item['evidence'][0]['text']}")

    if explain:
        dims = item["persona_dimensions"]
        print(
            "   persona dimensions: "
            f"action={dims['action_intent']:.3f}, "
            f"guidance={dims['guidance_need']:.3f}, "
            f"sensitivity={dims['privacy_sensitivity']:.3f}"
        )
        profile = item["item_dimension_profile"]
        print(
            "   item profile: "
            f"action={profile.get('action_intent', 0):.3f}, "
            f"guidance={profile.get('guidance_need', 0):.3f}, "
            f"sensitivity={profile.get('privacy_sensitivity', 0):.3f}"
        )
        print(f"   structural fit: {item['structural_fit']:.3f}")
        if item["persona_relevance"] is None:
            print("   item-specific alignment: neutral baseline (no direct 33-question mapping)")
        else:
            print(f"   item-specific alignment: {item['persona_relevance']:+.3f}")

        used = [s for s in item.get("survey_signals", []) if s["used_in_alignment"]]
        if used:
            print("   mapped survey signals:")
            for signal in used:
                print(
                    f"      - {signal['question']} ({signal['domain']}): "
                    f"z={signal['z']:+.3f}, direction={signal['direction']}, "
                    f"strength={signal['strength']}, contribution={signal['contribution']:+.3f}"
                )
    print()


def run_one(policy, persona, blocks, catalog, mapping, config, top, explain):
    candidates = build_candidates(blocks, catalog)
    results = recommend_for_persona(
        candidates,
        persona,
        mapping,
        config,
        top_n=top,
    )

    print("\n" + "=" * 72)
    print(f"{policy} -> {persona['name']}")
    print("=" * 72)

    dims = results["persona_dimensions"]
    print(
        "Persona profile: "
        f"Action intent={dims['action_intent']:.3f} | "
        f"Guidance need={dims['guidance_need']:.3f} | "
        f"Privacy sensitivity={dims['privacy_sensitivity']:.3f}\n"
    )

    print("TOP POLICY-SUPPORTED RECOMMENDATIONS")
    print("-" * 72)
    if not results["recommended"]:
        print("No policy-supported candidates found.\n")
        return results

    for index, item in enumerate(results["recommended"], 1):
        print_candidate(item, index, explain)

    if explain:
        remaining = [
            item for item in results["all_ranked"]
            if item["recommendation_id"] not in {
                x["recommendation_id"] for x in results["recommended"]
            }
        ]
        if remaining:
            print("OTHER POLICY-SUPPORTED OPTIONS")
            print("-" * 72)
            for index, item in enumerate(remaining, 1):
                print_candidate(item, index, False)

    return results


def process_policy(policy_name, args, personas, catalog, mapping, config):
    blocks = load_policy_blocks(args.extractions, policy_name)
    if not blocks:
        print(f"skipping {policy_name!r} - no extractor output found")
        return

    if args.all:
        selected = list(personas["personas"].values())
    elif args.persona:
        selected = [get_persona(personas, args.persona)]
    else:
        raise SystemExit("Provide a persona name or use --all")

    persona_results = {}
    for persona in selected:
        result = run_one(policy_name, persona, blocks, catalog, mapping, config, args.top, args.explain)
        if result is not None:
            persona_results[persona["name"]] = result

    if persona_results:
        from report import generate_html_report

        cache = {}
        if REPORT_CACHE_PATH.exists():
            cache = load_json(REPORT_CACHE_PATH)

        cache[policy_name] = persona_results
        REPORT_CACHE_PATH.write_text(json.dumps(cache, default=str), encoding="utf-8")

        generate_html_report(cache, REPORT_HTML_PATH)


def main() -> None:
    parser = argparse.ArgumentParser(description="33-question hierarchical utility privacy recommender")
    parser.add_argument("policy", nargs="?")
    parser.add_argument("persona", nargs="?")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--all-policies", action="store_true", help="Run every real policy in the catalog, not just one")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--top", type=int, default=6)
    parser.add_argument("--list-policies", action="store_true")
    parser.add_argument("--extractions", type=Path, default=DEFAULT_EXTRACTIONS)
    args = parser.parse_args()

    if args.list_policies:
        for policy in list_policies(args.extractions):
            print(policy)
        return

    personas = load_json(DATA_DIR / "persona_question_scores.json")
    catalog = load_json(DATA_DIR / "recommendation_catalog.json")
    mapping = load_json(DATA_DIR / "survey_mapping.json")
    config = load_json(DATA_DIR / "scoring_config.json")

    if args.all_policies:
        all_names = list_policies(args.extractions)
        print(f"Running {len(all_names)} policies...\n")
        for policy_name in all_names:
            process_policy(policy_name, args, personas, catalog, mapping, config)
        return

    if not args.policy:
        raise SystemExit("Provide a policy name, use --all-policies, or use --list-policies")

    process_policy(args.policy, args, personas, catalog, mapping, config)


if __name__ == "__main__":
    main()