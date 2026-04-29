"""LLM adapter for AgroPredict AI.

Provides an OpenAI-compatible HTTP adapter with circuit breaker protection
and a disabled no-op adapter for when LLM_ENABLED=false.

The API key is NEVER logged or stored in plain text. Logs show only 'sk-***'.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Protocol, runtime_checkable

from backend.llm.config import LLMConfig

logger = logging.getLogger(__name__)

_CIRCUIT_OPEN_AFTER_FAILURES = 3
_CIRCUIT_RESET_AFTER_SECONDS = 60


@runtime_checkable
class LLMAdapter(Protocol):
    """Protocol for LLM completion adapters."""

    def complete(self, prompt: str, system: str) -> str: ...


class DisabledAdapter:
    """No-op adapter returned when LLM_ENABLED=false."""

    def complete(self, prompt: str, system: str) -> str:
        return ""


class OpenAICompatibleAdapter:
    """HTTP adapter for any OpenAI-compatible LLM API.

    - Uses httpx.Client for synchronous HTTP.
    - Applies a circuit breaker that opens after 3 consecutive failures
      and resets after 60 seconds.
    - The API key value is NEVER logged. Only 'sk-***' appears in logs.
    """

    def __init__(self, config: LLMConfig) -> None:
        import httpx

        self._config = config
        self._client = httpx.Client(
            base_url=config.llm_api_url,
            headers={
                "Authorization": f"Bearer {config.llm_api_key}",
                "Content-Type": "application/json",
            },
            timeout=config.llm_timeout_seconds,
        )

        # Circuit breaker state
        self._failure_count = 0
        self._circuit_opened_at: float | None = None

        # Log redacted key hint for audit trail - never log the real key
        masked = "sk-***" if config.llm_api_key else "(empty)"
        logger.info(
            "llm_adapter_initialized",
            extra={
                "api_url": config.llm_api_url,
                "model_id": config.llm_model_id,
                "key_hint": masked,
            },
        )

    def _is_circuit_open(self) -> bool:
        if self._circuit_opened_at is None:
            return False
        elapsed = time.monotonic() - self._circuit_opened_at
        if elapsed >= _CIRCUIT_RESET_AFTER_SECONDS:
            # Auto-reset
            self._failure_count = 0
            self._circuit_opened_at = None
            return False
        return True

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= _CIRCUIT_OPEN_AFTER_FAILURES:
            self._circuit_opened_at = time.monotonic()
            logger.warning(
                "llm_circuit_breaker_opened",
                extra={"failure_count": self._failure_count},
            )

    def _record_success(self) -> None:
        self._failure_count = 0
        self._circuit_opened_at = None

    def complete(self, prompt: str, system: str) -> str:
        if self._is_circuit_open():
            logger.warning("llm_circuit_breaker_open_skipping_call")
            raise RuntimeError("LLM circuit breaker is open")

        payload = {
            "model": self._config.llm_model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }

        try:
            response = self._client.post("/chat/completions", content=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            self._record_success()
            return text
        except Exception as exc:
            self._record_failure()
            logger.warning(
                "llm_completion_failed",
                extra={"error": str(exc), "failure_count": self._failure_count},
            )
            raise


def build_llm_adapter(config: LLMConfig) -> LLMAdapter:
    """Factory: returns the appropriate adapter based on config."""
    if not config.llm_enabled:
        return DisabledAdapter()
    config.validate_enabled()
    return OpenAICompatibleAdapter(config)
