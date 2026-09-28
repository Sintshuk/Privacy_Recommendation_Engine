"""
SEGMENTER - turns a privacy-policy source file (HTML or PDF) into
context-preserving segments, using Docling for structural parsing and
token-aware chunking.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import tiktoken
from bs4 import BeautifulSoup, Tag
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

MODEL_NAME = "gpt-4o"
DEFAULT_MAX_TOKENS = 600
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

_converter = DocumentConverter(allowed_formats=[InputFormat.HTML, InputFormat.PDF])

# Docling serialises HTML links like [label](href) - this recovers them.
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# --------------------------------------------------------------------
# Text cleanup
# --------------------------------------------------------------------

def fix_punctuation_spacing(text: str) -> str:
    """'account .' -> 'account.'"""
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def clean_text(text: str) -> str:
    """Collapse whitespace while preserving the wording."""
    return fix_punctuation_spacing(" ".join((text or "").split()))


def normalise_for_match(text: str) -> str:
    """Loose normalisation used ONLY for matching headings/anchors - never as actual evidence text."""
    text = clean_text(text).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def strip_inline_markdown(text: str) -> str:
    """**website** -> website"""
    text = (text or "").replace("**", "").replace("__", "").replace("`", "")
    return clean_text(text)


def docling_text_to_visible_text(raw_text: str) -> str:
    """Strips Docling's Markdown serialization down to the visible policy wording (links preserved separately)."""
    text = raw_text or ""
    text = MARKDOWN_LINK_RE.sub(lambda m: strip_inline_markdown(m.group(1)), text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?m)^\s*[-+*]\s+", "", text)   # bullet markers
    text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)  # heading markers
    return clean_text(text)


def dedupe_headings(headings: list[str] | None) -> list[str]:
    """Docling sometimes repeats a heading two chunks in a row - only consecutive duplicates are removed."""
    result: list[str] = []
    for heading in headings or []:
        heading = clean_text(heading)
        if heading and (not result or normalise_for_match(result[-1]) != normalise_for_match(heading)):
            result.append(heading)
    return result


def is_obvious_ui_noise(text: str) -> bool:
    """Only drops chunks that are nothing but page furniture. Short policy text is kept - no aggressive length filter."""
    obvious_noise = {
        "back to top", "view summary learn more back to top", "view summary",
        "expand all", "collapse all", "print",
    }
    return normalise_for_match(text) in obvious_noise


# --------------------------------------------------------------------
# Links
# --------------------------------------------------------------------

def link_kind(href: str) -> str:
    href = (href or "").strip()
    if href.startswith("#"):
        return "internal"
    if href.lower().startswith("mailto:"):
        return "email"
    if href.lower().startswith("tel:"):
        return "phone"
    return "external"


def extract_links_from_docling_text(raw_text: str) -> list[dict]:
    """Turns Docling's [label](href) markdown links back into {text, href, kind} dicts."""
    links: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for match in MARKDOWN_LINK_RE.finditer(raw_text or ""):
        label = strip_inline_markdown(match.group(1))
        href = match.group(2).strip()

        if not label or not href or (label, href) in seen:
            continue

        seen.add((label, href))
        links.append({"text": label, "href": href, "kind": link_kind(href)})

    return links


def filter_links_to_own_text(segments: list[dict]) -> list[dict]:
    """Keeps only links whose visible label actually occurs in the final cleaned segment text."""
    for segment in segments:
        segment["links"] = [link for link in segment["links"] if link["text"] in segment["text"]]
    return segments


# --------------------------------------------------------------------
# Recovering original HTML anchor ids (HTML only - a PDF has none)
# --------------------------------------------------------------------

CONSENT_WIDGET_TERMS = [
    "onetrust", "consent-banner", "cookie-banner", "cookiebanner",
    "cookie-consent", "cookieconsent", "cc-window",
]


