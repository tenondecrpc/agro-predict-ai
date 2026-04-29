## ADDED Requirements

### Requirement: Docker Compose worker service
The system SHALL include a `worker` service in `docker-compose.yml` that runs the ARQ worker process.

#### Scenario: Worker service starts with Docker Compose
- **WHEN** `make local-up` is executed
- **THEN** the worker service starts alongside PostgreSQL and Redis

#### Scenario: Worker service connects to Redis
- **WHEN** the worker service is running
- **THEN** it connects to the Redis service on port 6379

#### Scenario: Worker service depends on healthy Redis
- **WHEN** Redis is not yet healthy
- **THEN** the worker service waits for Redis health check before starting

### Requirement: Kubernetes worker deployment
The system SHALL deploy the ARQ worker as a separate Kubernetes Deployment with its own HPA.

#### Scenario: Worker deployment uses correct container command
- **WHEN** the worker deployment is created
- **THEN** the container command is `arq backend.worker.WorkerSettings`

#### Scenario: Worker deployment shares backend image
- **WHEN** the worker deployment is created
- **THEN** it uses the same container image as the backend

#### Scenario: Worker deployment has environment variables
- **WHEN** the worker deployment is created
- **THEN** it receives the same environment variables as the backend (database URL, Redis URL, encryption keys)

### Requirement: Worker HPA
The system SHALL include a HorizontalPodAutoscaler for the worker deployment that scales based on queue depth.

#### Scenario: HPA scales on ARQ queue length
- **WHEN** the ARQ queue length exceeds the target
- **THEN** the HPA increases the number of worker replicas

#### Scenario: HPA scales down when queue is empty
- **WHEN** the ARQ queue is empty for the cooldown period
- **THEN** the HPA reduces the number of worker replicas to the minimum

### Requirement: Worker resource quotas
The system SHALL define resource requests and limits for the worker deployment.

#### Scenario: Worker has memory request and limit
- **WHEN** the worker deployment is created
- **THEN** memory request is 512Mi and limit is 1Gi (configurable via Helm values)

#### Scenario: Worker has CPU request and limit
- **WHEN** the worker deployment is created
- **THEN** CPU request is 250m and limit is 500m (configurable via Helm values)
