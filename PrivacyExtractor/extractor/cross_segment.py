"""
CROSS_SEGMENT - runs AFTER every segment in one policy has been extracted.

Resolves "Not specified" channels and unresolved references, but only when
a real document link identifies the target segment.

This is a separate second pass because extraction of a single segment
(pipeline.py) can't see the rest of the document.
"""

from __future__ import annotations

from urllib.parse import urlparse


def get_fragment(href: str) -> str | None:
    """Return the #fragment of a link, or None.

    Handles both "#anchor" and "https://site.com/page#anchor".
    """
    if not href:
        return None

    parsed = urlparse(href)
    return parsed.fragment or None


def build_anchor_index(rows: list[dict]) -> dict[str, str]:
    """Map every real HTML id in the policy to the segment that contains it."""
    index: dict[str, str] = {}

    for row in rows:
        segment = row["segment"]

        for html_id in segment.get("html_ids", []):
            index[html_id] = segment["id"]

    return index


def build_channel_index(rows: list[dict]) -> dict[str, list[dict]]:
    """Map each segment id to the usable request channels found in it.

    "Not specified" is excluded because it isn't a real channel.
    """
    index: dict[str, list[dict]] = {}

    for row in rows:
        result = row["result"]

        if not result:
            continue

        real_channels = [
            channel
            for channel in result.get("request_channel", [])
            if channel.get("value") != "Not specified"
        ]

        if real_channels:
            index[row["segment"]["id"]] = real_channels

    return index


def resolve_via_link(
    segment: dict,
    anchor_index: dict,
    channel_index: dict,
) -> tuple[list[dict], str] | None:
    """Resolve a reference only when a real HTML link fragment points to a
    segment that contains usable request channels."""
    for link in segment.get("links", []):
        fragment = get_fragment(link.get("href", ""))

        if not fragment:
            continue

        target_segment_id = anchor_index.get(fragment)

        if target_segment_id and target_segment_id in channel_index:
            return channel_index[target_segment_id], "internal_link"

    return None


def resolve_cross_segment_channels(rows: list[dict]) -> list[dict]:
    """Run once after all segments in the policy have been extracted.

    Resolves "Not specified" channels and unresolved references, only when a
    real document link identifies a target segment with usable channels.
    If the target can't be identified reliably, it is left unresolved rather
    than guessed from nearby segments.
    """
    anchor_index = build_anchor_index(rows)
    channel_index = build_channel_index(rows)

    for row in rows:
        segment = row["segment"]
        result = row["result"]

        if not result:
            continue

        for channel in result.get("request_channel", []):
            if channel.get("value") != "Not specified":
                continue

            resolved = resolve_via_link(segment, anchor_index, channel_index)

            if resolved:
                real_channels, method = resolved
                channel["resolved_channels"] = real_channels
                channel["resolution_method"] = method

        for reference in result.get("references", []):
            resolved = resolve_via_link(segment, anchor_index, channel_index)

            if resolved:
                real_channels, method = resolved
                reference["resolved_channels"] = real_channels
                reference["resolution_method"] = method

    return rows