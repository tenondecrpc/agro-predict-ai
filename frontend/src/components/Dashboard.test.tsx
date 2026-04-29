import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AgentHealthPanel from "../components/AgentHealthPanel";
import FeatureFlagManager from "../components/FeatureFlagManager";
import PredictionList from "../components/PredictionList";
import TenantManager from "../components/TenantManager";

const AGENT_NAMES = ["data_analyst", "ml_executor", "recommendation_engine", "explainability", "reviewer"];

const makeHealthResponse = (status = "healthy") => ({
  agents: Object.fromEntries(
    AGENT_NAMES.map((name) => [
      name,
      {
        status,
        last_executed_at: null,
        p95_latency_ms: null,
        error_rate_15m: 0,
        total_executions_15m: 0,
        active_degradation_flags: [],
      },
    ])
  ),
});

describe("PredictionList", () => {
  it("renders prediction list header", () => {
    render(<PredictionList tenantId="t1" />);
    expect(screen.getByText("Predictions")).toBeInTheDocument();
  });

  it("has filter dropdown", () => {
    render(<PredictionList tenantId="t1" />);
    expect(screen.getByLabelText("Filter predictions by status")).toBeInTheDocument();
  });
});

describe("AgentHealthPanel", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => makeHealthResponse("healthy"),
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders all 5 agents", async () => {
    render(<AgentHealthPanel />);
    for (const name of AGENT_NAMES) {
      await waitFor(() => expect(screen.getByText(name)).toBeInTheDocument());
    }
  });

  it("shows healthy status", async () => {
    render(<AgentHealthPanel />);
    await waitFor(() => {
      const statuses = screen.getAllByText("Healthy");
      expect(statuses.length).toBe(5);
    });
  });
});

describe("TenantManager", () => {
  it("renders existing tenants", () => {
    render(<TenantManager />);
    expect(screen.getByText("Alpha Corp")).toBeInTheDocument();
    expect(screen.getByText("Beta Farms")).toBeInTheDocument();
  });

  it("can add a tenant", async () => {
    render(<TenantManager />);
    const input = screen.getByLabelText("New tenant name");
    await userEvent.type(input, "Gamma Agro");
    await userEvent.click(screen.getByText("Create Tenant"));
    expect(screen.getByText("Gamma Agro")).toBeInTheDocument();
  });
});

describe("FeatureFlagManager", () => {
  it("renders feature flags", () => {
    render(<FeatureFlagManager />);
    expect(screen.getByText("new_prediction_model")).toBeInTheDocument();
    expect(screen.getByText("advanced_explainability")).toBeInTheDocument();
  });

  it("can toggle a flag", async () => {
    render(<FeatureFlagManager />);
    const toggleBtn = screen.getAllByText("Enable")[0];
    await userEvent.click(toggleBtn);
    expect(screen.getAllByText("Disable").length).toBeGreaterThan(0);
  });
});
