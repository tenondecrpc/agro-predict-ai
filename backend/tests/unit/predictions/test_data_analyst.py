from __future__ import annotations

import pytest

from backend.predictions.agents.data_analyst import DataAnalystAgent, DataQualityError
from backend.predictions.models import PredictionInput


class TestDataAnalystAgent:
    @pytest.fixture
    def agent(self) -> DataAnalystAgent:
        return DataAnalystAgent()

    def test_valid_data(self, agent: DataAnalystAgent) -> None:
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
            },
        )
        result = agent.execute(inp)
        assert result["validated"] is True
        assert result["input_data_hash"] == inp.input_data_hash
        assert "data_sources" in result
        assert result["uncertainty_flagged"] is False

    def test_missing_required_field(self, agent: DataAnalystAgent) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={
                "soil_moisture": 0.35,
                # missing temperature_c which is required for corn/midwest_us
            },
        )
        with pytest.raises(DataQualityError) as exc_info:
            agent.execute(inp)
        assert "temperature_c" in str(exc_info.value)
        assert exc_info.value.uncertainty_flagged is True

    def test_stale_data(self, agent: DataAnalystAgent) -> None:
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
                "data_freshness_hours": 72,  # stale (>48h)
            },
        )
        result = agent.execute(inp)
        assert result["validated"] is True
        assert result["uncertainty_flagged"] is True
        assert "stale_data" in result["uncertainty_reasons"]

    def test_contradictory_data(self, agent: DataAnalystAgent) -> None:
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
                "soil_moisture_secondary": 0.15,  # contradicts primary
            },
        )
        with pytest.raises(DataQualityError) as exc_info:
            agent.execute(inp)
        assert "contradiction" in str(exc_info.value).lower()
        assert exc_info.value.escalate is True

    def test_computes_provenance(self, agent: DataAnalystAgent) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35, "temperature_c": 22.5, "rainfall_mm": 45.0},
        )
        result = agent.execute(inp)
        provenance = result["data_sources"]
        assert len(provenance) >= 1
        assert all("source_id" in p for p in provenance)
        assert all("validation_status" in p for p in provenance)
        assert all("checksum" in p for p in provenance)
