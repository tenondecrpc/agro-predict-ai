import { describe, expect, it } from "vitest";

import { activeGraphCandidate, invalidGraphCandidate } from "../data/sampleData";
import {
  buildSimulationPlan,
  getSimulationOfficeState,
  getSimulationAgentVisual,
  simulateAgentNarration,
} from "./graphSimulator";
import type { GraphCandidate } from "../data/sampleData";

const emptyCandidate: GraphCandidate = {
  profileId: "empty",
  nodes: [],
  edges: [],
};

describe("buildSimulationPlan", () => {
  it("produces a valid plan from the active graph candidate", () => {
    const plan = buildSimulationPlan(activeGraphCandidate);
    expect(plan.protectedInvariantErrors).toHaveLength(0);
    expect(plan.steps).toHaveLength(8);
    expect(plan.steps[0].nodeId).toBe("ingest_event");
    expect(plan.steps[0].visualAgent.spritePath).toBe("/assets/sprites/agent_a.png");
    expect(plan.steps[0].office.phase).toBe("intake");
    expect(plan.steps[0].office.activeAgents).toEqual(["data_analyst"]);
    expect(plan.steps[plan.steps.length - 1].nodeId).toBe("publish_recommendation");
    expect(plan.steps[plan.steps.length - 1].emitsRecommendation).toBe(true);
  });

  it("orders the data quality gate before analysis in the plan", () => {
    const plan = buildSimulationPlan(activeGraphCandidate);
    const qualityIdx = plan.steps.findIndex((s) => s.nodeId === "validate_sources");
    const analystIdx = plan.steps.findIndex((s) => s.nodeId === "data_analyst");
    expect(qualityIdx).toBeGreaterThanOrEqual(0);
    expect(analystIdx).toBeGreaterThan(qualityIdx);
  });

  it("orders model, recommendation, explainability, and review before release", () => {
    const plan = buildSimulationPlan(activeGraphCandidate);
    const releaseIdx = plan.steps.findIndex((s) => s.nodeId === "publish_recommendation");
    expect(releaseIdx).toBeGreaterThan(0);
    for (const required of ["ml_executor", "recommendation_engine", "explainability", "reviewer"]) {
      const reqIdx = plan.steps.findIndex((s) => s.nodeId === required);
      expect(reqIdx).toBeGreaterThanOrEqual(0);
      expect(reqIdx).toBeLessThan(releaseIdx);
    }
  });

  it("returns errors and empty steps for the invalid graph candidate", () => {
    const plan = buildSimulationPlan(invalidGraphCandidate);
    expect(plan.steps).toHaveLength(0);
    expect(plan.protectedInvariantErrors.length).toBeGreaterThan(0);
  });

  it("short-circuits on structural failure with empty candidate", () => {
    const plan = buildSimulationPlan(emptyCandidate);
    expect(plan.steps).toHaveLength(0);
    expect(plan.protectedInvariantErrors.length).toBeGreaterThan(0);
  });

  it("returns errors for a candidate that violates traversal order", () => {
    const swapped: GraphCandidate = {
      ...activeGraphCandidate,
      nodes: activeGraphCandidate.nodes.map((n) => {
        if (n.id === "data_analyst") return { ...n, id: "validate_sources", label: "Data Quality Gate" };
        if (n.id === "validate_sources") return { ...n, id: "data_analyst", label: "Data Analyst" };
        return n;
      }),
      edges: activeGraphCandidate.edges.map((e) => {
        const flip = (v: string) =>
          v === "data_analyst" ? "validate_sources" : v === "validate_sources" ? "data_analyst" : v;
        return { ...e, from: flip(e.from), to: flip(e.to) };
      }),
    };
    const plan = buildSimulationPlan(swapped);
    expect(plan.steps).toHaveLength(0);
    expect(
      plan.protectedInvariantErrors.some((e) => e.includes("data_analyst") && e.includes("validate_sources")),
    ).toBe(true);
  });
});

describe("getSimulationOfficeState", () => {
  it("maps data analysis to a data analyst and reviewer operations interaction", () => {
    expect(getSimulationOfficeState("data_analyst")).toMatchObject({
      phase: "analysis",
      activeAgents: ["data_analyst", "reviewer"],
      carrier: "data_analyst",
    });
  });

  it("maps recommendation drafting to model and recommendation agents", () => {
    expect(getSimulationOfficeState("recommendation_engine")).toMatchObject({
      phase: "recommendation",
      activeAgents: ["ml_executor", "recommendation_engine"],
      carrier: "recommendation_engine",
    });
  });

  it("falls back to a data analyst-led custom office state for unknown nodes", () => {
    expect(getSimulationOfficeState("unknown_node_xyz")).toMatchObject({
      phase: "intake",
      activeAgents: ["data_analyst"],
    });
  });
});

describe("getSimulationAgentVisual", () => {
  it("maps known runtime nodes to bundled PNG sprite sheets", () => {
    expect(getSimulationAgentVisual("ml_executor")).toMatchObject({
      role: "ml_executor",
      spritePath: "/assets/sprites/agent_c.png",
    });
    expect(getSimulationAgentVisual("recommendation_engine")).toMatchObject({
      role: "recommendation_engine",
      spritePath: "/assets/sprites/agent_d.png",
    });
    expect(getSimulationAgentVisual("reviewer")).toMatchObject({
      role: "reviewer",
      spritePath: "/assets/sprites/agent_b.png",
    });
  });

  it("falls back to the data analyst visual for unknown nodes", () => {
    expect(getSimulationAgentVisual("unknown_node_xyz")).toMatchObject({
      role: "data_analyst",
      spritePath: "/assets/sprites/agent_a.png",
    });
  });
});

describe("simulateAgentNarration", () => {
  const knownNodeIds = [
    "ingest_event",
    "validate_sources",
    "data_analyst",
    "ml_executor",
    "recommendation_engine",
    "explainability",
    "reviewer",
    "publish_recommendation",
  ];

  it("returns a non-empty stable string for each known node ID", () => {
    for (const nodeId of knownNodeIds) {
      const first = simulateAgentNarration(nodeId);
      const second = simulateAgentNarration(nodeId);
      expect(first).toBe(second);
      expect(first.length).toBeGreaterThan(0);
    }
  });

  it("returns a fallback that includes the node ID for unknown nodes", () => {
    const narration = simulateAgentNarration("unknown_node_xyz");
    expect(narration).toContain("unknown_node_xyz");
  });
});
