import type { GraphCandidate } from "../data/sampleData";

export const requiredProtectedNodes = [
  "validate_sources",
  "data_analyst",
  "ml_executor",
  "recommendation_engine",
  "explainability",
  "reviewer",
  "publish_recommendation",
];

export type GraphValidation = {
  valid: boolean;
  errors: string[];
};

export function parseGraphCandidate(source: string): GraphCandidate | null {
  try {
    return JSON.parse(source) as GraphCandidate;
  } catch {
    return null;
  }
}

export function validateGraphCandidate(source: string): GraphValidation {
  const parsed = parseGraphCandidate(source);
  if (parsed === null) {
    return {
      valid: false,
      errors: ["Candidate graph JSON is invalid."],
    };
  }

  const nodeIds = new Set(parsed.nodes.map((node) => node.id));
  const errors: string[] = [];

  requiredProtectedNodes.forEach((nodeId) => {
    if (!nodeIds.has(nodeId)) {
      errors.push(`Protected path is missing required node "${nodeId}".`);
    }
  });

  const publishIndex = parsed.nodes.findIndex((node) => node.id === "publish_recommendation");
  const reviewerIndex = parsed.nodes.findIndex((node) => node.id === "reviewer");
  if (publishIndex !== -1 && reviewerIndex !== -1 && publishIndex < reviewerIndex) {
    errors.push('Recommendation release node "publish_recommendation" appears before "reviewer".');
  }

  const hasSuccessPath = parsed.edges.some(
    (edge) => edge.from === "reviewer" && edge.to === "publish_recommendation",
  );
  if (!hasSuccessPath) {
    errors.push('Success path does not reach "publish_recommendation" through "reviewer".');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
