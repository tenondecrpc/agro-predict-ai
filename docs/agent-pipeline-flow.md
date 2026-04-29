# AgroPredict AI - Agent Pipeline Flow

## Overview

AgroPredict AI is a multi-agent predictive intelligence system for agriculture and logistics. It uses **LangGraph** to orchestrate **5 specialized agents** that work in a chain to transform raw data into actionable, explained recommendations.

All agent communication flows exclusively through the LangGraph `StateGraph` - there are no direct inter-agent API calls. Each agent has a single responsibility, explicit input/output contracts, and deterministic fallback behavior when upstream agents fail.

---

## The 5 Agents

### 1. Data Analyst (Aline)

**Role:** Data ingestion, validation, and feature extraction.

**Responsibilities:**
- Receives raw data from external sources (agricultural sensors, logistics data, weather feeds, market data)
- Executes the **quality gate**: verifies data is valid, complete, and fresh
- If data fails validation, the pipeline halts - no prediction is emitted without valid data
- Processes validated data and extracts features for the ML model
- Handles graceful degradation when external APIs fail (routes to backup providers or historical baselines)

**Phases:** `intake`, `quality-gate`, `analysis`

---

### 2. ML Executor (Mila)

**Role:** Machine learning model execution.

**Responsibilities:**
- Receives validated, processed data from the Data Analyst
- Executes the appropriate scikit-learn model (crop yield prediction, logistics route optimization, etc.)
- Generates numerical predictions with confidence intervals
- Model artifacts are versioned with metadata (training date, dataset hash, accuracy metrics)
- Supports shadow-mode validation before active runtime

**Phases:** `model-run`

---

### 3. Recommendation Engine (Nico)

**Role:** Translates numerical predictions into actionable recommendations.

**Responsibilities:**
- Takes model outputs (e.g., "expected yield: 85%") and converts them to concrete actions (e.g., "increase irrigation in zone B by 15%")
- Applies business rules and tenant-specific context
- Ensures recommendations are grounded in verifiable data with complete provenance chains
- No recommendation is emitted without an attached data provenance chain

**Phases:** `recommendation`

---

### 4. Explainability (Sofia)

**Role:** Generates explanation artifacts for every recommendation.

**Responsibilities:**
- Produces explainability artifacts: which features drove the decision, confidence level, data provenance chain
- This is **non-negotiable**: no recommendation is released without an attached explanation
- Supports post-hoc analysis of any recommendation
- Exposes feature importance and data freshness metadata

**Phases:** `explainability`

---

### 5. Reviewer (Ravi)

**Role:** Final gatekeeper before recommendation release.

**Responsibilities:**
- Verifies the entire chain is correct: valid data -> model executed -> recommendation generated -> explanation attached
- If anything fails in the chain, rejects and routes to escalation
- Human approval is **break-glass only** for exception paths (security review, model accuracy regression, data contradictions, budget exhaustion, policy violations)
- The normal success path does NOT require manual approval

**Phases:** `quality-gate` (initial data review), `review` (final review), `release` (publication)

---

## Pipeline Phases

| Phase | Active Agents | What Happens |
|-------|--------------|--------------|
| **intake** | Data Analyst | Raw data arrives from external sources |
| **quality-gate** | Data Analyst + Reviewer | Data is validated; pipeline halts if validation fails |
| **analysis** | Data Analyst | Data is processed and features are extracted |
| **model-run** | Data Analyst + ML Executor | ML model is executed against prepared data |
| **recommendation** | ML Executor + Recommendation Engine | Actionable recommendations are generated |
| **explainability** | Recommendation Engine + Explainability | Explanation artifacts are produced |
| **review** | Explainability + Reviewer | Final review of the entire chain |
| **release** | Data Analyst + Reviewer | Recommendation is published to the tenant-scoped prediction surface |
| **complete** | All 5 agents | Pipeline finished; all agents gather |

---

## Core Invariants

### Non-Negotiable Rules

1. **All predictions MUST be grounded in verifiable data sources** with complete provenance chains
2. **No prediction before data quality gates pass** and readiness is confirmed
3. **Every agent emits structured logs, metrics, and traces**; predictions include explanation artifacts
4. **Test-first development** is mandatory for all agents, models, and integrations
5. **System operates under partial failure** with graceful degradation; cached-model fallback with staleness warnings on data pipeline interruption
6. **Agent communication ONLY through LangGraph state** - no direct inter-agent API calls
7. **No model may emit recommendations** without passing data quality gates and accuracy validation
8. **Any path to production recommendations** must traverse model execution, explainability verification, and review approval
9. **Human approval is break-glass only** - the normal success path cannot require manual approval

### Failure Handling

- When an agent fails, downstream agents receive explicit failure signals and degrade gracefully rather than crash
- Data pipeline interruptions trigger cached-model fallback with staleness warnings
- External API failures (weather services, satellite imagery, market data) route to backup providers or historical baselines
- Air-gapped deployments function without external connectivity using local model caches and stored datasets
- Every failure terminal path maps to an explicit escalation reason and a registered escalation sink

---

## Deployment Profiles

Both **connected** and **air-gapped** deployment profiles are first-class supported:

- **Connected:** Full external API access for real-time data ingestion
- **Air-gapped:** Functions without external connectivity using local model caches and stored datasets

Multi-tenancy means teams, business units, and projects inside one customer-owned deployment. There is no vendor-operated SaaS control plane and no cross-customer data plane.

---

## Visual Representation

The agent pipeline is visualized as a **lunar space station office** where each agent has a desk, monitor, and personal workspace. During pipeline execution:

- Active agents move from their desks to interact with their pipeline partner
- Speech bubbles show what each agent is currently doing
- A document icon appears when an agent is carrying data to the next stage
- A green pulse indicator shows which agents are currently active
- The phase card in the top-right shows the current pipeline stage
- A scrolling ticker at the bottom displays real-time pipeline status

When the pipeline completes, all 5 agents gather together in the center of the office.
