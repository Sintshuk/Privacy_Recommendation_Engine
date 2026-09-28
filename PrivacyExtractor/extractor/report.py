from __future__ import annotations

import html
import json
from collections import defaultdict
from typing import Any


CATEGORY_INFO = {
    "right_type": {
        "label": "Formal right",
        "class": "right-highlight",
    },
    "choice_type": {
        "label": "Choice",
        "class": "choice-highlight",
    },
    "request_channel": {
        "label": "Request channel",
        "class": "channel-highlight",
    },
    "references": {
        "label": "Unresolved reference",
        "class": "reference-highlight",
    },
    "rejected": {
        "label": "Rejected",
        "class": "rejected-highlight",
    },
}


def collect_evidence_annotations(result: dict) -> dict[str, list[dict]]:
    """
    Groups all annotations by their exact evidence quote.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)

    for attribute in [
        "right_type",
        "choice_type",
        "request_channel",
        "references",
        "rejected",
    ]:
        for item in result.get(attribute, []):
            evidence = item.get("evidence", "")

            if not evidence:
                continue

            grouped[evidence].append({
                "attribute": attribute,
                "item": item,
            })

    return grouped


def choose_highlight_class(annotations: list[dict]) -> str:
    """
    Chooses one visible colour when the same evidence has several annotations.
    Accepted results take priority.
    """
    priority = [
        "right_type",
        "choice_type",
        "request_channel",
        "references",
        "rejected",
    ]

    attributes = {
        annotation["attribute"]
        for annotation in annotations
    }

    for attribute in priority:
        if attribute in attributes:
            return CATEGORY_INFO[attribute]["class"]

    return "neutral-highlight"


def annotation_title(annotations: list[dict]) -> str:
    descriptions: list[str] = []

    for annotation in annotations:
        attribute = annotation["attribute"]
        item = annotation["item"]

        category_label = CATEGORY_INFO[attribute]["label"]

        value = item.get(
            "value",
            item.get("target_text", ""),
        )

        if attribute == "rejected":
            reason = item.get("reason", "")
            descriptions.append(
                f"{category_label}: {value} ({reason})"
            )

        else:
            descriptions.append(
                f"{category_label}: {value}"
            )

    return " | ".join(descriptions)


def highlight_segment_text(segment_text: str, result: dict) -> str:
    """
    Highlights exact evidence spans inside the segment text.
    """
    evidence_groups = collect_evidence_annotations(result)

    intervals: list[dict] = []

    for evidence, annotations in evidence_groups.items():
        start = 0

        while True:
            index = segment_text.find(evidence, start)

            if index == -1:
                break

            intervals.append({
                "start": index,
                "end": index + len(evidence),
                "evidence": evidence,
                "annotations": annotations,
            })

            start = index + len(evidence)

    # Prefer longer evidence spans when overlaps occur.
    intervals.sort(
        key=lambda item: (
            item["start"],
            -(item["end"] - item["start"]),
        )
    )

    selected: list[dict] = []
    current_end = -1

    for interval in intervals:
        if interval["start"] < current_end:
            continue

        selected.append(interval)
        current_end = interval["end"]

    output: list[str] = []
    cursor = 0

    for interval in selected:
        output.append(
            html.escape(segment_text[cursor:interval["start"]])
        )

        css_class = choose_highlight_class(interval["annotations"])
        title = annotation_title(interval["annotations"])

        highlighted_text = segment_text[
            interval["start"]:interval["end"]
        ]

        output.append(
            f'<mark class="{css_class}" '
            f'title="{html.escape(title)}">'
            f'{html.escape(highlighted_text)}'
            '</mark>'
        )

        cursor = interval["end"]

    output.append(
        html.escape(segment_text[cursor:])
    )

    return "".join(output)


def build_channels_by_linked_item_id(result: dict) -> dict[str, list[dict]]:
    """
    Each channel stores which right(s)/choice(s) it belongs to:

      channel["linked_ids"] = [
          "Policy:S1:right:1",
          "Policy:S1:choice:1"
      ]

    The report needs the reverse lookup:

      item_id -> linked channels
    """
    channels_by_linked_item_id: dict[str, list[dict]] = defaultdict(list)

    for channel in result.get("request_channel", []):
        for linked_id in channel.get("linked_ids", []):
            channels_by_linked_item_id[linked_id].append(channel)

    return channels_by_linked_item_id


def render_linked_channels(
    item: dict,
    channels_by_linked_item_id: dict[str, list[dict]],
) -> str:
    """
    Builds the linked-channel display under each right/choice row.
    """
    item_id = item.get("id", "")
    linked_channels = channels_by_linked_item_id.get(item_id, [])

    if not linked_channels:
        return (
            '<div class="linked-channels empty">'
            'No linked channel found in this segment.'
            '</div>'
        )

    pieces: list[str] = []

    for channel in linked_channels:
        value = html.escape(str(channel.get("value", "")))
        evidence = html.escape(str(channel.get("evidence", "")))
        channel_id = html.escape(str(channel.get("id", "")))

        link = channel.get("link")

        if link and link.get("url"):
            url = html.escape(str(link["url"]))
            label = html.escape(str(link.get("visible_text", value)))
            value_html = (
                f'{value} — '
                f'<a href="{url}" target="_blank" rel="noopener">'
                f'{label}'
                f'</a>'
            )
        else:
            value_html = value

        resolution_note = ""

        if channel.get("resolution_method"):
            method = html.escape(str(channel["resolution_method"]))
            resolution_note = (
                f' <span class="resolution-tag">'
                f'resolved via {method}'
                f'</span>'
            )

        pieces.append(
            f'<div class="linked-channel-item">'
            f'→ {value_html}{resolution_note}<br>'
            f'<span>{evidence}</span>'
            f'</div>'
        )

    return f'<div class="linked-channels">{"".join(pieces)}</div>'


def accepted_table(result: dict) -> str:
    rows: list[str] = []
    channels_by_linked_item_id = build_channels_by_linked_item_id(result)

    for attribute in [
        "right_type",
        "choice_type",
        "request_channel",
        "references",
    ]:
        category = CATEGORY_INFO[attribute]

        for item in result.get(attribute, []):
            value = item.get(
                "value",
                item.get("target_text", ""),
            )

            evidence = item.get("evidence", "")
            item_id = item.get("id", "")

            linked_html = ""

            if attribute in ("right_type", "choice_type"):
                linked_html = render_linked_channels(
                    item,
                    channels_by_linked_item_id,
                )

            rows.append(
                "<tr>"
                f'<td><span class="category-pill {category["class"]}">'
                f'{html.escape(category["label"])}'
                "</span></td>"
                f"<td>{html.escape(str(value))}{linked_html}</td>"
                f"<td>{html.escape(str(evidence))}</td>"
                f"<td><code>{html.escape(str(item_id))}</code></td>"
                "</tr>"
            )

    if not rows:
        return (
            '<p class="empty-message">'
            "No accepted annotations."
            "</p>"
        )

    return (
        '<table class="annotation-table">'
        "<thead>"
        "<tr>"
        "<th>Type</th>"
        "<th>Annotation</th>"
        "<th>Exact evidence</th>"
        "<th>ID</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def rejected_table(result: dict) -> str:
    rejected = result.get("rejected", [])

    if not rejected:
        return ""

    rows: list[str] = []

    for item in rejected:
        value = item.get(
            "value",
            item.get("target_text", ""),
        )

        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('attribute', '')))}</td>"
            f"<td>{html.escape(str(value))}</td>"
            f"<td>{html.escape(str(item.get('evidence', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            "</tr>"
        )

    return (
        '<details class="review-box rejected-box">'
        f"<summary>Rejected ({len(rejected)})</summary>"
        '<table class="annotation-table">'
        "<thead>"
        "<tr>"
        "<th>Attribute</th>"
        "<th>Model value</th>"
        "<th>Evidence</th>"
        "<th>Reason</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</details>"
    )


def segment_metadata(segment: dict) -> str:
    metadata = {
        "heading_path": segment.get("heading_path", []),
        "html_ids": segment.get("html_ids", []),
        "links": segment.get("links", []),
        "previous_segment_id": segment.get("previous_segment_id"),
        "next_segment_id": segment.get("next_segment_id"),
        "previous_segment_context": segment.get(
            "previous_segment_text",
            "",
        ),
    }

    return json.dumps(
        metadata,
        ensure_ascii=False,
        indent=2,
    )


def build_segment_card(row: dict) -> str:
    segment = row["segment"]
    result = row.get("result")

    segment_id = segment.get("id", "")

    if result is None:
        return f"""
        <div class="segment-card failed-card">
            <h3>{html.escape(segment_id)} — Extraction failed</h3>
            <div class="source-text">
                {html.escape(segment.get("text", ""))}
            </div>
        </div>
        """

    highlighted_text = highlight_segment_text(
        segment_text=segment.get("text", ""),
        result=result,
    )

    accepted_count = sum(
        len(result.get(attribute, []))
        for attribute in [
            "right_type",
            "choice_type",
            "request_channel",
            "references",
        ]
    )

    rejected_count = len(
        result.get("rejected", [])
    )

    return f"""
    <div class="segment-card">
        <div class="segment-header">
            <h3>{html.escape(segment_id)}</h3>

            <div class="counts">
                <span class="count accepted-count">
                    Accepted: {accepted_count}
                </span>

                <span class="count rejected-count">
                    Rejected: {rejected_count}
                </span>
            </div>
        </div>

        <div class="source-label">
            Annotated source text
        </div>

        <div class="source-text">
            {highlighted_text}
        </div>

        <h4>Accepted annotations</h4>
        {accepted_table(result)}

        {rejected_table(result)}

        <details class="metadata-box">
            <summary>Segment context and HTML metadata</summary>
            <pre>{html.escape(segment_metadata(segment))}</pre>
        </details>
    </div>
    """


def safe_policy_id(policy_name: str) -> str:
    return (
        policy_name
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def generate_combined_report(
    all_results: dict,
    output_path: str,
    run_metadata: dict,
) -> None:
    sections: list[str] = []
    options: list[str] = []

    for index, (policy_name, rows) in enumerate(all_results.items()):
        policy_id = safe_policy_id(policy_name)

        options.append(
            f'<option value="{html.escape(policy_id)}">'
            f'{html.escape(policy_name)}'
            "</option>"
        )

        cards = "".join(
            build_segment_card(row)
            for row in rows
        )

        display = "block" if index == 0 else "none"

        sections.append(
            f'<section id="policy-{html.escape(policy_id)}" '
            f'style="display:{display};">'
            f"<h2>{html.escape(policy_name)}</h2>"
            f"{cards}"
            "</section>"
        )

    metadata_json = json.dumps(
        run_metadata,
        ensure_ascii=False,
        indent=2,
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Rights and Choices Extraction Review</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: #f4f7fb;
            color: #172033;
            font-family:
                Inter,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }}

        .page {{
            max-width: 1320px;
            margin: 0 auto;
            padding: 26px;
        }}

        .top-bar {{
            background: #172033;
            color: white;
            padding: 18px 22px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
        }}

        .top-bar h1 {{
            margin: 0;
            font-size: 21px;
        }}

        select {{
            min-width: 180px;
            padding: 9px 12px;
            border-radius: 8px;
            border: none;
        }}

        .legend {{
            background: white;
            border: 1px solid #dce3ed;
            border-radius: 10px;
            margin: 18px 0;
            padding: 14px 16px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .legend-item,
        .category-pill {{
            display: inline-block;
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
        }}

        .right-highlight {{
            background: #bbf7d0;
            color: #14532d;
        }}

        .choice-highlight {{
            background: #bfdbfe;
            color: #1e3a8a;
        }}

        .channel-highlight {{
            background: #ddd6fe;
            color: #4c1d95;
        }}

        .reference-highlight {{
            background: #fed7aa;
            color: #7c2d12;
        }}

        .rejected-highlight {{
            background: #fecaca;
            color: #7f1d1d;
            text-decoration: line-through;
            text-decoration-thickness: 1px;
        }}

        mark {{
            padding: 2px 3px;
            border-radius: 4px;
            cursor: help;
        }}

        .run-metadata {{
            background: #e9eef6;
            padding: 12px;
            border-radius: 8px;
            white-space: pre-wrap;
            font-size: 12px;
        }}

        .segment-card {{
            background: white;
            border: 1px solid #dce3ed;
            border-radius: 12px;
            margin: 18px 0;
            padding: 18px;
            box-shadow:
                0 3px 12px
                rgba(28, 42, 69, 0.06);
        }}

        .failed-card {{
            border-color: #ef4444;
        }}

        .segment-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            border-bottom: 1px solid #e5eaf1;
            padding-bottom: 10px;
            margin-bottom: 14px;
        }}

        .segment-header h3 {{
            margin: 0;
        }}

        .counts {{
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
        }}

        .count {{
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 12px;
            font-weight: 700;
        }}

        .accepted-count {{
            background: #dcfce7;
            color: #166534;
        }}

        .rejected-count {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .source-label {{
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 7px;
        }}

        .source-text {{
            font-size: 16px;
            line-height: 1.85;
            background: #f8fafc;
            border-left: 4px solid #94a3b8;
            padding: 14px 16px;
            border-radius: 6px;
            margin-bottom: 18px;
        }}

        .annotation-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 16px;
            font-size: 13px;
        }}

        .annotation-table th {{
            text-align: left;
            background: #eef2f7;
            padding: 9px;
            border: 1px solid #dce3ed;
        }}

        .annotation-table td {{
            vertical-align: top;
            padding: 9px;
            border: 1px solid #dce3ed;
            line-height: 1.45;
        }}

        .annotation-table td:nth-child(3) {{
            max-width: 560px;
        }}

        code {{
            font-size: 11px;
            word-break: break-all;
        }}

        .review-box {{
            margin: 13px 0;
            padding: 10px;
            border-radius: 8px;
        }}

        .review-box summary {{
            cursor: pointer;
            font-weight: 800;
        }}

        .rejected-box {{
            background: #fff1f2;
            border: 1px solid #fda4af;
        }}

        .metadata-box {{
            margin-top: 14px;
            background: #eef2f7;
            border-radius: 8px;
            padding: 10px;
        }}

        .metadata-box summary {{
            cursor: pointer;
            font-weight: 700;
        }}

        .metadata-box pre {{
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-size: 11px;
        }}

        .empty-message {{
            color: #64748b;
            font-style: italic;
        }}

        .linked-channels {{
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px dashed #dce3ed;
        }}

        .linked-channel-item {{
            font-size: 12px;
            color: #4c1d95;
            margin-top: 5px;
        }}

        .linked-channels.empty {{
            font-size: 12px;
            color: #94a3b8;
            font-style: italic;
            margin-top: 6px;
        }}

        .linked-channel-item a {{
            color: #2563eb;
            text-decoration: underline;
        }}

        .resolution-tag {{
            font-size: 10px;
            background: #fef3c7;
            color: #92400e;
            padding: 1px 5px;
            border-radius: 4px;
            margin-left: 4px;
        }}

        @media (max-width: 800px) {{
            .page {{
                padding: 12px;
            }}

            .top-bar,
            .segment-header {{
                align-items: flex-start;
                flex-direction: column;
            }}

            .annotation-table {{
                display: block;
                overflow-x: auto;
            }}
        }}
    </style>
</head>

<body>
    <div class="page">
        <div class="top-bar">
            <h1>Rights & Choices Extraction Review</h1>

            <select onchange="showPolicy(this.value)">
                {''.join(options)}
            </select>
        </div>

        <div class="legend">
            <span class="legend-item right-highlight">
                Formal right
            </span>

            <span class="legend-item choice-highlight">
                Choice
            </span>

            <span class="legend-item channel-highlight">
                Request channel
            </span>

            <span class="legend-item reference-highlight">
                Unresolved reference
            </span>

            <span class="legend-item rejected-highlight">
                Rejected
            </span>
        </div>

        <details>
            <summary><b>Run metadata</b></summary>
            <pre class="run-metadata">{html.escape(metadata_json)}</pre>
        </details>

        {''.join(sections)}
    </div>

    <script>
        function showPolicy(policyId) {{
            document
                .querySelectorAll("section")
                .forEach(function(section) {{
                    section.style.display = "none";
                }});

            document
                .getElementById("policy-" + policyId)
                .style.display = "block";
        }}
    </script>
</body>
</html>
"""

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(document)

    print(f"Report written to: {output_path}")