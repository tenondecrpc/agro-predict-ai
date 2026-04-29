import type { GraphCandidate } from "../data/sampleData";
import { validateGraphCandidate } from "./graphValidation";

export type SimulationAgentRole =
  | "data_analyst"
  | "ml_executor"
  | "recommendation_engine"
  | "explainability"
  | "reviewer";

export type SimulationAgentVisual = {
  role: SimulationAgentRole;
  title: string;
  spritePath: string;
  facing: "front" | "back" | "left" | "right";
};

export type SimulationOfficePhase =
  | "intake"
  | "quality-gate"
  | "analysis"
  | "model-run"
  | "recommendation"
  | "explainability"
  | "review"
  | "release"
  | "complete";

export type SimulationOfficeState = {
  phase: SimulationOfficePhase;
  label: string;
  interaction: string;
  activeAgents: SimulationAgentRole[];
  carrier?: SimulationAgentRole;
  speech: Partial<Record<SimulationAgentRole, string>>;
};

export type SimulationStep = {
  index: number;
  nodeId: string;
  label: string;
  isProtected: boolean;
  emitsRecommendation: boolean;
  transitionReason: string;
  narration: string;
  visualAgent: SimulationAgentVisual;
  office: SimulationOfficeState;
};

export type SimulationPlan = {
  steps: SimulationStep[];
  protectedInvariantErrors: string[];
};

const narrationByNodeId: Record<string, string> = {
  ingest_event:
    "Receiving a validated ingestion event for a crop, logistics, or market prediction request.",
  validate_sources:
    "Checking data freshness, source readiness, tenant scope, and provenance before prediction can begin.",
  data_analyst:
    "Profiling sensor, weather, Oracle APEX, and logistics inputs so downstream models receive trusted features.",
  ml_executor:
    "Running the selected model adapter and attaching confidence intervals plus model metadata.",
  recommendation_engine:
    "Converting model output into an actionable agriculture or logistics recommendation.",
  explainability:
    "Building the explanation artifact with feature importance, freshness, and provenance evidence.",
  reviewer:
    "Verifying data quality, model execution, explainability, and release policy before approval.",
  publish_recommendation:
    "Publishing the approved recommendation to the tenant-scoped prediction surface.",
};

const visualAgentByRole: Record<SimulationAgentRole, Omit<SimulationAgentVisual, "role">> = {
  data_analyst: {
    title: "Data Analyst",
    spritePath: "/assets/sprites/agent_a.png",
    facing: "back",
  },
  ml_executor: {
    title: "ML Executor",
    spritePath: "/assets/sprites/agent_c.png",
    facing: "back",
  },
  recommendation_engine: {
    title: "Recommendation Engine",
    spritePath: "/assets/sprites/agent_d.png",
    facing: "right",
  },
  explainability: {
    title: "Explainability",
    spritePath: "/assets/sprites/agent_s.png",
    facing: "front",
  },
  reviewer: {
    title: "Reviewer",
    spritePath: "/assets/sprites/agent_b.png",
    facing: "left",
  },
};

const nodeAgentRole: Record<string, SimulationAgentRole> = {
  ingest_event: "data_analyst",
  validate_sources: "data_analyst",
  data_analyst: "data_analyst",
  ml_executor: "ml_executor",
  recommendation_engine: "recommendation_engine",
  explainability: "explainability",
  reviewer: "reviewer",
  publish_recommendation: "reviewer",
};

