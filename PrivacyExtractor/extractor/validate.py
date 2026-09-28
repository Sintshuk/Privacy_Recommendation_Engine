"""
VALIDATE - the main gate every right/choice/channel/reference passes
through: real vocabulary value? real exact-quote evidence?
"""

from __future__ import annotations

from typing import Any

from extractor.context import formal_right_context
from extractor.text_utils import normalise_text


def validate_entries(
    raw_entries: Any,
    allowed_values: dict,
    attribute: str,
    segment: dict[str, Any],
) -> tuple[list[dict], list[dict]]:
    """
    For each entry the model returned:
    1. checks it's really in our vocabulary
    2. checks the evidence is a real, exact quote from the segment
    Keeps the model's local id/applies_to (for channel linking) if present.
    """
    accepted: list[dict] = []
    rejected: list[dict] = []

    if not isinstance(raw_entries, list):
        rejected.append({"attribute": attribute, "reason": "attribute_is_not_a_list", "raw": raw_entries})
        return accepted, rejected

    segment_text = segment.get("text", "")

    for entry in raw_entries:
        if not isinstance(entry, dict):
            rejected.append({"attribute": attribute, "reason": "entry_not_object", "raw": entry})
            continue

        value = entry.get("value", "")
        evidence = entry.get("evidence", "")
        local_id = entry.get("id", "")
        applies_to_local = entry.get("applies_to", [])

        base_item = {"attribute": attribute, "value": value, "evidence": evidence}

        if value not in allowed_values:
            rejected.append({**base_item, "reason": "invalid_vocabulary_value"})
            continue

        if not evidence or evidence not in segment_text:
            rejected.append({**base_item, "reason": "evidence_not_exact"})
            continue

        accepted.append({
            "value": value,
            "evidence": evidence,
            "confidence": "extracted",
            "_local_id": local_id,
            "_applies_to_local": applies_to_local,
        })

    return accepted, rejected


def valid_unresolved_reference(evidence: str) -> bool:
    """Keeps only references that genuinely point to information elsewhere in the document."""
    evidence_lower = normalise_text(evidence)

    reference_phrases = [
        "section", "described below", "described above", "described in",
        "set out below", "set out above", "contact details below",
        "contact information below", "contact details above",
        "contact information above", "refer to", "see below", "see above",
        "tools above", "tools below",
    ]
    noise_phrases = ["back to top", "microsoft privacy report"]

    if any(phrase in evidence_lower for phrase in noise_phrases):
        return False

    return any(phrase in evidence_lower for phrase in reference_phrases)


RELEVANT_REFERENCE_TERMS = [
    "right", "access", "control", "choice", "delete", "erase", "eras",
    "rectif", "correct", "restrict", "object", "portab", "consent",
    "opt out", "opt-out", "opting out", "unsubscribe", "complaint",
    "contact", "request", "manage", "withdraw", "exercise",
]


def is_relevant_reference(evidence: str, target_text: str) -> bool:
    """True when a reference's evidence or destination plausibly concerns rights/choices/contact."""
    combined = normalise_text(f"{target_text} {evidence}")
    return any(term in combined for term in RELEVANT_REFERENCE_TERMS)


def validate_references(raw_references: Any, segment: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Same discipline as validate_entries, but for cross-reference claims."""
    accepted: list[dict] = []
    rejected: list[dict] = []

    if not isinstance(raw_references, list):
        rejected.append({"attribute": "reference", "reason": "attribute_is_not_a_list", "raw": raw_references})
        return accepted, rejected

    segment_text = segment.get("text", "")

    for entry in raw_references:
        if not isinstance(entry, dict):
            rejected.append({"attribute": "reference", "reason": "entry_not_object", "raw": entry})
            continue

        evidence = entry.get("evidence", "")
        target_text = entry.get("target_text", "")

        if not evidence or evidence not in segment_text:
            rejected.append({
                "attribute": "reference", "evidence": evidence,
                "target_text": target_text, "reason": "evidence_not_exact",
            })
            continue

        if not valid_unresolved_reference(evidence):
            rejected.append({
                "attribute": "reference", "evidence": evidence,
                "target_text": target_text, "reason": "not_an_unresolved_reference",
            })
            continue

        if not is_relevant_reference(evidence, target_text):
            rejected.append({
                "attribute": "reference", "evidence": evidence,
                "target_text": target_text, "reason": "reference_target_not_rights_relevant",
            })
            continue

        accepted.append({
            "evidence": evidence,
            "target_text": target_text,
            "confidence": "extracted",
        })

    return accepted, rejected


DUPLICATE_CHOICE_VALUES = {
    "View and update personal data",
    "Delete personal data or account",
    "Manage notifications and communications",
}


def suppress_formal_right_choice_duplicates(
    rights: list[dict],
    choices: list[dict],
    segment: dict[str, Any],
) -> tuple[list[dict], list[dict]]:
    """Removes ordinary-choice duplicates when the same passage is clearly a formal rights list."""
    if not rights or not formal_right_context(segment):
        return choices, []

    right_evidence = {normalise_text(item.get("evidence", "")) for item in rights}

    kept_choices: list[dict] = []
    suppressed: list[dict] = []

    for choice in choices:
        choice_evidence = normalise_text(choice.get("evidence", ""))
        exact_duplicate = choice_evidence in right_evidence
        formal_object_language = (
            choice.get("value") == "Manage notifications and communications"
            and "object" in choice_evidence
        )

        if choice.get("value") in DUPLICATE_CHOICE_VALUES and (exact_duplicate or formal_object_language):
            suppressed.append({
                "attribute": "choice_type",
                "value": choice.get("value", ""),
                "evidence": choice.get("evidence", ""),
                "reason": "duplicate_of_formal_right",
            })
            continue

        kept_choices.append(choice)

    return kept_choices, suppressed