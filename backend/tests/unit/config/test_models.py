from __future__ import annotations

from backend.config.models import ConfigAudit, ConfigEntry


class TestConfigEntry:
    def test_create(self) -> None:
        cfg = ConfigEntry(
            config_key="max_predictions_per_hour",
            config_value="100",
            tenant_id="t1",
            created_by="admin",
        )
        assert cfg.version == 1
        assert cfg.active is True

    def test_update(self) -> None:
        cfg = ConfigEntry(
            config_key="max_predictions_per_hour",
            config_value="100",
            tenant_id="t1",
            created_by="admin",
        )
        new_cfg = cfg.update("200", changed_by="admin")
        assert new_cfg.version == 2
        assert new_cfg.config_value == "200"


class TestConfigAudit:
    def test_audit_creation(self) -> None:
        audit = ConfigAudit(
            config_id="cfg-123",
            version=2,
            action="update",
            performed_by="admin",
            details={"old_value": "100", "new_value": "200"},
        )
        assert audit.action == "update"
        assert audit.performed_by == "admin"
