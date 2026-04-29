export type OperatorRole = "viewer" | "operator" | "admin" | "super-admin";
export type RunStatus = "planning" | "active" | "paused" | "review" | "dlq" | "completed";
export type RuntimeAgentRole =
  | "data_analyst"
  | "ml_executor"
  | "recommendation_engine"
  | "explainability"
  | "reviewer";

export type RunCard = {
  id: string;
  predictionId: string;
  lane: string;
  agent: RuntimeAgentRole;
  status: RunStatus;
  retryCount: number;
  costUsd: number;
};

export type GraphCandidate = {
  profileId: string;
  nodes: Array<{
    id: string;
    label: string;
    protected: boolean;
    emitsRecommendation?: boolean;
  }>;
  edges: Array<{ from: string; to: string; transition: string }>;
};

export type AgentCard = {
  role: string;
  model: string;
  tools: string[];
  retryBudget: string;
  testPrompt: string;
};

export type PersistenceAdapterStatus = {
  name: string;
  configured: boolean;
  healthy: boolean;
};

export type PersistenceStatusCard = {
  migrationVersion: string;
  appliedVersion: string;
  activeSnapshotId: string;
  adapters: PersistenceAdapterStatus[];
};

export type ApiDeprecationTimeline = {
  deprecationId: string;
  route: string;
  method: string;
  version: string;
  deprecatedAt: string;
  sunsetAt: string;
  rationale: string;
  replacementRoute: string;
};

export type DeploymentProfileCard = {
  profile: "connected" | "air_gapped";
  provider: string;
  telemetry: string;
  statusSync: string;
  runbook: string;
};

export const roles: OperatorRole[] = ["viewer", "operator", "admin", "super-admin"];

export const deploymentProfile: DeploymentProfileCard = {
  profile: "air_gapped",
  provider: "OpenCode Go",
  telemetry: "External telemetry disabled",
  statusSync: "Internal status only",
  runbook: "docs/runbooks/air-gapped-deployment.md",
};

export const initialRuns: RunCard[] = [
  {
    id: "run-101",
    predictionId: "CROP-101",
    lane: "Tenant Alpha - soybean yield",
    agent: "data_analyst",
    status: "planning",
    retryCount: 0,
    costUsd: 1.2,
  },
  {
    id: "run-102",
    predictionId: "LOG-204",
    lane: "Tenant Alpha - cold-chain routing",
    agent: "ml_executor",
    status: "active",
    retryCount: 1,
    costUsd: 4.8,
  },
  {
    id: "run-103",
    predictionId: "IRR-318",
    lane: "Tenant Beta - irrigation risk",
    agent: "reviewer",
    status: "paused",
    retryCount: 0,
    costUsd: 2.6,
  },
  {
    id: "run-104",
    predictionId: "MKT-442",
    lane: "Tenant Alpha - market demand",
    agent: "explainability",
    status: "dlq",
    retryCount: 2,
    costUsd: 3.4,
  },
];

export const activeGraphCandidate: GraphCandidate = {
  profileId: "prediction_pipeline_v1",
  nodes: [
    { id: "ingest_event", label: "Ingest Event", protected: true },
    { id: "validate_sources", label: "Data Quality Gate", protected: true },
    { id: "data_analyst", label: "Data Analyst", protected: true },
    { id: "ml_executor", label: "ML Executor", protected: true },
    { id: "recommendation_engine", label: "Recommendation Engine", protected: true },
    { id: "explainability", label: "Explainability", protected: true },
    { id: "reviewer", label: "Reviewer", protected: true },
    { id: "publish_recommendation", label: "Publish Recommendation", protected: true, emitsRecommendation: true },
  ],
  edges: [
    { from: "START", to: "ingest_event", transition: "success" },
    { from: "ingest_event", to: "validate_sources", transition: "success" },
    { from: "validate_sources", to: "data_analyst", transition: "success" },
    { from: "data_analyst", to: "ml_executor", transition: "success" },
    { from: "ml_executor", to: "recommendation_engine", transition: "success" },
    { from: "recommendation_engine", to: "explainability", transition: "success" },
    { from: "explainability", to: "reviewer", transition: "success" },
    { from: "reviewer", to: "publish_recommendation", transition: "success" },
  ],
};

export const invalidGraphCandidate: GraphCandidate = {
  ...activeGraphCandidate,
  nodes: activeGraphCandidate.nodes.filter(
    (node) => node.id !== "reviewer" && node.id !== "explainability",
  ),
  edges: activeGraphCandidate.edges.filter(
    (edge) =>
      !["reviewer", "explainability"].includes(edge.from) &&
      !["reviewer", "explainability"].includes(edge.to),
  ),
};

export const agentCards: AgentCard[] = [
  {
    role: "data_analyst",
    model: "rules + statistical profiling",
    tools: ["apex_read", "quality_checks", "provenance_read"],
    retryBudget: "data validation: 2",
    testPrompt: "Summarize data freshness, missing fields, and provenance gaps.",
  },
  {
    role: "ml_executor",
    model: "scikit-learn adapter",
    tools: ["model_registry", "feature_store", "accuracy_registry"],
    retryBudget: "model execution: 2",
    testPrompt: "Run the selected model and report confidence intervals.",
  },
  {
    role: "reviewer",
    model: "policy evaluator",
    tools: ["explanation_read", "policy_check", "escalation_sink"],
    retryBudget: "review: 1",
    testPrompt: "Verify data quality, explainability, and release policy before approval.",
  },
];

export const spriteManifest = [
  {
    spriteId: "agent-data-analyst",
    sourceKind: "bundled",
    runtimeRole: "data_analyst",
    runtimeState: "planning",
    path: "/assets/sprites/agent_a.png",
  },
  {
    spriteId: "agent-reviewer",
    sourceKind: "bundled",
    runtimeRole: "reviewer",
    runtimeState: "review",
    path: "/assets/sprites/agent_b.png",
  },
  {
    spriteId: "agent-ml-executor",
    sourceKind: "bundled",
    runtimeRole: "ml_executor",
    runtimeState: "active",
    path: "/assets/sprites/agent_c.png",
  },
  {
    spriteId: "agent-recommendation-engine",
    sourceKind: "bundled",
    runtimeRole: "recommendation_engine",
    runtimeState: "active",
    path: "/assets/sprites/agent_d.png",
  },
  {
    spriteId: "agent-explainability",
    sourceKind: "bundled",
    runtimeRole: "explainability",
    runtimeState: "active",
    path: "/assets/sprites/agent_s.png",
  },
];

export const persistenceStatus: PersistenceStatusCard = {
  migrationVersion: "20260418_0006",
  appliedVersion: "20260418_0006",
  activeSnapshotId: "snapshot-prod-0042",
  adapters: [
    { name: "database", configured: true, healthy: true },
    { name: "redis", configured: true, healthy: true },
    { name: "encryption", configured: true, healthy: true },
  ],
};

export const apiDeprecations: ApiDeprecationTimeline[] = [
  {
    deprecationId: "runtime-simulate-v1",
    route: "/api/v1/runtime/simulate",
    method: "POST",
    version: "v1",
    deprecatedAt: "2026-04-26",
    sunsetAt: "2027-04-26",
    rationale: "v2 will separate prediction simulation from execution controls.",
    replacementRoute: "/api/v2/runtime/simulations",
  },
];
