"""LLM configuration for AgroPredict AI.

Reads configuration from environment variables.
The key itself (LLM_API_KEY) must never be hardcoded or logged in full.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """LLM provider settings, read directly from environment variables."""

    llm_enabled: bool = False
    llm_api_key: str = ""
    llm_api_url: str = "https://opencode.ai/zen/go/v1"
    llm_model_id: str = "minimax-m2.7"
    llm_timeout_seconds: int = 30

    model_config = {"env_prefix": ""}

    def validate_enabled(self) -> None:
        """Raise ValueError when LLM is enabled but no API key is present."""
        if self.llm_enabled and not self.llm_api_key:
            raise ValueError("LLM_API_KEY must be set when LLM_ENABLED=true")

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls()
