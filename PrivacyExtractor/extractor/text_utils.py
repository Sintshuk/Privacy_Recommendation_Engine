"""
TEXT_UTILS - small text-comparison helpers shared across validation and
matching.
"""


def normalise_text(value: str) -> str:
    """Lowercases and collapses whitespace, so text comparisons don't fail on casing/spacing alone."""
    return " ".join(value.lower().split())