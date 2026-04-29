from __future__ import annotations

import pytest

from backend.observability.logger import StructuredLogger


class TestStructuredLogger:
    @pytest.fixture
    def logger(self) -> StructuredLogger:
        return StructuredLogger()

    def test_log_agent_execution(self, logger: StructuredLogger) -> None:
        entry = logger.log_agent_execution(
            tenant_id="t1",
            prediction_id="pred-123",
            agent_name="data_analyst",
            duration_ms=150,
            status="success",
        )
        assert entry["tenant_id"] == "t1"
        assert entry["agent_name"] == "data_analyst"
        assert entry["level"] == "info"

    def test_log_agent_execution_error(self, logger: StructuredLogger) -> None:
        entry = logger.log_agent_execution(
            tenant_id="t1",
            prediction_id="pred-123",
            agent_name="ml_executor",
            duration_ms=200,
            status="failure",
            error_message="Model unavailable",
        )
        assert entry["level"] == "error"
        assert entry["error_message"] == "Model unavailable"

    def test_log_prediction(self, logger: StructuredLogger) -> None:
        entry = logger.log_prediction(
            tenant_id="t1",
            prediction_id="pred-123",
            model_version="v1.2.0",
            status="completed",
            duration_ms=5000,
        )
        assert entry["prediction_id"] == "pred-123"
        assert entry["model_version"] == "v1.2.0"
