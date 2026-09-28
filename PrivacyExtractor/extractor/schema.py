"""
SCHEMA - the contract for what the model is allowed to return.

value fields are Literal enums built FROM vocabulary.py at import time,
not free strings. OpenAI structured outputs enforces an enum at decode
time, so the model cannot return a value outside the vocabulary - e.g.
it can no longer paraphrase "Right of access" as "Right to access".

Because the enums are generated from vocabulary.py, editing the
vocabulary automatically updates this contract. Nothing here needs
manual editing when you add or rename a value.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from extractor.vocabulary import RIGHT_TYPE, CHOICE_TYPE, REQUEST_CHANNEL

RightValue = Literal[tuple(RIGHT_TYPE.keys())]
ChoiceValue = Literal[tuple(CHOICE_TYPE.keys())]
ChannelValue = Literal[tuple(REQUEST_CHANNEL.keys())]


class RightEntry(BaseModel):
    id: str = Field(description="Short local label unique within this response, e.g. 'r1'.")
    value: RightValue = Field(description="One of the allowed right_type values.")
    evidence: str = Field(description="Exact verbatim quote copied from the Segment Text.")


class ChoiceEntry(BaseModel):
    id: str = Field(description="Short local label unique within this response, e.g. 'c1'.")
    value: ChoiceValue = Field(description="One of the allowed choice_type values.")
    evidence: str = Field(description="Exact verbatim quote copied from the Segment Text.")


class Channel(BaseModel):
    id: str = Field(description="Short local label unique within this response, e.g. 'ch1'.")
    value: ChannelValue = Field(description="One of the allowed request_channel values.")
    evidence: str = Field(description="Exact verbatim quote copied from the Segment Text.")
    applies_to: list[str] = Field(
        description="Local ids of the right(s)/choice(s) this channel serves. Empty list if unclear.",
    )


class Reference(BaseModel):
    evidence: str = Field(description="Exact verbatim quote copied from the Segment Text.")
    target_text: str = Field(description="What the reference points at, e.g. 'How to contact us'.")


class ExtractionResponse(BaseModel):
    """The complete per-segment response. Empty lists when nothing applies."""

    right_type: list[RightEntry]
    choice_type: list[ChoiceEntry]
    request_channel: list[Channel]
    references: list[Reference]


def empty_response() -> dict:
    """The canonical 'nothing found here' result, so abstention is representable."""
    return {"right_type": [], "choice_type": [], "request_channel": [], "references": []}