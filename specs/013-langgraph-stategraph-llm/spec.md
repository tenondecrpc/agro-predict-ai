# Feature Specification: LangGraph StateGraph with Real LLM Integration

**Feature Branch**: `013-langgraph-stategraph-llm`
**Created**: 2026-04-28
**Status**: Draft
**Input**: Refactor PredictionGraph from imperative Python into a real LangGraph StateGraph, and wire a real LLM provider (OpenCode Go, model minimax-m2.7) into the recommendation_engine and reviewer agents.

## Context

`PredictionGraph` in `backend/src/backend/predictions/graph.py` currently runs the five-agent pipeline as a plain Python method chain. This bypasses LangGraph's native checkpointing, resumability, tracing, and typed state transitions. The `recommendation_engine` and `reviewer` agents produce outputs from deterministic rules rather than LLM reasoning. This spec covers:

1. Replacing the imperative pipeline with a proper `StateGraph(PredictionState)`.
2. Adding a secure LLM adapter that calls the OpenCode Go API using credentials read exclusively from environment variables or Vault - never hardcoded.
3. Wiring `recommendation_engine` and `reviewer` to use real LLM inference for natural-language recommendation generation and output validation.

## Secure LLM Credential Scheme

LLM provider credentials MUST follow the same secrets-management contract as all other credentials in the system (spec `010-security-secrets`):

- **Environment variables (local dev)**: `LLM_API_KEY`, `LLM_API_URL`, `LLM_MODEL_ID` read from a `.env` file that is listed in `.gitignore` and NEVER committed to the repository.
- **Kubernetes (staging/production)**: credentials provisioned via `ExternalSecret` backed by Vault or the configured secret store, injected as env vars into the backend pod at runtime. The `externalsecret.yaml` Helm template already supports this pattern.
- **Air-gapped deployments**: `LLM_API_URL` can point to an internally hosted model endpoint (e.g., Ollama or a self-hosted inference server). The adapter must accept any OpenAI-compatible base URL, not assume a specific host.
- **Validation at startup**: the application MUST refuse to start if `LLM_API_KEY` or `LLM_MODEL_ID` is missing and `LLM_ENABLED=true`. If `LLM_ENABLED=false` (default for air-gapped or CI), agents fall back to deterministic rule-based outputs and emit a `llm_disabled` degradation flag.
- **No key in code, configs, specs, or logs**: the actual key value MUST NOT appear in source code, config files, spec documents, log output, or error messages. Log entries MUST redact the key (e.g., `LLM_API_KEY=sk-***`).

Default values for the OpenCode Go provider (dev convenience, not secrets):

```
LLM_API_URL=https://opencode.ai/zen/go/v1
LLM_MODEL_ID=minimax-m2.7
```

`LLM_API_KEY` has no safe default and MUST always be injected from the environment or Vault.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real LangGraph StateGraph executes the prediction pipeline (Priority: P1)

