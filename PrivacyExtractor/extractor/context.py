"""
CONTEXT - helpers for document context and HTML link matching.

Used to identify formal-rights framing where needed and to attach
the most specific real HTML link to extracted evidence.
"""

from __future__ import annotations

from typing import Any

from extractor.text_utils import normalise_text

EXPLICIT_RIGHT_PHRASES = [
    "right to",
    "have the right",
    "has the right",
    "privacy right",
    "data protection right",
    "data subject right",
    "entitled to",
]

FORMAL_LIST_PHRASES = [
    "following data protection rights",
    "following privacy rights",
    "following rights",
    "you have certain rights",
    "you have the following rights",
    "you may have the right",
    "exercise your data protection rights",
    "exercise your privacy rights",
    "data protection rights regardless of your location",
]

RIGHTS_HEADING_PHRASES = [
    "your rights",
    "privacy rights",
    "data protection rights",
    "data subject rights",
    "individual rights",
]


def formal_right_context(
    segment: dict[str, Any],
    evidence: str = "",
    extended_context: str = "",
) -> bool:
    """
    Checks whether a passage is framed as a formal privacy/data
    protection right, looking at the evidence, current segment,
    previous segment, wider preceding context, and heading path.
    """
    current_text = normalise_text(segment.get("text", ""))
    previous_text = normalise_text(segment.get("previous_segment_text", ""))
    extended_text = normalise_text(extended_context)
    heading_text = normalise_text(" ".join(segment.get("heading_path", [])))
    evidence_text = normalise_text(evidence)

    if any(phrase in evidence_text for phrase in EXPLICIT_RIGHT_PHRASES):
        return True

    if any(phrase in current_text for phrase in FORMAL_LIST_PHRASES):
        return True

    if any(phrase in extended_text[-1200:] for phrase in FORMAL_LIST_PHRASES):
        return True

    if any(phrase in previous_text[-700:] for phrase in FORMAL_LIST_PHRASES):
        return True

    if any(phrase in heading_text for phrase in RIGHTS_HEADING_PHRASES):
        return True

    combined_context = " ".join([extended_text[-1200:], previous_text[-700:], current_text, heading_text])
    return any(phrase in combined_context for phrase in FORMAL_LIST_PHRASES)


def find_matching_link(segment: dict[str, Any], evidence: str) -> dict[str, str] | None:
    """
    Finds the most specific real HTML link whose visible text overlaps
    with the evidence. If several match, prefers the longest link text.
    """
    evidence_normalised = normalise_text(evidence)

    matches = [
        link for link in segment.get("links", [])
        if normalise_text(link.get("text", ""))
        and (
            normalise_text(link.get("text", "")) in evidence_normalised
            or evidence_normalised in normalise_text(link.get("text", ""))
        )
    ]

    if not matches:
        return None

    return max(matches, key=lambda link: len(normalise_text(link.get("text", ""))))


def find_link_for_evidence(evidence: str, segment: dict) -> dict | None:
    """Finds the most specific matching HTML link for an annotation's evidence and returns its real destination."""
    link = find_matching_link(segment=segment, evidence=evidence)

    if not link:
        return None

    return {
        "url": link.get("href", ""),
        "kind": link.get("kind", ""),
        "visible_text": link.get("text", ""),
    }