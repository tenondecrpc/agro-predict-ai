# Feature Specification: Deployment Profiles

**Feature Branch**: `009-deployment-profiles`  
**Created**: 2026-04-28  
**Status**: Implemented  
**Input**: Helm charts for connected and air-gapped Kubernetes deployment with HPA, health probes, and resource quotas

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy to connected Kubernetes cluster (Priority: P1)

An operator deploys AgroPredict AI to a connected Kubernetes cluster using Helm. The deployment includes backend (FastAPI + ARQ workers), frontend (React), PostgreSQL, Redis, and all supporting infrastructure. The deployment uses Helm values for environment-specific configuration.

**Why this priority**: Connected deployment is the primary deployment profile. Without it, the system cannot be deployed to production.

**Independent Test**: Can be fully tested by deploying to a local Minikube cluster and verifying all components start, health checks pass, and the prediction pipeline executes.

**Acceptance Scenarios**:

1. **Given** a connected Kubernetes cluster, **When** the Helm chart is deployed, **Then** all components (backend, frontend, PostgreSQL, Redis) start and pass health checks.
2. **Given** the deployment is complete, **When** a prediction request is submitted, **Then** the full pipeline executes and returns a result.
3. **Given** the deployment uses environment-specific values, **When** the deployment is inspected, **Then** all configuration values match the values file.

---

### User Story 2 - Deploy to air-gapped Kubernetes cluster (Priority: P2)

An operator deploys AgroPredict AI to an air-gapped Kubernetes cluster with no external connectivity. All container images, dependencies, and model artifacts are pre-loaded. External services (LLM providers, weather APIs, satellite imagery) are disabled or replaced with local alternatives.

**Why this priority**: Air-gapped deployment is a first-class supported profile. Many agricultural organizations operate in environments with no external connectivity.

**Independent Test**: Can be fully tested by deploying to an air-gapped Minikube cluster (simulated by blocking external network access) and verifying the system operates with local data and cached models.

**Acceptance Scenarios**:

1. **Given** an air-gapped Kubernetes cluster, **When** the air-gapped Helm chart is deployed, **Then** all components start without requiring external network access.
2. **Given** the air-gapped deployment is running, **When** a prediction request is submitted, **Then** the system uses local data sources and cached models.
3. **Given** the air-gapped deployment is running, **When** external service calls are attempted, **Then** the system gracefully degrades and uses fallback behavior.

---

### User Story 3 - Horizontal scaling with HPA (Priority: ARQ workers)

The system scales horizontally using Kubernetes Horizontal Pod Autoscaler (HPA) based on ARQ queue depth and CPU utilization. As prediction demand increases, additional worker pods are automatically provisioned.

**Why this priority**: Horizontal scaling ensures the system can handle variable prediction loads without manual intervention.

**Independent Test**: Can be tested by submitting a burst of prediction requests and verifying HPA provisions additional worker pods.

**Acceptance Scenarios**:

1. **Given** the ARQ queue depth exceeds the HPA threshold, **When** the autoscaler evaluates, **Then** additional worker pods are provisioned.
2. **Given** the ARQ queue depth drops below the scale-down threshold, **When** the autoscaler evaluates, **Then** excess worker pods are terminated.
3. **Given** HPA is scaling, **When** predictions are processed, **Then** no predictions are lost or duplicated during scaling events.

---

### Edge Cases

- What happens when a Helm upgrade fails mid-deployment?
- How does the system handle a node failure in the Kubernetes cluster?
- What happens when resource quotas prevent HPA from scaling?
- How does the air-gapped profile handle model updates (no external connectivity)?
- What happens when the PostgreSQL or Redis pods are evicted due to resource pressure?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide Helm charts for connected Kubernetes deployment.
- **FR-002**: System MUST provide Helm charts for air-gapped Kubernetes deployment.
- **FR-003**: System MUST support Horizontal Pod Autoscaler (HPA) for backend workers based on queue depth and CPU.
- **FR-004**: System MUST include liveness and readiness health probes for all pods.
- **FR-005**: System MUST enforce resource quotas (CPU, memory) for all pods.
- **FR-006**: System MUST support environment-specific configuration via Helm values files.
- **FR-007**: System MUST disable external service calls in air-gapped profile (LLM providers, weather APIs, satellite imagery).
- **FR-008**: System MUST use local model caches and stored datasets in air-gapped profile.
- **FR-009**: System MUST support Helm upgrade with zero-downtime rolling updates.
- **FR-010**: System MUST support Helm rollback to previous release version.

### Key Entities

- **HelmRelease**: Represents a deployed Helm release. Key attributes: release_name, chart_version, values_file, namespace, status, deployed_at.
- **HPAConfig**: Represents HPA configuration for a component. Key attributes: component_name, min_replicas, max_replicas, cpu_target, queue_depth_target, scale_up_stabilization, scale_down_stabilization.
- **HealthProbe**: Represents a Kubernetes health probe configuration. Key attributes: component_name, probe_type (liveness, readiness), path, initial_delay, period, timeout, failure_threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Connected deployment completes within 10 minutes from Helm install to all pods ready.
- **SC-002**: Air-gapped deployment completes without any external network requests.
- **SC-003**: HPA scales from 1 to 10 worker pods within 2 minutes of queue depth increase.
- **SC-004**: Helm upgrade completes with zero prediction failures during the rolling update.
- **SC-005**: Helm rollback completes within 2 minutes and restores the previous release state.
