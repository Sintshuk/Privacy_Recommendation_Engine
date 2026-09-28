"""
PIPELINE - orchestrates one segment's extraction, in order: build the
prompt, call the model, validate everything, recover
cross-attribute mistakes, assign IDs, link channels to their rights and
choices, attach real clickable links, and clean up.

The model call itself lives in model_client.py - this file is
orchestration only.
"""

from __future__ import annotations

import json
from typing import Any

from extractor.vocabulary import RIGHT_TYPE, CHOICE_TYPE, REQUEST_CHANNEL
from extractor.prompt import USER_TEMPLATE, build_vocab_section
from extractor.model_client import call_model
from extractor.validate import validate_entries, validate_references, suppress_formal_right_choice_duplicates
from extractor.recover import recover_rejected_rights_as_choices, recover_channel_as_reference
from extractor.linking import add_ids, resolve_local_links, attach_real_links, strip_internal_fields


def extract_rights(segment: dict[str, Any], policy_name: str) -> dict[str, Any] | None:
    """Runs the full pipeline for one segment. See module docstring for the step-by-step order."""
    user_prompt = USER_TEMPLATE.format(
        vocab_block=build_vocab_section(),
        previous_segment_text=segment.get("previous_segment_text", "") or "(none)",
        heading_path=" > ".join(segment.get("heading_path", [])) or "(none)",
        links=json.dumps(segment.get("links", []), ensure_ascii=False),
        segment_text=segment.get("text", ""),
    )

    parsed = call_model(user_prompt)
    if parsed is None:
        return None

    rights, rejected_rights = validate_entries(
        raw_entries=parsed.get("right_type", []),
        allowed_values=RIGHT_TYPE, attribute="right_type", segment=segment,
    )
    choices, rejected_choices = validate_entries(
        raw_entries=parsed.get("choice_type", []),
        allowed_values=CHOICE_TYPE, attribute="choice_type", segment=segment,
    )
    channels, rejected_channels = validate_entries(
        raw_entries=parsed.get("request_channel", []),
        allowed_values=REQUEST_CHANNEL, attribute="request_channel", segment=segment,
    )
    references, rejected_references = validate_references(
        raw_references=parsed.get("references", []), segment=segment,
    )

    choices, suppressed_choices = suppress_formal_right_choice_duplicates(
        rights=rights, choices=choices, segment=segment,
    )

    rejected = rejected_rights + rejected_choices + rejected_channels + rejected_references + suppressed_choices

    # Recovery pass: some rejections are really "wrong attribute type", not "not real".
    recovered_choices, rejected = recover_rejected_rights_as_choices(rejected, segment)
    choices = choices + recovered_choices

    recovered_references, rejected = recover_channel_as_reference(rejected)
    references = references + recovered_references

    segment_id = segment["id"]

    rights = add_ids(rights, policy_name, segment_id, "right")
    choices = add_ids(choices, policy_name, segment_id, "choice")
    channels = add_ids(channels, policy_name, segment_id, "channel")
    references = add_ids(references, policy_name, segment_id, "reference")

    channels = resolve_local_links(channels, rights, choices)
    channels = attach_real_links(channels, segment)

    rights = strip_internal_fields(rights)
    choices = strip_internal_fields(choices)
    channels = strip_internal_fields(channels)

    return {
        "right_type": rights,
        "choice_type": choices,
        "request_channel": channels,
        "references": references,
        "rejected": rejected,
    }