"""
MODEL_CLIENT - the only file that talks to the API. Split out of
pipeline.py so the orchestration logic there (validate, recover, link)
can be read without the HTTP/error-handling in the way.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from extractor.prompt import API_KEY, BASE_URL, MODEL, SYSTEM_PROMPT
from extractor.schema import ExtractionResponse, empty_response

# One client for the whole run
_client = OpenAI(base_url=BASE_URL, api_key=API_KEY, max_retries=6)


def call_model(user_prompt: str) -> dict[str, Any] | None:
    """
    Asks the model for one segment's extraction, with the response shape
    enforced by the API rather than repaired afterwards. Returns a plain
    dict, or None if the model refused or the call failed.
    """
    try:
        completion = _client.chat.completions.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format=ExtractionResponse,
        )
    except Exception as error:
        print(f"  model call failed after retries: {error}")
        raise

    message = completion.choices[0].message

    if getattr(message, "refusal", None):
        print(f"  model refused: {message.refusal}")
        return None

    if message.parsed is None:
        return empty_response()

    return message.parsed.model_dump()
