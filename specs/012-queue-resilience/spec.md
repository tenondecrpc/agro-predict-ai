# Feature Specification: Queue and Resilience

**Feature Branch**: `012-queue-resilience`  
**Created**: 2026-04-28  
**Status**: Implemented  
**Input**: ARQ workers, circuit breakers, dead letter queue, rate limiting, and graceful shutdown to checkpoint boundaries

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Asynchronous prediction processing via ARQ (Priority: P1)

Prediction requests are enqueued in Redis via ARQ and processed by worker pods. Workers consume jobs from the queue, execute the prediction pipeline, and store results. The system supports multiple workers for parallel processing and horizontal scaling.

**Why this priority**: Asynchronous processing enables the system to handle prediction loads that exceed synchronous request timeouts. It is essential for long-running predictions and batch processing.

**Independent Test**: Can be fully tested by submitting an async prediction request, verifying it is enqueued, and confirming a worker processes it and stores the result.

**Acceptance Scenarios**:

1. **Given** an async prediction request is submitted, **When** the request is accepted, **Then** a job is enqueued in ARQ and a job ID is returned to the caller.
2. **Given** a job is enqueued, **When** a worker is available, **Then** the worker processes the job and stores the prediction result.
3. **Given** multiple workers are running, **When** multiple jobs are enqueued, **Then** jobs are distributed across workers for parallel processing.

---

### User Story 2 - Dead letter queue for failed jobs (Priority: P2)

Jobs that fail after the configured retry limit are moved to a dead letter queue (DLQ). DLQ jobs are preserved for analysis and manual reprocessing. Operators can view DLQ contents, analyze failure patterns, and retry or discard individual jobs.

**Why this priority**: Without a DLQ, failed jobs are lost and their failure context is unrecoverable. The DLQ enables post-mortem analysis and manual recovery.

**Independent Test**: Can be tested by submitting a job that is guaranteed to fail, verifying it is moved to the DLQ after retries, and confirming the operator can view and retry it.

**Acceptance Scenarios**:

1. **Given** a job fails repeatedly, **When** the retry limit is exceeded, **Then** the job is moved to the DLQ with failure details.
2. **Given** a job is in the DLQ, **When** an operator views the DLQ, **Then** the job's failure details, retry history, and original payload are visible.
3. **Given** a job is in the DLQ, **When** an operator retries it, **Then** the job is re-enqueued for processing.

---

### User Story 3 - Graceful shutdown to checkpoint boundaries (Priority: P3)

When a worker pod is terminated (scaling down, node maintenance, deployment update), it completes its current job to the next checkpoint boundary before shutting down. No jobs are lost or left in an inconsistent state during shutdown.

**Why this priority**: Graceful shutdown ensures prediction integrity during operational events (scaling, updates, maintenance). Lost or corrupted predictions undermine user trust.

**Independent Test**: Can be tested by submitting a prediction, terminating the worker mid-execution, and verifying the job completes to the checkpoint or is safely re-queued.

**Acceptance Scenarios**:

1. **Given** a worker is processing a job, **When** a shutdown signal is received, **Then** the worker completes to the next checkpoint boundary before exiting.
2. **Given** a worker is terminated during a long-running job, **When** the job is re-queued, **Then** it resumes from the last checkpoint rather than starting over.
3. **Given** a graceful shutdown is in progress, **When** new jobs are submitted, **Then** they are routed to other available workers.

---

### Edge Cases

- What happens when Redis is unavailable (queue cannot be accessed)?
- How does the system handle a job that exceeds the maximum processing time?
- What happens when the DLQ itself becomes full?
- How does the system handle rate limiting for a tenant that is sending requests faster than allowed?
- What happens when all workers are terminated simultaneously (e.g., node failure)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use ARQ and Redis for asynchronous job queuing and processing.
- **FR-002**: System MUST support multiple ARQ workers for parallel job processing.
- **FR-003**: System MUST implement a dead letter queue (DLQ) for jobs that exceed the retry limit.
- **FR-004**: System MUST preserve DLQ jobs with failure details, retry history, and original payload.
- **FR-005**: System MUST allow operators to view, retry, and discard DLQ jobs.
- **FR-006**: System MUST implement circuit breakers for external service calls (weather APIs, satellite imagery, market data).
- **FR-007**: System MUST rate-limit prediction requests per tenant based on configured quotas.
- **FR-008**: System MUST support graceful shutdown to checkpoint boundaries for worker pods.
- **FR-009**: System MUST checkpoint job state at defined boundaries to enable resume after interruption.
- **FR-010**: System MUST support weighted-fair queueing to prevent tenant resource starvation.

### Key Entities

- **ARQJob**: Represents a queued prediction job. Key attributes: job_id, tenant_id, request_payload, status, enqueued_at, started_at, completed_at, retry_count, error_history.
- **DeadLetterJob**: Represents a job in the dead letter queue. Key attributes: dlq_id, original_job_id, failure_reason, retry_history, original_payload, enqueued_at, status (pending, retried, discarded).
- **CircuitBreaker**: Represents a circuit breaker for an external service. Key attributes: service_name, state (closed, open, half-open), failure_count, last_failure_at, opened_at, threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ARQ workers process jobs with a median latency of under 5 seconds from enqueue to start.
- **SC-002**: 100% of failed jobs (after retry limit) are preserved in the DLQ.
- **SC-003**: Graceful shutdown completes within 30 seconds with zero lost jobs.
- **SC-004**: Circuit breakers open within 30 seconds of detecting external service failure.
- **SC-005**: Rate limiting is accurate within 1% of configured quotas (no tenant exceeds quota by more than 1%).