const officeByNodeId: Record<string, SimulationOfficeState> = {
  ingest_event: {
    phase: "intake",
    label: "Prediction intake",
    interaction: "Data Analyst receives the tenant-scoped ingestion event and opens the operations board.",
    activeAgents: ["data_analyst"],
    speech: {
      data_analyst: "New prediction event received.",
      reviewer: "Standing by for approval.",
    },
  },
  validate_sources: {
    phase: "quality-gate",
    label: "Data quality gate",
    interaction: "Data Analyst checks freshness, tenant isolation, and provenance before the model lane opens.",
    activeAgents: ["data_analyst"],
    carrier: "data_analyst",
    speech: {
      data_analyst: "Validating source readiness.",
    },
  },
  data_analyst: {
    phase: "analysis",
    label: "Feature analysis",
    interaction: "Data Analyst profiles agronomic and logistics inputs while Reviewer watches policy state.",
    activeAgents: ["data_analyst", "reviewer"],
    carrier: "data_analyst",
    speech: {
      data_analyst: "Features and anomalies are ready.",
      reviewer: "Checking data evidence.",
    },
  },
  ml_executor: {
    phase: "model-run",
    label: "Model execution",
    interaction: "ML Executor runs the registered model and records confidence, version, and dataset hash.",
    activeAgents: ["ml_executor"],
    carrier: "ml_executor",
    speech: {
      ml_executor: "Model adapter is running.",
    },
  },
  recommendation_engine: {
    phase: "recommendation",
    label: "Recommendation draft",
    interaction: "Recommendation Engine turns model output into operational guidance for the tenant.",
    activeAgents: ["ml_executor", "recommendation_engine"],
    carrier: "recommendation_engine",
    speech: {
      ml_executor: "Confidence interval attached.",
      recommendation_engine: "Drafting field guidance.",
    },
  },
  explainability: {
    phase: "explainability",
    label: "Explanation artifact",
    interaction: "Explainability assembles feature importance, data freshness, and provenance evidence.",
    activeAgents: ["recommendation_engine", "explainability"],
    carrier: "explainability",
    speech: {
      recommendation_engine: "Recommendation is ready.",
      explainability: "Evidence package attached.",
    },
  },
  reviewer: {
    phase: "review",
    label: "Release review",
    interaction: "Reviewer checks the complete evidence chain before any recommendation reaches production.",
    activeAgents: ["explainability", "reviewer"],
    carrier: "explainability",
    speech: {
      explainability: "Provenance is complete.",
      reviewer: "Approving policy gates.",
    },
  },
  publish_recommendation: {
    phase: "release",
    label: "Recommendation release",
    interaction: "Reviewer releases the approved recommendation to the tenant-scoped prediction surface.",
    activeAgents: ["data_analyst", "reviewer"],
    carrier: "reviewer",
    speech: {
      data_analyst: "Audit trail retained.",
      reviewer: "Recommendation approved.",
    },
  },
};

export function simulateAgentNarration(nodeId: string): string {
  return narrationByNodeId[nodeId] ?? `Executing node: ${nodeId}.`;
}

export function getSimulationAgentVisual(nodeId: string): SimulationAgentVisual {
  const role = nodeAgentRole[nodeId] ?? "data_analyst";
  return { role, ...visualAgentByRole[role] };
}

export function getSimulationOfficeState(
  nodeId: string,
  narration: string = simulateAgentNarration(nodeId),
): SimulationOfficeState {
  const configured = officeByNodeId[nodeId];
  if (!configured) {
    return {
      phase: "intake",
      label: "Custom graph step",
      interaction: `Executing custom node ${nodeId}.`,
      activeAgents: ["data_analyst"],
      speech: { data_analyst: narration },
    };
  }

  const primaryRole = nodeAgentRole[nodeId] ?? "data_analyst";
  return {
    ...configured,
    speech: {
      ...configured.speech,
      [primaryRole]: narration,
    },
  };
}

export function buildSimulationPlan(candidate: GraphCandidate): SimulationPlan {
  const validation = validateGraphCandidate(JSON.stringify(candidate));
  if (!validation.valid) {
    return { steps: [], protectedInvariantErrors: validation.errors };
  }

  const successEdges = new Map<string, string>();
  for (const edge of candidate.edges) {
    if (edge.transition === "success") {
      successEdges.set(edge.from, edge.to);
    }
  }

  const nodeMap = new Map(candidate.nodes.map((n) => [n.id, n]));
  const steps: SimulationStep[] = [];
  let current = successEdges.get("START");

  while (current !== undefined && nodeMap.has(current)) {
    const node = nodeMap.get(current)!;
    const narration = simulateAgentNarration(node.id);
    steps.push({
      index: steps.length,
      nodeId: node.id,
      label: node.label,
      isProtected: node.protected,
      emitsRecommendation: node.emitsRecommendation ?? false,
      transitionReason: "success",
      narration,
      visualAgent: getSimulationAgentVisual(node.id),
      office: getSimulationOfficeState(node.id, narration),
    });
    current = successEdges.get(current);
  }

  const nodeOrder = steps.map((s) => s.nodeId);
  const protectedInvariantErrors: string[] = [];

  const dataAnalystIdx = nodeOrder.indexOf("data_analyst");
  const qualityGateIdx = nodeOrder.indexOf("validate_sources");
  if (dataAnalystIdx !== -1 && qualityGateIdx !== -1 && dataAnalystIdx < qualityGateIdx) {
    protectedInvariantErrors.push(
      'Traversal order violation: "data_analyst" appears before "validate_sources".',
    );
  }

  const publishIdx = nodeOrder.indexOf("publish_recommendation");
  if (publishIdx !== -1) {
    for (const required of ["ml_executor", "recommendation_engine", "explainability", "reviewer"]) {
      const reqIdx = nodeOrder.indexOf(required);
      if (reqIdx === -1 || reqIdx > publishIdx) {
        protectedInvariantErrors.push(
          `Traversal order violation: "publish_recommendation" reached without traversing "${required}".`,
        );
      }
    }
  }

  if (protectedInvariantErrors.length > 0) {
    return { steps: [], protectedInvariantErrors };
  }

  return { steps, protectedInvariantErrors: [] };
}
