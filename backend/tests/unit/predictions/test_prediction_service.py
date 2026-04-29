from __future__ import annotations

import pytest

from backend.predictions.models import PredictionInput, PredictionStatus
from backend.predictions.repository import InMemoryPredictionRepository
from backend.predictions.service import PredictionService


class TestPredictionService:
    @pytest.fixture
    def repository(self) -> InMemoryPredictionRepository:
        return InMemoryPredictionRepository()

    @pytest.fixture
    def service(self, repository: InMemoryPredictionRepository) -> PredictionService:
        return PredictionService(repository=repository)

    @pytest.fixture
    def valid_input(self) -> PredictionInput:
        return PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35, "temperature_c": 22.5, "rainfall_mm": 45.0},
        )

    def test_execute_saves_and_returns_prediction(
        self, service: PredictionService, valid_input: PredictionInput
    ) -> None:
        result = service.execute(valid_input, model_version="v1.2.0")
        assert result.status == PredictionStatus.COMPLETED
        assert result.prediction_id is not None

        # Verify it was saved
        saved = service.repository.get_by_id(result.prediction_id, tenant_id="tenant-alpha")
        assert saved is not None
        assert saved.prediction_id == result.prediction_id

    def test_execute_with_stale_data(self, service: PredictionService) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={
                "soil_moisture": 0.35,
                "temperature_c": 22.5,
                "rainfall_mm": 45.0,
                "data_freshness_hours": 72,
            },
        )
        result = service.execute(inp, model_version="v1.2.0")
        assert result.status == PredictionStatus.COMPLETED
        assert result.explanation_artifact is not None
        assert "stale_data" in result.explanation_artifact.uncertainty_factors

    def test_execute_escalates_on_bad_data(self, service: PredictionService) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35},  # missing required fields
        )
        result = service.execute(inp, model_version="v1.2.0")
        assert result.status == PredictionStatus.ESCALATED
        assert result.escalation_reason is not None

    def test_get_prediction(self, service: PredictionService, valid_input: PredictionInput) -> None:
        result = service.execute(valid_input, model_version="v1.2.0")
        fetched = service.get_prediction(result.prediction_id, tenant_id="tenant-alpha")
        assert fetched is not None
        assert fetched.prediction_id == result.prediction_id

    def test_get_prediction_wrong_tenant(self, service: PredictionService, valid_input: PredictionInput) -> None:
        result = service.execute(valid_input, model_version="v1.2.0")
        fetched = service.get_prediction(result.prediction_id, tenant_id="other-tenant")
        assert fetched is None

    def test_list_predictions_by_tenant(self, service: PredictionService, valid_input: PredictionInput) -> None:
        service.execute(valid_input, model_version="v1.2.0")
        service.execute(valid_input, model_version="v1.2.0")

        results = service.list_predictions(tenant_id="tenant-alpha")
        assert len(results) == 2