An operator deploys the backend. When a prediction request arrives, it is processed by a compiled LangGraph `StateGraph` with five nodes (`data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, `reviewer`). Each node receives typed `PredictionState` and returns an updated state. LangGraph checkpoints state after each node using `langgraph-checkpoint-postgres`. If the process is interrupted mid-pipeline, the job can be resumed from the last checkpoint.

**Why this priority**: The constitution mandates LangGraph StateGraph orchestration. Correct checkpointing and typed state transitions are the foundation for all agent work, including the LLM integration.

**Independent Test**: Submit a prediction request and verify the response includes a `checkpoint_id` traceable in the `langgraph_checkpoints` table. Kill the worker mid-graph and confirm the job resumes from the correct node on restart.

**Acceptance Scenarios**:

1. **Given** a valid prediction request, **When** the graph executes, **Then** each node transition is recorded as a LangGraph checkpoint in PostgreSQL and the final state is complete.
2. **Given** the worker is terminated after `ml_executor` completes, **When** the worker restarts and resumes the job, **Then** the graph continues from `recommendation_engine` without re-running earlier nodes.
3. **Given** a node raises an unrecoverable exception, **When** the graph reaches the error boundary, **Then** the state transitions to an `escalated` terminal and the checkpoint captures the failure reason.

---

### User Story 2 - recommendation_engine generates recommendations via LLM (Priority: P2)

The `recommendation_engine` agent sends a structured prompt to the OpenCode Go LLM API containing the crop type, region, ML model output, confidence interval, and feature importance. The LLM returns a natural-language recommendation. The agent validates the response format, extracts structured fields (`recommendation`, `priority`, `actions`), and passes them through `PredictionState` to the next node.

**Why this priority**: LLM-generated recommendations replace the current hardcoded string templates and deliver agronomically meaningful, context-aware advice.

**Independent Test**: Run `recommendation_engine` in isolation with a mocked LangGraph state containing known ML output. Verify the returned state contains a non-empty `recommendation` string, a valid `priority` value, and at least one `action`.

**Acceptance Scenarios**:

1. **Given** LLM credentials are configured and the API is reachable, **When** `recommendation_engine` executes, **Then** it returns a structured recommendation grounded in the ML output passed through state.
2. **Given** the LLM API returns a malformed response, **When** `recommendation_engine` processes it, **Then** the agent falls back to the deterministic template and sets `degradation_flags: ["llm_recommendation_fallback"]`.
3. **Given** `LLM_ENABLED=false`, **When** `recommendation_engine` executes, **Then** it uses the deterministic rule-based output and sets `degradation_flags: ["llm_disabled"]` without attempting any API call.
4. **Given** the LLM API call exceeds the configured timeout, **When** the circuit breaker opens, **Then** subsequent calls fail fast and the fallback activates until the circuit resets.

---

### User Story 3 - reviewer validates prediction output via LLM (Priority: P3)

The `reviewer` agent sends the complete prediction output (recommendation, confidence, provenance chain) to the LLM API with a validation prompt. The LLM checks for internal consistency, policy compliance, and agronomic plausibility. If the LLM flags an issue, the reviewer escalates with the reason. If the LLM approves, the prediction is released.

**Why this priority**: LLM-based review replaces the current pass-through reviewer and adds a genuine quality gate before recommendations reach operators.

**Independent Test**: Run `reviewer` with a state containing a deliberate policy violation (e.g., recommendation to over-irrigate despite drought alert). Verify the agent escalates with a LLM-provided reason rather than releasing the prediction.

**Acceptance Scenarios**:

1. **Given** a valid prediction state, **When** `reviewer` runs the LLM validation, **Then** it releases the prediction if the LLM returns an approval signal.
2. **Given** a prediction with an internally inconsistent recommendation, **When** `reviewer` runs, **Then** it escalates the prediction with the LLM-identified reason and sets `escalation_reason`.
3. **Given** the LLM is unavailable and `LLM_ENABLED=false`, **When** `reviewer` executes, **Then** it falls back to rule-based validation and sets `degradation_flags: ["llm_review_fallback"]`.

---

### User Story 4 - LLM credentials managed securely with no key exposure (Priority: P1)

Developers clone the repository, create a local `.env` file with their `LLM_API_KEY`, and run `docker-compose up`. The backend reads credentials from the environment. No key ever appears in source code, logs, or error output. In Kubernetes, an `ExternalSecret` injects the key from Vault.

**Why this priority**: Key exposure in a repository or log stream is a critical security incident. This is a Tier 1 non-negotiable per spec `010-security-secrets`.

**Independent Test**: Run `git grep -r "LLM_API_KEY" -- "*.py" "*.ts" "*.yaml" "*.json"` on the repository and confirm no actual key values appear. Start the backend with `LLM_API_KEY` unset and `LLM_ENABLED=true`; confirm startup fails with a clear error that does not include the key value.

**Acceptance Scenarios**:

1. **Given** `.env` is in `.gitignore`, **When** a developer commits all tracked files, **Then** `LLM_API_KEY` does not appear in the commit.
2. **Given** an LLM API error occurs, **When** the error is logged, **Then** the log entry shows `LLM_API_KEY=sk-***` (redacted), not the actual key.
3. **Given** the Kubernetes `ExternalSecret` is configured, **When** the backend pod starts, **Then** it reads `LLM_API_KEY` from the injected environment variable with no Vault token or raw key in the pod spec.

---

### Edge Cases

- What happens when the LLM returns a recommendation that contradicts the data provenance chain?
- How does the system behave when LangGraph checkpointing fails (PostgreSQL unreachable mid-graph)?
- What happens when the LLM response exceeds the maximum token budget?
- How does the StateGraph handle a node that returns a partial state update (missing required fields)?
- What happens in air-gapped mode when `LLM_API_URL` points to an unreachable internal host?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `PredictionGraph` MUST be implemented as a LangGraph `StateGraph(PredictionState)` with five named nodes: `data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, `reviewer`.
- **FR-002**: State MUST be a typed `TypedDict` (`PredictionState`) with all fields explicitly declared and versioned.
- **FR-003**: The compiled graph MUST use `langgraph-checkpoint-postgres` as the checkpointer, writing checkpoints to the `langgraph_checkpoints` table.
- **FR-004**: Agent communication MUST occur only through `PredictionState` - no direct function calls between agent modules.
- **FR-005**: `recommendation_engine` MUST call the LLM API when `LLM_ENABLED=true`, passing crop, region, ML output, confidence, and feature importance as structured context.
- **FR-006**: `reviewer` MUST call the LLM API when `LLM_ENABLED=true`, passing the full prediction output for consistency and policy validation.
- **FR-007**: Both agents MUST fall back to deterministic rule-based logic when `LLM_ENABLED=false` or when the LLM call fails, and MUST set the appropriate `degradation_flags`.
- **FR-008**: The LLM adapter MUST read credentials exclusively from `LLM_API_KEY`, `LLM_API_URL`, and `LLM_MODEL_ID` environment variables.
- **FR-009**: The LLM adapter MUST redact the key value in all log output.
- **FR-010**: The application MUST refuse to start if `LLM_ENABLED=true` and `LLM_API_KEY` is not set.
- **FR-011**: The LLM adapter MUST implement a circuit breaker: open after 3 consecutive failures, reset after 60 seconds.
- **FR-012**: LLM calls MUST have a configurable timeout (default: 30 seconds, env var `LLM_TIMEOUT_SECONDS`).
- **FR-013**: The graph MUST support resumability: given a `thread_id`, it MUST resume from the last checkpoint instead of re-running from the start.
- **FR-014**: `.env` MUST be listed in `.gitignore`. A `.env.example` file with placeholder values (no real keys) MUST be provided.

### Key Entities

- **PredictionState**: TypedDict representing full pipeline state. Fields: `tenant_id`, `team_id`, `input_data`, `validated_data`, `quality_flags`, `model_output`, `confidence_interval`, `feature_importance`, `recommendation`, `priority`, `actions`, `explanation_artifact`, `review_result`, `escalation_reason`, `degradation_flags`, `data_provenance`, `thread_id`, `checkpoint_id`.
- **LLMAdapter**: Interface for LLM provider calls. Implementations: `OpenAICompatibleAdapter` (OpenCode Go), `DisabledAdapter` (LLM_ENABLED=false fallback).
- **LLMConfig**: Pydantic settings model reading `LLM_API_KEY`, `LLM_API_URL`, `LLM_MODEL_ID`, `LLM_ENABLED`, `LLM_TIMEOUT_SECONDS` from environment.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of prediction executions create LangGraph checkpoints in PostgreSQL (zero executions that bypass the StateGraph).
- **SC-002**: The graph successfully resumes from checkpoint in 100% of simulated mid-graph interruption tests.
- **SC-003**: `git grep` on the repository finds zero occurrences of the actual `LLM_API_KEY` value in any tracked file.
- **SC-004**: LLM fallback activates within 5 seconds when the LLM API is unreachable.
- **SC-005**: P95 end-to-end latency for LLM-augmented predictions is under 45 seconds (includes LLM call budget of 15 seconds per agent).
- **SC-006**: Zero startup failures in CI where `LLM_ENABLED=false` (all tests pass without a real LLM key).
