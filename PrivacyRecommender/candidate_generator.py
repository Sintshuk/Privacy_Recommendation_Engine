"""Build policy-supported recommendation candidates."""

from __future__ import annotations

import re

# skipped values
EXCLUDED_VALUES = {"Other", "Not specified", "", None}
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I) # find an email address in text

# cleans up one contact method
def _channel_details(channel: dict) -> dict:
    """Keep action details already found by the extractor."""
    evidence = channel.get("evidence", "") or ""
    link = channel.get("link")

    if isinstance(link, dict):
        url = link.get("url") or link.get("href")
        label = link.get("visible_text") or link.get("text")
    else:
        url = link
        label = None

    emails = EMAIL_RE.findall(evidence)

    return {
        "type": channel.get("value"),
        "evidence": evidence,
        "email": emails[0] if emails else None,
        "url": url,
        "label": label,
    }

# turns extraction to a clean recommendation candidate
def build_candidates(policy_blocks: list[dict], catalog: dict) -> list[dict]:
    """Create one candidate per supported right or choice."""
    candidates: dict[str, dict] = {}

    for block in policy_blocks:
        # find channels
        channels_by_target: dict[str, list[dict]] = {}

        for item in block.get("extractions", []):
            if item.get("attribute") != "request_channel":
                continue

            for target_id in item.get("linked_ids", []):
                channels_by_target.setdefault(target_id, []).append(item)

        # build a candidate for each right/choice
        for item in block.get("extractions", []):
            attribute = item.get("attribute")
            value = item.get("value")

            if attribute not in {"right_type", "choice_type"}:
                continue

            if value in EXCLUDED_VALUES:
                continue

            catalog_item = catalog.get(attribute, {}).get(value)

            if catalog_item is None:
                continue

            candidate_id = catalog_item["id"]

            candidate = candidates.setdefault(
                candidate_id,
                {
                    "recommendation_id": candidate_id,
                    "title": catalog_item["title"],
                    "category": catalog_item["category"],
                    "attribute": attribute,
                    "value": value,
                    "evidence": [],
                    "channels": [],
                    "functionality_impact": catalog_item.get(
                        "functionality_impact",
                        "unknown",
                    ),
                },
            )

            #attach evidence
            evidence = {
                "text": item.get("evidence", ""),
                "confidence": item.get("confidence"),
                "segment_id": block.get("segment_id"),
                "segment_text": block.get("segment_text", ""),
            }

            if evidence not in candidate["evidence"]:
                candidate["evidence"].append(evidence)

            for channel in channels_by_target.get(item.get("id"), []):
                clean_channel = _channel_details(channel)

                if clean_channel not in candidate["channels"]:
                    candidate["channels"].append(clean_channel)

    return list(candidates.values())
