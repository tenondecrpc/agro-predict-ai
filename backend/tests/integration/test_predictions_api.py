from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.predictions.repository import InMemoryPredictionRepository
from backend.predictions.service import PredictionService


def _make_mock_redis() -> MagicMock:
    """Create a mock Redis client that simulates successful enqueue."""
    mock = MagicMock()
    mock.get.return_value = None  # No in-flight jobs
    mock.incr.return_value = 1
    mock.decr.return_value = 0
    mock.hset.return_value = 1
    mock.expire.return_value = True
    return mock


@pytest.fixture
def client() -> TestClient:
    repository = InMemoryPredictionRepository()
    service = PredictionService(repository=repository)
    mock_redis = _make_mock_redis()
    app = create_app(prediction_service=service, redis_client=mock_redis)
    # Mock _enqueue_prediction to avoid needing real ARQ/Redis
    patcher = patch("backend.predictions.api._enqueue_prediction", return_value=None)
    patcher.start()
    test_client = TestClient(app)
    yield test_client
    patcher.stop()


class TestPredictionsAPI:
    def test_create_prediction_success(self, client: TestClient) -> None:
        payload = {
            "tenant_id": "tenant-alpha",
            "team_id": "team-core",
            "crop": "corn",
            "region": "midwest_us",
            "time_horizon_days": 30,
            "input_data": {
                "soil_moisture": 0.35,
                "temperature_c": 22.5,
                "rainfall_mm": 45.0,
            },
        }
        response = client.post("/api/v1/predictions", json=payload)
        # POST now returns 202 Accepted (async dispatch)
        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data
        assert data["status"] in ("queued", "completed")
        assert "status_url" in data

    def test_create_prediction_missing_field(self, client: TestClient) -> None:
        payload = {
            "tenant_id": "tenant-alpha",
            "team_id": "team-core",
            "crop": "corn",
            "region": "midwest_us",
            "time_horizon_days": 30,
        }
        response = client.post("/api/v1/predictions", json=payload)
        assert response.status_code == 422

    def test_create_prediction_stale_data(self, client: TestClient) -> None:
        payload = {
            "tenant_id": "tenant-alpha",
            "team_id": "team-core",
            "crop": "corn",
            "region": "midwest_us",
            "time_horizon_days": 30,
            "input_data": {
                "soil_moisture": 0.35,
                "temperature_c": 22.5,
                "rainfall_mm": 45.0,
                "data_freshness_hours": 72,
            },
        }
        response = client.post("/api/v1/predictions", json=payload)
        # POST now returns 202 Accepted
        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data
        assert data["status"] in ("queued", "completed")

    def test_create_prediction_bad_data_escalates(self, client: TestClient) -> None:
        payload = {
            "tenant_id": "tenant-alpha",
            "team_id": "team-core",
            "crop": "corn",
            "region": "midwest_us",
            "time_horizon_days": 30,
            "input_data": {
                "soil_moisture": 0.35,
                # missing required fields
            },
        }
        response = client.post("/api/v1/predictions", json=payload)
        # POST now returns 202 Accepted (escalation happens async in worker)
        assert response.status_code == 202
        data = response.json()
        assert "run_id" in data

    def test_get_prediction(self, client: TestClient) -> None:
        # Create a prediction via the service directly to populate repository
        from backend.predictions.models import PredictionInput
        from backend.predictions.service import PredictionService

        repository = InMemoryPredictionRepository()
        service = PredictionService(repository=repository)
        app = create_app(prediction_service=service)
        test_client = TestClient(app)

        valid_input = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35, "temperature_c": 22.5, "rainfall_mm": 45.0},
        )
        result = service.execute(valid_input, model_version="v1.2.0")
        prediction_id = result.prediction_id

        # Fetch it via API
        response = test_client.get(f"/api/v1/predictions/{prediction_id}?tenant_id=tenant-alpha")
        assert response.status_code == 200
        data = response.json()
        assert data["prediction_id"] == prediction_id

    def test_get_prediction_not_found(self, client: TestClient) -> None:
        response = client.get("/api/v1/predictions/nonexistent?tenant_id=tenant-alpha")
        assert response.status_code == 404

    def test_list_predictions(self, client: TestClient) -> None:
        from backend.predictions.models import PredictionInput
        from backend.predictions.service import PredictionService

        repository = InMemoryPredictionRepository()
        service = PredictionService(repository=repository)
        app = create_app(prediction_service=service)
        test_client = TestClient(app)

        valid_input = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35, "temperature_c": 22.5, "rainfall_mm": 45.0},
        )
        service.execute(valid_input, model_version="v1.2.0")
        service.execute(valid_input, model_version="v1.2.0")

        response = test_client.get("/api/v1/predictions?tenant_id=tenant-alpha")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
