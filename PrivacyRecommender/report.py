from __future__ import annotations

import html
import json
from pathlib import Path

from candidate_generator import build_candidates
from scoring import recommend_for_persona, merge_config

CONFIDENCE_PLAIN = {
    "high": ("Strong match", "Backed by clear, specific survey evidence for this exact recommendation."),
    "medium": ("Good match", "Backed by relevant survey evidence for this recommendation."),
    "low": ("Possible match", "Backed by partial or indirect survey evidence."),
    "baseline": ("General fit", "No specific survey question covers this exact item - based on this persona's overall privacy profile instead."),
}

DIMENSION_PLAIN = {
    "action_intent": "Takes privacy action",
    "guidance_need": "Needs more guidance",
    "privacy_sensitivity": "Sensitive to privacy risks",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def safe_id(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)


def render_dimension_bars(dimensions: dict) -> str:
    bars = []
    for key, label in DIMENSION_PLAIN.items():
        pct = round(dimensions.get(key, 0.5) * 100)
        bars.append(f"""
        <div class="dim-row">
            <span class="dim-label">{html.escape(label)}</span>
            <div class="dim-track"><div class="dim-fill" style="width:{pct}%;"></div></div>
        </div>
        """)
    return "".join(bars)


def render_recommendation_card(item: dict, rank: int, panel_id: str) -> tuple[str, str]:
    conf_label, conf_desc = CONFIDENCE_PLAIN.get(item["mapping_confidence"], ("General fit", ""))
    conf_class = f"conf-{item['mapping_confidence']}"

    evidence_html = "".join(
        f'<div class="evidence-quote">&ldquo;{html.escape(e["text"])}&rdquo;</div>'
        for e in item.get("evidence", [])[:1]
    )

    channel_html = ""
    for c in item.get("channels", []):
        parts = [html.escape(c.get("type") or "")]
        if c.get("email"):
            parts.append(html.escape(c["email"]))
        if c.get("url"):
            parts.append(f'<a href="{html.escape(c["url"])}" target="_blank" rel="noopener">link</a>')
        if not c.get("email") and not c.get("url") and c.get("evidence"):
            parts.append(html.escape(c["evidence"]))
        channel_html += f'<div class="channel-line">{" &middot; ".join(p for p in parts if p)}</div>'
    card = f"""
    <div class="rec-card">
        <div class="rec-rank">{rank}</div>
        <div class="rec-body">
            <div class="rec-title">{html.escape(item['title'])}</div>
            <span class="conf-badge {conf_class}">{html.escape(conf_label)}</span>
            {evidence_html}
            {channel_html}
            <button class="details-toggle" onclick="toggleDetail('{panel_id}')">Show scoring details</button>
        </div>
    </div>
    """

    domain_rows = "".join(
        f'<tr><td>{html.escape(d)}</td><td>{v:+.3f}</td></tr>'
        for d, v in item.get("domain_scores", {}).items()
    )
    signal_rows = "".join(f"""
        <div class="signal-row">
            <b>{html.escape(s.get('question',''))}</b> ({html.escape(s.get('strength',''))})
            &rarr; z={s.get('z',0):+.3f}, contribution {s.get('contribution', 0):+.3f}
            <div class="signal-reason">{html.escape(s.get('reason',''))}</div>
        </div>
        """ for s in item.get("survey_signals", []))

    panel = f"""
    <div class="detail-panel" id="{panel_id}" style="display:none;">
        <p class="detail-label">Why this confidence level</p>
        <p class="detail-text">{html.escape(conf_desc)}</p>
        <p class="detail-label">Utility score (internal ranking number)</p>
        <p class="detail-text">{item['utility']:.1f} / 100</p>
        {"<p class='detail-label'>Matched survey questions</p>" + signal_rows if signal_rows else ""}
        {"<p class='detail-label'>Domain scores</p><table class='domain-table'><tbody>" + domain_rows + "</tbody></table>" if domain_rows else ""}
    </div>
    """
    return card, panel


def build_report_data(data_dir: Path, catalog_path: Path) -> dict:
    catalog = load_json(data_dir / "recommendation_catalog.json")
    survey_mapping = load_json(data_dir / "survey_mapping.json")
    config = merge_config(load_json(data_dir / "scoring_config.json"))
    personas = load_json(data_dir / "persona_question_scores.json")["personas"]

    all_blocks = load_json(catalog_path)
    policy_names = sorted({b["policy"] for b in all_blocks})

    report = {}
    for policy_name in policy_names:
        blocks = [b for b in all_blocks if b["policy"] == policy_name]
        candidates = build_candidates(blocks, catalog)
        if not candidates:
            continue
        report[policy_name] = {}
        for pid, persona in personas.items():
            result = recommend_for_persona(candidates, persona, survey_mapping, config, top_n=6)
            report[policy_name][persona["name"]] = result

    return report


def generate_html_report(report_data: dict, output_path: Path) -> None:
    """Full multi-policy report with a policy dropdown - used by running
    this file directly (python3 report.py), across every policy in the
    catalog. For a single policy from recommender.py, see
    generate_single_policy_html below instead."""
    policy_names = sorted(report_data.keys())
    first_policy = policy_names[0]

    policy_options = "".join(
        f'<option value="{html.escape(safe_id(p))}">{html.escape(p)}</option>' for p in policy_names
    )

    sections = []
    for policy_name in policy_names:
        policy_id = safe_id(policy_name)
        persona_names = sorted(report_data[policy_name].keys())

        tabs = []
        panels = []
        for i, persona_name in enumerate(persona_names):
            persona_id = safe_id(persona_name)
            result = report_data[policy_name][persona_name]
            display = "block" if i == 0 else "none"

            tabs.append(
                f'<button class="persona-tab" onclick="showPersona(\'{html.escape(policy_id)}\',\'{html.escape(persona_id)}\')">{html.escape(persona_name)}</button>'
            )

            cards = []
            details = []
            for rank, item in enumerate(result["recommended"], start=1):
                panel_id = f"detail-{policy_id}-{persona_id}-{rank}"
                card, panel = render_recommendation_card(item, rank, panel_id)
                cards.append(card)
                details.append(panel)

            panels.append(f"""
            <div class="persona-panel" id="panel-{html.escape(policy_id)}-{html.escape(persona_id)}" style="display:{display};">
                <div class="profile-box">
                    <div class="profile-title">What this persona is like</div>
                    {render_dimension_bars(result["persona_dimensions"])}
                </div>
                <div class="rec-list">{"".join(cards)}</div>
                {"".join(details)}
            </div>
            """)

        sections.append(f"""
        <section id="policy-{html.escape(policy_id)}" style="display:{"block" if policy_name == first_policy else "none"};">
            <h2>{html.escape(policy_name)}</h2>
            <div class="persona-tabs">{"".join(tabs)}</div>
            {"".join(panels)}
        </section>
        """)

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Privacy Recommendations - Demo</title>
<style>
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#f4f7fb; color:#172033; font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }}
    .page {{ max-width:900px; margin:0 auto; padding:26px; }}
    .top-bar {{ background:#172033; color:white; padding:18px 22px; border-radius:12px; display:flex; align-items:center; justify-content:space-between; gap:20px; }}
    .top-bar h1 {{ margin:0; font-size:20px; }}
    select {{ min-width:240px; padding:9px 12px; border-radius:8px; border:none; }}
    .persona-tabs {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; }}
    .persona-tab {{ padding:8px 14px; border-radius:20px; border:1px solid #cbd5e1; background:white; cursor:pointer; font-size:13px; }}
    .persona-tab:hover {{ background:#eef2f7; }}
    .profile-box {{ background:white; border-radius:12px; padding:16px 18px; margin-bottom:16px; }}
    .profile-title {{ font-weight:700; font-size:13px; margin-bottom:10px; color:#334155; }}
    .dim-row {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; font-size:12px; }}
    .dim-label {{ width:160px; color:#475569; }}
    .dim-track {{ flex:1; background:#eef2f7; border-radius:6px; height:8px; overflow:hidden; }}
    .dim-fill {{ background:#4f46e5; height:100%; }}
    .rec-list {{ display:flex; flex-direction:column; gap:10px; }}
    .rec-card {{ background:white; border-radius:12px; padding:14px 16px; display:flex; gap:12px; }}
    .rec-rank {{ font-weight:800; font-size:20px; color:#94a3b8; width:26px; flex-shrink:0; }}
    .rec-title {{ font-weight:700; font-size:15px; margin-bottom:6px; }}
    .conf-badge {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 9px; border-radius:999px; color:white; margin-bottom:8px; }}
    .conf-high, .conf-medium {{ background:#16a34a; }}
    .conf-low {{ background:#d97706; }}
    .conf-baseline {{ background:#64748b; }}
    .evidence-quote {{ font-size:13px; background:#f8fafc; border-left:3px solid #94a3b8; padding:8px 12px; border-radius:6px; margin-bottom:8px; }}
    .channel-line {{ font-size:12px; color:#475569; margin-bottom:2px; }}
    .channel-line.none {{ font-style:italic; color:#94a3b8; }}
    .details-toggle {{ margin-top:8px; font-size:11px; color:#4f46e5; background:none; border:1px solid #c7d2fe; border-radius:6px; padding:4px 10px; cursor:pointer; }}
    .detail-panel {{ background:#f8fafc; border-radius:10px; padding:14px 16px; margin:-4px 0 10px 38px; font-size:12px; }}
    .detail-label {{ font-weight:800; text-transform:uppercase; letter-spacing:.04em; font-size:10px; color:#64748b; margin:10px 0 4px; }}
    .detail-text {{ margin:0; }}
    .signal-row {{ background:white; border-radius:6px; padding:6px 10px; margin-bottom:5px; }}
    .signal-reason {{ color:#64748b; margin-top:2px; }}
    .domain-table {{ border-collapse:collapse; }}
    .domain-table td {{ padding:2px 8px; border:1px solid #e5eaf1; }}
</style>
</head>
<body>
<div class="page">
    <div class="top-bar">
        <h1>Privacy Recommendations</h1>
        <select onchange="showPolicy(this.value)">{policy_options}</select>
    </div>
    {"".join(sections)}
</div>
<script>
function showPolicy(policyId) {{
    document.querySelectorAll("section").forEach(s => s.style.display = "none");
    document.getElementById("policy-" + policyId).style.display = "block";
}}
function showPersona(policyId, personaId) {{
    document.querySelectorAll("#policy-" + policyId + " .persona-panel").forEach(p => p.style.display = "none");
    document.getElementById("panel-" + policyId + "-" + personaId).style.display = "block";
}}
function toggleDetail(panelId) {{
    var el = document.getElementById(panelId);
    if (el) el.style.display = (el.style.display === "none") ? "block" : "none";
}}
</script>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    print(f"Report written to: {output_path} ({len(policy_names)} policies)")


def generate_single_policy_html(policy_name: str, persona_results: dict, output_path: Path) -> None:
    """
    Same visual design as the full multi-policy report, but for one
    policy already computed by recommender.py - no policy dropdown
    needed, and nothing gets recomputed. persona_results is
    {persona_name: result_dict_from_recommend_for_persona}. This is
    what recommender.py calls automatically after every run.
    """
    policy_id = safe_id(policy_name)
    persona_names = sorted(persona_results.keys())

    tabs = []
    panels = []
    for i, persona_name in enumerate(persona_names):
        persona_id = safe_id(persona_name)
        result = persona_results[persona_name]
        display = "block" if i == 0 else "none"

        tabs.append(
            f'<button class="persona-tab" onclick="showPersona(\'{html.escape(persona_id)}\')">{html.escape(persona_name)}</button>'
        )

        cards = []
        details = []
        for rank, item in enumerate(result["recommended"], start=1):
            panel_id = f"detail-{persona_id}-{rank}"
            card, panel = render_recommendation_card(item, rank, panel_id)
            cards.append(card)
            details.append(panel)

        panels.append(f"""
        <div class="persona-panel" id="panel-{html.escape(persona_id)}" style="display:{display};">
            <div class="profile-box">
                <div class="profile-title">What this persona is like</div>
                {render_dimension_bars(result["persona_dimensions"])}
            </div>
            <div class="rec-list">{"".join(cards)}</div>
            {"".join(details)}
        </div>
        """)

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(policy_name)} - Privacy Recommendations</title>
<style>
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:#f4f7fb; color:#172033; font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif; }}
    .page {{ max-width:900px; margin:0 auto; padding:26px; }}
    .top-bar {{ background:#172033; color:white; padding:18px 22px; border-radius:12px; }}
    .top-bar h1 {{ margin:0; font-size:20px; }}
    .persona-tabs {{ display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; }}
    .persona-tab {{ padding:8px 14px; border-radius:20px; border:1px solid #cbd5e1; background:white; cursor:pointer; font-size:13px; }}
    .persona-tab:hover {{ background:#eef2f7; }}
    .profile-box {{ background:white; border-radius:12px; padding:16px 18px; margin-bottom:16px; }}
    .profile-title {{ font-weight:700; font-size:13px; margin-bottom:10px; color:#334155; }}
    .dim-row {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; font-size:12px; }}
    .dim-label {{ width:160px; color:#475569; }}
    .dim-track {{ flex:1; background:#eef2f7; border-radius:6px; height:8px; overflow:hidden; }}
    .dim-fill {{ background:#4f46e5; height:100%; }}
    .rec-list {{ display:flex; flex-direction:column; gap:10px; }}
    .rec-card {{ background:white; border-radius:12px; padding:14px 16px; display:flex; gap:12px; }}
    .rec-rank {{ font-weight:800; font-size:20px; color:#94a3b8; width:26px; flex-shrink:0; }}
    .rec-title {{ font-weight:700; font-size:15px; margin-bottom:6px; }}
    .conf-badge {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 9px; border-radius:999px; color:white; margin-bottom:8px; }}
    .conf-high, .conf-medium {{ background:#16a34a; }}
    .conf-low {{ background:#d97706; }}
    .conf-baseline {{ background:#64748b; }}
    .evidence-quote {{ font-size:13px; background:#f8fafc; border-left:3px solid #94a3b8; padding:8px 12px; border-radius:6px; margin-bottom:8px; }}
    .channel-line {{ font-size:12px; color:#475569; margin-bottom:2px; }}
    .channel-line.none {{ font-style:italic; color:#94a3b8; }}
    .details-toggle {{ margin-top:8px; font-size:11px; color:#4f46e5; background:none; border:1px solid #c7d2fe; border-radius:6px; padding:4px 10px; cursor:pointer; }}
    .detail-panel {{ background:#f8fafc; border-radius:10px; padding:14px 16px; margin:-4px 0 10px 38px; font-size:12px; }}
    .detail-label {{ font-weight:800; text-transform:uppercase; letter-spacing:.04em; font-size:10px; color:#64748b; margin:10px 0 4px; }}
    .detail-text {{ margin:0; }}
    .signal-row {{ background:white; border-radius:6px; padding:6px 10px; margin-bottom:5px; }}
    .signal-reason {{ color:#64748b; margin-top:2px; }}
    .domain-table {{ border-collapse:collapse; }}
    .domain-table td {{ padding:2px 8px; border:1px solid #e5eaf1; }}
</style>
</head>
<body>
<div class="page">
    <div class="top-bar"><h1>{html.escape(policy_name)}</h1></div>
    <div class="persona-tabs">{"".join(tabs)}</div>
    {"".join(panels)}
</div>
<script>
function showPersona(personaId) {{
    document.querySelectorAll(".persona-panel").forEach(p => p.style.display = "none");
    document.getElementById("panel-" + personaId).style.display = "block";
}}
function toggleDetail(panelId) {{
    var el = document.getElementById(panelId);
    if (el) el.style.display = (el.style.display === "none") ? "block" : "none";
}}
</script>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    print(f"HTML demo written to: {output_path}")


if __name__ == "__main__":
    DATA_DIR = Path(__file__).parent / "Data"
    catalog_path = Path(__file__).parent.parent / "PrivacyExtractor" / "output" / "ipn101_extractions_clean.json"
    report_data = build_report_data(DATA_DIR, catalog_path)
    generate_html_report(report_data, Path(__file__).parent / "recommendations_demo.html")