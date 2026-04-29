from __future__ import annotations

import pytest

from backend.deployment.models import DeploymentConfig, DeploymentProfile, HPAConfig


class TestDeploymentConfig:
    def test_connected_profile(self) -> None:
        config = DeploymentConfig(profile=DeploymentProfile.CONNECTED)
        assert config.external_services_enabled is True
        assert config.is_air_gapped() is False

    def test_air_gapped_profile(self) -> None:
        config = DeploymentConfig(profile=DeploymentProfile.AIR_GAPPED)
        assert config.external_services_enabled is False
        assert config.is_air_gapped() is True

    def test_hpa_config_valid(self) -> None:
        hpa = HPAConfig(component_name="workers", min_replicas=1, max_replicas=10)
        assert hpa.min_replicas == 1
        assert hpa.max_replicas == 10

    def test_hpa_config_invalid(self) -> None:
        with pytest.raises(ValueError):
            HPAConfig(component_name="workers", min_replicas=5, max_replicas=2)
