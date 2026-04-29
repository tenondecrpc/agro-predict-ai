from __future__ import annotations

from backend.security.models import BreakGlassEvent, Secret


class TestSecret:
    def test_needs_rotation(self) -> None:
        from datetime import UTC, datetime, timedelta
        secret = Secret(
            vault_path="secret/data/db",
            secret_type="database",
            rotation_schedule_days=30,
            last_rotated_at=datetime.now(UTC) - timedelta(days=31),
        )
        assert secret.needs_rotation() is True

    def test_no_rotation_needed(self) -> None:
        from datetime import UTC, datetime
        secret = Secret(
            vault_path="secret/data/db",
            secret_type="database",
            last_rotated_at=datetime.now(UTC),
        )
        assert secret.needs_rotation() is False


class TestBreakGlassEvent:
    def test_dual_approval(self) -> None:
        event = BreakGlassEvent(requested_by="user-a", action_taken="access_secret")
        event.approve("admin-1")
        assert event.status == "pending"
        assert event.is_fully_approved() is False
        event.approve("admin-2")
        assert event.status == "approved"
        assert event.is_fully_approved() is True

    def test_same_approver_twice(self) -> None:
        event = BreakGlassEvent(requested_by="user-a", action_taken="access_secret")
        event.approve("admin-1")
        event.approve("admin-1")
        assert event.status == "pending"
        assert event.is_fully_approved() is False
