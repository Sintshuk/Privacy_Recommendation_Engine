"""
RECOVER - rescue claims that were rejected for being the WRONG ATTRIBUTE
TYPE (e.g. tagged as a right when it's really a choice), instead of
losing the fact entirely.
"""

from __future__ import annotations

from typing import Any

from extractor.text_utils import normalise_text
from extractor.validate import valid_unresolved_reference

CONFIDENCE_INFERRED = "inferred"

# Only these right_type values have a clear, unambiguous choice_type
# equivalent. Values like "Right to object" don't map cleanly to one
# choice, so those stay rejected rather than risk a wrong guess.
RIGHT_TO_CHOICE_FALLBACK = {
    "Right of access": "View and update personal data",
    "Right to rectification": "View and update personal data",
    "Right to erasure": "Delete personal data or account",
}

# Wording that shows the passage really does describe a self-service
# control, rather than merely a right stated without formal framing.
# "You have the right to erasure" outside a rights list is NOT evidence
# that a delete button exists; "you can delete your account in the app"
# is. Requiring this stops the fallback inventing mechanisms.
SELF_SERVICE_TERMS = [
    "you can", "you may", "in the app", "in your account", "account settings",
    "settings", "dashboard", "portal", "online", "self-service", "directly",
    "within our services", "on the website", "sign in", "log in",
]


def looks_like_self_service(evidence: str) -> bool:
    """True when the evidence describes an actual control the user can operate."""
    return any(term in normalise_text(evidence) for term in SELF_SERVICE_TERMS)


def recover_rejected_rights_as_choices(
    rejected: list[dict],
    segment: dict[str, Any],
) -> tuple[list[dict], list[dict]]:
    """
    A right rejected for missing formal-rights framing MAY still describe
    a real choice - but only when the evidence actually points at a
    usable control. Otherwise it stays rejected and visible.
    """
    recovered: list[dict] = []
    still_rejected: list[dict] = []

    for item in rejected:
        is_right_rejection = (
            item.get("attribute") == "right_type"
            and item.get("reason") == "formal_right_context_missing"
        )
        fallback_value = RIGHT_TO_CHOICE_FALLBACK.get(item.get("value", ""))
        evidence = item.get("evidence", "")

        if is_right_rejection and fallback_value and looks_like_self_service(evidence):
            recovered.append({
                "value": fallback_value,
                "evidence": evidence,
                "confidence": CONFIDENCE_INFERRED,
                "inference_rule": "right_without_formal_framing_to_choice",
                "_local_id": "",
                "_applies_to_local": [],
                "recovered_from": f"right_type:{item.get('value', '')}",
            })
            continue

        if is_right_rejection and fallback_value:
            item = {**item, "reason": "formal_right_context_missing_and_no_self_service_control"}

        still_rejected.append(item)

    return recovered, still_rejected


def recover_channel_as_reference(rejected: list[dict]) -> tuple[list[dict], list[dict]]:
    """A request_channel rejection sometimes means the text was really an unresolved cross-reference."""
    recovered: list[dict] = []
    still_rejected: list[dict] = []

    for item in rejected:
        is_channel_rejection = item.get("attribute") == "request_channel"
        evidence = item.get("evidence", "")

        if is_channel_rejection and valid_unresolved_reference(evidence):
            recovered.append({
                "evidence": evidence,
                "target_text": evidence,
                "confidence": CONFIDENCE_INFERRED,
                "inference_rule": "channel_to_unresolved_reference",
                "recovered_from": f"request_channel:{item.get('value', '')}",
            })
            continue

        still_rejected.append(item)

    return recovered, still_rejected