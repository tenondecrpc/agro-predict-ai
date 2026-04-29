"""Shared helpers for procurement LLM agents.

Each procurement agent follows the same pattern:

1. Build a structured prompt from typed inputs.
2. Call ``LLMAdapter.complete(prompt, system)``.
3. Parse the response (JSON for structured agents, plain text for the
   negotiator).
4. Validate against a Pydantic model.
5. On any failure - LLM disabled, circuit open, malformed JSON,
   validation error - fall back to a deterministic implementation that
   still produces a useful (if simpler) result.

This file centralizes the JSON extraction + Pydantic validation logic
so every agent shares the same robustness.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from backend.llm.adapter import DisabledAdapter, LLMAdapter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def is_llm_available(adapter: LLMAdapter) -> bool:
    return not isinstance(adapter, DisabledAdapter)


def extract_json(raw: str) -> Any:
    """Pull the first JSON object/array out of an LLM response.

    LLMs often wrap JSON in markdown fences, prepend prose, or trail
    commentary. This function:

    1. Tries to parse the whole response as JSON.
    2. Falls back to extracting from a ```json ... ``` fenced block.
    3. Falls back to the first ``{...}`` or ``[...]`` substring.

    Raises ``ValueError`` if no JSON can be extracted.
    """
    if not raw or not raw.strip():
        raise ValueError("empty response")

    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = _JSON_FENCE_RE.search(raw)
    if match:
        body = match.group(1).strip()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass

    # Try the first JSON object substring
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = raw.find(start_char)
        end = raw.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(raw[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError("no JSON object/array found in response")


def validate_to_model(data: Any, model: type[T]) -> T:  # noqa: UP047
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        logger.warning("llm_output_validation_failed: %s", exc)
        raise


def safe_complete(adapter: LLMAdapter, *, system: str, prompt: str) -> str | None:
    """Call the adapter, returning None on any failure (logged).

    The adapter's circuit breaker handles cascading failures upstream;
    this wrapper protects the agent from raising into the API layer.
    """
    if not is_llm_available(adapter):
        return None
    try:
        return adapter.complete(prompt=prompt, system=system)
    except Exception as exc:  # noqa: BLE001
        logger.warning("llm_call_failed: %s", exc)
        return None
