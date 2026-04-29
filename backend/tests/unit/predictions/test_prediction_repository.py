from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.predictions.models import (
    DataProvenanceEntry,
    ExplanationArtifactModel,
    PredictionInput,
    PredictionOutput,
    PredictionStatus,
)
from backend.predictions.repository import InMemoryPredictionRepository, PredictionRepository


class TestInMemoryPredictionRepository:
    @pytest.fixture
    def repo(self) -> InMemoryPredictionRepository:
        return InMemoryPredictionRepository()

    @pytest.fixture
    def sample_input(self) -> PredictionInput:
        return PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35},
        )

    @pytest.fixture
    def sample_output(self, sample_input: PredictionInput) -> PredictionOutput:
        return PredictionOutput(
            prediction_id="pred-123",
            tenant_id=sample_input.tenant_id,
            model_version="v1.2.0",
            status=PredictionStatus.COMPLETED,
            output={"yield_tons_per_hectare": 8.5},
            confidence_interval={"lower": 7.2, "upper": 9.8},
            feature_importance={"soil_moisture": 0.45},
            data_provenance=[
                DataProvenanceEntry(
                    source_id="weather-001",
                    ingested_at=datetime.now(UTC),
                    validation_status="passed",
                    checksum="abc",
                )
            ],
            explanation_artifact=ExplanationArtifactModel(
                feature_scores={"soil_moisture": 0.45},
                data_sources_used=["weather-001"],
                confidence_level=0.85,
                uncertainty_factors=[],
                human_readable_summary="Good yield expected.",
            ),
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

    def test_save_and_get_by_id(self, repo: InMemoryPredictionRepository, sample_output: PredictionOutput) -> None:
        saved = repo.save(sample_output)
        assert saved.prediction_id == "pred-123"

        retrieved = repo.get_by_id("pred-123", tenant_id="tenant-alpha")
        assert retrieved is not None
        assert retrieved.prediction_id == "pred-123"

    def test_get_by_id_wrong_tenant(self, repo: InMemoryPredictionRepository, sample_output: PredictionOutput) -> None:
        repo.save(sample_output)
        retrieved = repo.get_by_id("pred-123", tenant_id="other-tenant")
        assert retrieved is None

    def test_get_by_id_not_found(self, repo: InMemoryPredictionRepository) -> None:
        retrieved = repo.get_by_id("nonexistent", tenant_id="tenant-alpha")
        assert retrieved is None

    def test_list_by_tenant(self, repo: InMemoryPredictionRepository, sample_output: PredictionOutput) -> None:
        repo.save(sample_output)
        repo.save(
            PredictionOutput(
                prediction_id="pred-456",
                tenant_id="tenant-alpha",
                model_version="v1.2.0",
                status=PredictionStatus.COMPLETED,
                output={"yield_tons_per_hectare": 9.0},
                confidence_interval={"lower": 8.0, "upper": 10.0},
                feature_importance={},
                data_provenance=[],
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
        )
        repo.save(
            PredictionOutput(
                prediction_id="pred-789",
                tenant_id="tenant-beta",
                model_version="v1.2.0",
                status=PredictionStatus.COMPLETED,
                output={},
                confidence_interval=None,
                feature_importance={},
                data_provenance=[],
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
        )

        results = repo.list_by_tenant("tenant-alpha")
        assert len(results) == 2
        assert {r.prediction_id for r in results} == {"pred-123", "pred-456"}

    def test_list_by_tenant_empty(self, repo: InMemoryPredictionRepository) -> None:
        results = repo.list_by_tenant("tenant-alpha")
        assert results == []

    def test_update_existing(self, repo: InMemoryPredictionRepository, sample_output: PredictionOutput) -> None:
        repo.save(sample_output)
        updated = sample_output.model_copy(update={"status": PredictionStatus.FAILED})
        repo.save(updated)

        retrieved = repo.get_by_id("pred-123", tenant_id="tenant-alpha")
        assert retrieved is not None
        assert retrieved.status == PredictionStatus.FAILED

    def test_is_prediction_repository(self, repo: InMemoryPredictionRepository) -> None:
        assert isinstance(repo, PredictionRepository)
