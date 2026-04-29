## ADDED Requirements

### Requirement: ARQ WorkerSettings class
The system SHALL provide an ARQ `WorkerSettings` class in `backend/src/backend/worker.py` that registers all job handler functions and configures worker lifecycle hooks.

#### Scenario: WorkerSettings is importable by ARQ CLI
- **WHEN** ARQ is invoked with `arq backend.worker.WorkerSettings`
- **THEN** the WorkerSettings class is found and loaded without errors

#### Scenario: WorkerSettings registers prediction job handler
- **WHEN** WorkerSettings is instantiated
- **THEN** the `functions` tuple includes `process_prediction_run`

#### Scenario: WorkerSettings configures lifecycle hooks
- **WHEN** WorkerSettings is instantiated
- **THEN** `on_startup` and `on_shutdown` hooks are configured

### Requirement: process_prediction_run job handler
The system SHALL provide an ARQ job handler `process_prediction_run` that executes the full prediction pipeline asynchronously.

#### Scenario: Handler receives job kwargs and builds PredictionInput
- **WHEN** `process_prediction_run` is called with kwargs containing `tenant_id`, `team_id`, `run_id`, and prediction data
- **THEN** a valid `PredictionInput` object is constructed

#### Scenario: Handler executes PredictionGraph
- **WHEN** a valid `PredictionInput` is available
- **THEN** the `PredictionGraph.execute()` method is called and returns a `PredictionOutput`

#### Scenario: Handler stores result in PostgreSQL
- **WHEN** the prediction graph completes successfully
- **THEN** the `PredictionOutput` is stored via `PostgresRunRepository`

#### Scenario: Handler captures terminal failures
- **WHEN** the prediction graph raises an unhandled exception
- **THEN** the failure is captured via `RedisWorkerController.capture_terminal_failure()` and the job is marked for DLQ

#### Scenario: Handler updates worker controller state
- **WHEN** the prediction graph completes (success or failure)
- **THEN** the worker controller's in-flight counter is decremented and the checkpoint is released

### Requirement: Worker lifecycle hooks
The system SHALL implement `on_startup` and `on_shutdown` hooks for the ARQ worker process.

#### Scenario: on_startup initializes worker controller
- **WHEN** the ARQ worker process starts
- **THEN** the `WorkerBootstrap` is built and the worker ID is registered with the worker controller

#### Scenario: on_shutdown drains worker gracefully
- **WHEN** the ARQ worker process receives a shutdown signal
- **THEN** `begin_drain(worker_id)` is called to stop accepting new jobs

#### Scenario: on_shutdown completes current job
- **WHEN** shutdown is in progress and a job is being processed
- **THEN** the job completes to the next checkpoint boundary before the process exits

### Requirement: Worker health reporting
The system SHALL expose worker health information including active job count, queue depth, and error rate.

#### Scenario: Health endpoint reports worker status
- **WHEN** the health check endpoint is queried
- **THEN** the response includes worker status with active job count and queue depth

#### Scenario: Health reports degraded when queue is backed up
- **WHEN** the queue depth exceeds the configured threshold
- **THEN** the health status reflects degraded worker capacity

### Requirement: Configurable job timeout
The system SHALL allow configurable job timeout for prediction runs via environment variable.

#### Scenario: Default timeout is 300 seconds
- **WHEN** no timeout is configured
- **THEN** the default job timeout is 300 seconds

#### Scenario: Custom timeout via environment variable
- **WHEN** `BACKEND_WORKER_JOB_TIMEOUT_SECONDS` is set to a positive integer
- **THEN** the job timeout uses the configured value
