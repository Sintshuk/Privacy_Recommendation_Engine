"""
PROMPT - LLM communication: connection settings, the
system/user prompt text, and turning our vocabulary data into readable
text for the model to read.
"""

import os

from dotenv import load_dotenv

from extractor.vocabulary import RIGHT_TYPE, CHOICE_TYPE, REQUEST_CHANNEL

load_dotenv()

BASE_URL = "https://api.openai.com/v1"
API_KEY = os.environ["OPENAI_API_KEY"]
MODEL = "gpt-4o" # Model used


def format_vocab_block(vocab_dict: dict, attribute_name: str) -> str:
    """Turns one vocabulary dict (e.g. RIGHT_TYPE) into a readable list for the prompt."""
    lines = [f"{attribute_name} — choose only from these exact values:"]

    for value, information in vocab_dict.items():
        description = information.get("description", "")
        line = f'- "{value}": {description}'

        examples = information.get("examples", [])
        if examples:
            short_examples = "; ".join(f'"{e}"' for e in examples[:2])
            line += f" Examples: {short_examples}"

        note = information.get("note")
        if note:
            line += f" Note: {note}"

        lines.append(line)

    return "\n".join(lines)


def build_vocab_section() -> str:
    """Combines all three vocabularies (rights, choices, channels) into one block for the prompt."""
    return "\n\n".join([
        format_vocab_block(RIGHT_TYPE, "right_type"),
        format_vocab_block(CHOICE_TYPE, "choice_type"),
        format_vocab_block(REQUEST_CHANNEL, "request_channel"),
    ])


SYSTEM_PROMPT = """
You are a privacy-policy analyst extracting privacy rights,
privacy choices, request channels, and unresolved references.

Follow these rules exactly:

1. Extract only information explicitly stated in the current Segment Text.

2. Attribute values must exactly match the supplied closed vocabulary.
   Read every value's description, examples, and note before choosing.

3. Every extracted value must have an exact verbatim evidence quote copied
   from the current Segment Text.

4. Use previous-segment context only to understand whether the current
   segment continues a formal rights list. Evidence must still come from
   the current Segment Text.

5. A formal rights list may introduce the legal context once and then list
   rights in later sentences without repeating the words "right to".

6. Product controls such as dashboards, account pages, app settings,
   websites, device settings, and in-product features are normally choices,
   not formal legal rights. Consent withdrawal is always choice_type
   "Change or withdraw consent," even if the source calls it a "right."

7. Do not extract both a formal right and an ordinary choice from the same
   action when the passage is clearly part of a formal rights list.

8. A direct webpage, form, dashboard, account page, app, settings page,
   browser setting, phone number, email address, or postal address can be
   a request channel.

9. An unresolved reference points to information located elsewhere
   ("see the How to contact us section", "as described above").

10. A hyperlink or instruction you can act on directly - "visit this
    web form", "sign in to OneDrive", "you can request a copy" - is a
    mechanism, not a reference, even if phrased as a request.

11. Empty lists are a correct answer. Most segments have nothing to
    extract. Do not stretch a value to fit - missing an extraction is
    recoverable, inventing one is not.

12. Use the most specific vocabulary value available. If a sentence
    names several distinct items - data types, controls, or rights -
    extract each as its own entry, don't bundle them under one generic
    value. This applies to rights too: "access, update and amend" is
    two rights (access + rectification), not one.

13. Give each right_type/choice_type/request_channel entry a local id
    ("r1", "c1", "ch1"). For request_channel, add "applies_to": the
    local ids of the right(s)/choice(s) it belongs to, or [] if unclear.
""".strip()


USER_TEMPLATE = """
Before annotating, review every value in the vocabulary below, including
its description and examples - do not default to the first plausible
value or a generic one if a more specific value fits the evidence better.

{vocab_block}

Previous segment context:
<PREVIOUS_SEGMENT>
{previous_segment_text}
</PREVIOUS_SEGMENT>

Current heading path:
{heading_path}

HTML links found inside the current segment:
{links}

The HTML links may help identify whether visible linked text is a webpage,
form, dashboard, account page, email link, or phone link.

Evidence must still be exact visible wording from the current Segment Text.

Current Segment Text:
<SEGMENT>
{segment_text}
</SEGMENT>

Use empty lists when nothing applies. The response shape is enforced
automatically, so return the fields themselves and nothing else.
""".strip()