def prepare_html_for_anchor_extraction(html_text: str) -> BeautifulSoup:
    """Parses the ORIGINAL HTML so real element ids can be recovered."""
    soup = BeautifulSoup(html_text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for attr in ("id", "class"):
        for tag in soup.find_all(attrs={attr: True}):
            if tag.parent is None:
                continue
            value = tag.get(attr)
            value = " ".join(value) if isinstance(value, list) else str(value or "")
            if any(term in value.lower() for term in CONSENT_WIDGET_TERMS):
                tag.decompose()

    return soup


def get_search_root(soup: BeautifulSoup) -> Tag:
    """Prefers the main/article part of the page."""
    return soup.find("main") or soup.find("article") or soup.find("body") or soup


def get_anchor_heading(tag: Tag) -> str:
    """Finds the heading text associated with an element that owns an id."""
    if tag.name in HEADING_TAGS:
        return clean_text(tag.get_text(" "))
    heading = tag.find(list(HEADING_TAGS))
    return clean_text(heading.get_text(" ")) if heading is not None else ""


def get_anchor_text_probe(tag: Tag, max_words: int = 30) -> str:
    """A short visible-text fingerprint, used to fall back to when the heading alone isn't unique enough."""
    words = clean_text(tag.get_text(" ")).split()
    return " ".join(words[:max_words])


def extract_anchor_targets(html_text: str) -> list[dict]:
    """Extracts every original HTML id, plus enough context to later match it to a Docling segment."""
    soup = prepare_html_for_anchor_extraction(html_text)
    root = get_search_root(soup)

    targets: list[dict] = []
    seen_ids: set[str] = set()

    tags = ([root] if root.get("id") else []) + root.find_all(attrs={"id": True})

    for tag in tags:
        html_id = str(tag.get("id") or "").strip()
        if not html_id or html_id in seen_ids:
            continue
        seen_ids.add(html_id)

        heading = get_anchor_heading(tag)
        text_probe = get_anchor_text_probe(tag)
        if heading or text_probe:
            targets.append({"id": html_id, "heading": heading, "text_probe": text_probe})

    return targets


def attach_html_ids(segments: list[dict], anchor_targets: list[dict]) -> None:
    """
    Matches each original HTML anchor to a segment, preferring a unique
    heading match and falling back to a source-text fingerprint. This is
    what lets cross_segment.py follow a #fragment link to the right place.
    """
    if not segments:
        return

    heading_index: dict[str, list[int]] = defaultdict(list)
    for index, segment in enumerate(segments):
        headings = segment.get("heading_path", [])
        if headings:
            heading_index[normalise_for_match(headings[-1])].append(index)

    segment_texts = [normalise_for_match(segment["text"]) for segment in segments]

    for target in anchor_targets:
        found_index: int | None = None
        heading = normalise_for_match(target.get("heading", ""))

        if heading:
            candidates = heading_index.get(heading, [])
            if len(candidates) == 1:
                found_index = candidates[0]

        if found_index is None:
            probe_words = normalise_for_match(target.get("text_probe", "")).split()
            for length in (25, 18, 12, 8):
                if len(probe_words) < length:
                    continue
                probe = " ".join(probe_words[:length])
                matches = [i for i, text in enumerate(segment_texts) if probe in text]
                if len(matches) == 1:
                    found_index = matches[0]
                    break

        if found_index is not None and target["id"] not in segments[found_index]["html_ids"]:
            segments[found_index]["html_ids"].append(target["id"])


# --------------------------------------------------------------------
# Docling chunking
# --------------------------------------------------------------------

def build_chunker(max_tokens: int = DEFAULT_MAX_TOKENS) -> HybridChunker:
    """Token-aware chunking using the tokenizer for our model."""
    tokenizer = OpenAITokenizer(tokenizer=tiktoken.encoding_for_model(MODEL_NAME), max_tokens=max_tokens)
    return HybridChunker(tokenizer=tokenizer, merge_peers=True)


def chunks_to_segments(chunks) -> list[dict]:
    """Docling chunks -> our segment dicts, before ids/prev-next are assigned. Shared by the HTML and PDF entry points."""
    segments: list[dict] = []

    for chunk in chunks:
        raw_text = chunk.text or ""
        visible_text = docling_text_to_visible_text(raw_text)

        if not visible_text or is_obvious_ui_noise(visible_text):
            continue

        segments.append({
            "id": "",
            "text": visible_text,
            "heading_path": dedupe_headings(getattr(chunk.meta, "headings", None)),
            "links": extract_links_from_docling_text(raw_text),
            "html_ids": [],
        })

    return segments


def finalize_segments(segments: list[dict]) -> list[dict]:
    """Assigns contiguous ids, previous/next links, and runs the final link safety pass."""
    for index, segment in enumerate(segments, start=1):
        segment["id"] = f"S{index}"

    for index, segment in enumerate(segments):
        segment["previous_segment_id"] = segments[index - 1]["id"] if index > 0 else None
        segment["next_segment_id"] = segments[index + 1]["id"] if index < len(segments) - 1 else None

    return filter_links_to_own_text(segments)


# --------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------

def segment_policy_html(html_text: str, *, max_tokens: int = DEFAULT_MAX_TOKENS) -> list[dict]:
    """Converts privacy-policy HTML into context-preserving segments."""
    result = _converter.convert_string(content=html_text, format=InputFormat.HTML, name="privacy_policy.html")

    chunker = build_chunker(max_tokens=max_tokens)
    chunks = list(chunker.chunk(dl_doc=result.document))
    segments = chunks_to_segments(chunks)

    # HTML-only step: a PDF has no original-source anchor ids to recover.
    attach_html_ids(segments, extract_anchor_targets(html_text))

    return finalize_segments(segments)


def segment_policy_pdf(pdf_path: str, *, max_tokens: int = DEFAULT_MAX_TOKENS) -> list[dict]:
    """
    Converts a privacy-policy PDF into the same segment schema as
    segment_policy_html.
    """
    result = _converter.convert(pdf_path)

    chunker = build_chunker(max_tokens=max_tokens)
    chunks = list(chunker.chunk(dl_doc=result.document))
    segments = chunks_to_segments(chunks)

    return finalize_segments(segments)


def segment_policy_file(path: str, *, max_tokens: int = DEFAULT_MAX_TOKENS) -> list[dict]:
    """Dispatches by file extension - the single entry point everything else should call."""
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        return segment_policy_pdf(path, max_tokens=max_tokens)

    if suffix in (".html", ".htm"):
        html_text = Path(path).read_text(encoding="utf-8", errors="replace")
        return segment_policy_html(html_text, max_tokens=max_tokens)

    raise ValueError(f"Unsupported file type: {path!r} (expected .html, .htm, or .pdf)")