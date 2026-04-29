from __future__ import annotations

from backend.tenancy.models import QuotaTracker, Team, Tenant, TenantContext


class TestTenant:
    def test_tenant_budget(self) -> None:
        tenant = Tenant(name="Acme Corp", budget_limit=1000.0)
        assert tenant.has_budget(500.0) is True
        tenant.consume_budget(500.0)
        assert tenant.has_budget(600.0) is False
        assert tenant.has_budget(500.0) is True

    def test_unlimited_budget(self) -> None:
        tenant = Tenant(name="Acme Corp", budget_limit=0.0)
        assert tenant.has_budget(99999.0) is True


class TestTeam:
    def test_team_budget(self) -> None:
        team = Team(tenant_id="t1", name="Team A", budget_limit=100.0)
        assert team.has_budget(50.0) is True
        team.consume_budget(50.0)
        assert team.has_budget(60.0) is False


class TestTenantContext:
    def test_context_creation(self) -> None:
        ctx = TenantContext(tenant_id="t1", team_id="team-a")
        assert ctx.tenant_id == "t1"
        assert ctx.scope_level == "team"


class TestQuotaTracker:
    def test_check_and_consume(self) -> None:
        tracker = QuotaTracker()
        assert tracker.check_and_consume("team-a", "predictions", 3) is True
        assert tracker.check_and_consume("team-a", "predictions", 3) is True
        assert tracker.check_and_consume("team-a", "predictions", 3) is True
        assert tracker.check_and_consume("team-a", "predictions", 3) is False

    def test_usage_tracking(self) -> None:
        tracker = QuotaTracker()
        tracker.check_and_consume("team-a", "predictions", 10)
        tracker.check_and_consume("team-a", "predictions", 10)
        assert tracker.get_usage("team-a", "predictions") == 2

    def test_reset(self) -> None:
        tracker = QuotaTracker()
        tracker.check_and_consume("team-a", "predictions", 1)
        assert tracker.check_and_consume("team-a", "predictions", 1) is False
        tracker.reset("team-a", "predictions")
        assert tracker.check_and_consume("team-a", "predictions", 1) is True
