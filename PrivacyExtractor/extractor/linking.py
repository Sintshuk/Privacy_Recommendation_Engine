"""
LINKING - assigning permanent global IDs to everything, connecting each
request_channel to the specific right(s)/choice(s) it belongs to (within
the same segment), attaching real clickable links where they exist, and
cleaning up temporary fields before the data leaves this pipeline.
"""

from __future__ import annotations

from extractor.context import find_link_for_evidence


def add_ids(entries: list[dict], policy_name: str, segment_id: str, prefix: str) -> list[dict]:
    """Assigns a real, permanent, globally-unique ID to each entry (e.g. Microsoft:S8:choice:1)."""
    output: list[dict] = []
    for index, entry in enumerate(entries, start=1):
        item = dict(entry)
        item["id"] = f"{policy_name}:{segment_id}:{prefix}:{index}"
        output.append(item)
    return output


def resolve_local_links(
    channels: list[dict],
    rights: list[dict],
    choices: list[dict],
) -> list[dict]:
    """
    The model gave channels a list of LOCAL labels ("c1", "r1") saying
    which right/choice they belong to. Now that real global IDs are
    assigned, this swaps the local labels for the real ones, so each
    channel knows exactly which right(s)/choice(s) it answers, within
    THIS segment. Cross-segment linking is a separate step, not here.
    """
    local_to_global = {
        item["_local_id"]: item["id"]
        for item in rights + choices
        if item.get("_local_id")
    }

    for channel in channels:
        applies_to_local = channel.get("_applies_to_local", [])
        channel["linked_ids"] = [
            local_to_global[local_id]
            for local_id in applies_to_local
            if local_id in local_to_global
        ]

    return channels


def attach_real_links(channels: list[dict], segment: dict) -> list[dict]:
    """Attaches a real, clickable link (URL/email/phone) to each channel, when the segment has one matching its evidence."""
    for channel in channels:
        channel["link"] = find_link_for_evidence(channel["evidence"], segment)
    return channels


def strip_internal_fields(entries: list[dict]) -> list[dict]:
    """Removes temporary fields (_local_id, _applies_to_local) that only existed to build linked_ids."""
    return [{k: v for k, v in entry.items() if not k.startswith("_")} for entry in entries]