from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.ml_models.models import AccuracyMetrics, ModelStatus, ModelType
from backend.ml_models.repository import InMemoryModelRepository
from backend.ml_models.service import ModelService


class TestModelService:
    @pytest.fixture
    def service(self) -> ModelService:
        return ModelService(repository=InMemoryModelRepository())

    def _sample_metrics(self) -> AccuracyMetrics:
        return AccuracyMetrics(r2_score=0.85, rmse=1.2, mae=0.9)

    def test_register_model(self, service: ModelService) -> None:
        model = service.register(
            version="1.0.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="abc123",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={"soil_moisture": "float", "temperature": "float"},
        )
        assert model.version == "1.0.0"
        assert model.status == ModelStatus.REGISTERED

    def test_register_missing_dataset_hash(self, service: ModelService) -> None:
        with pytest.raises(ValueError, match="dataset_hash"):
            service.register(
                version="1.0.0",
                model_type=ModelType.SKLEARN,
                tenant_id="t1",
                team_id="team-a",
                training_date=datetime.now(UTC).isoformat(),
                dataset_hash="",
                accuracy_metrics=self._sample_metrics(),
                feature_schema={},
            )

    def test_activate_model(self, service: ModelService) -> None:
        model = service.register(
            version="1.0.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="abc123",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        activated = service.activate(model.model_id, tenant_id="t1")
        assert activated.status == ModelStatus.ACTIVE

    def test_rollback(self, service: ModelService) -> None:
        m1 = service.register(
            version="1.0.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="abc123",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        service.activate(m1.model_id, tenant_id="t1")

        m2 = service.register(
            version="1.1.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="def456",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        service.activate(m2.model_id, tenant_id="t1")

        rolled = service.rollback(tenant_id="t1")
        assert rolled is not None
        assert rolled.version == "1.0.0"
        assert rolled.status == ModelStatus.ACTIVE

    def test_shadow_validation(self, service: ModelService) -> None:
        active = service.register(
            version="1.0.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="abc123",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        service.activate(active.model_id, tenant_id="t1")

        shadow = service.register(
            version="1.1.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="def456",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        validation = service.create_shadow_validation(shadow.model_id, tenant_id="t1")
        assert validation.model_id == active.model_id
        assert validation.shadow_model_id == shadow.model_id

    def test_complete_validation_pass(self, service: ModelService) -> None:
        active = service.register(
            version="1.0.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="abc123",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        service.activate(active.model_id, tenant_id="t1")

        shadow = service.register(
            version="1.1.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="def456",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        validation = service.create_shadow_validation(shadow.model_id, tenant_id="t1")
        completed = service.complete_validation(
            validation.validation_id,
            accuracy_delta=0.02,
            comparison={"r2_improvement": 0.02},
        )
        assert completed.status == "completed"
        assert completed.accuracy_delta == 0.02

    def test_complete_validation_fail(self, service: ModelService) -> None:
        active = service.register(
            version="1.0.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="abc123",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        service.activate(active.model_id, tenant_id="t1")

        shadow = service.register(
            version="1.1.0",
            model_type=ModelType.SKLEARN,
            tenant_id="t1",
            team_id="team-a",
            training_date=datetime.now(UTC).isoformat(),
            dataset_hash="def456",
            accuracy_metrics=self._sample_metrics(),
            feature_schema={},
        )
        validation = service.create_shadow_validation(shadow.model_id, tenant_id="t1")
        completed = service.complete_validation(
            validation.validation_id,
            accuracy_delta=-0.05,
            comparison={"r2_regression": -0.05},
        )
        assert completed.status == "failed"
