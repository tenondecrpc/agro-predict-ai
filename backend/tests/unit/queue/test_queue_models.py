from __future__ import annotations

from backend.queue.models import ARQJob, CircuitBreaker, DeadLetterJob


class TestARQJob:
    def test_job_lifecycle(self) -> None:
        job = ARQJob(tenant_id="t1", request_payload={"crop": "corn"})
        assert job.status == "pending"
        job.start()
        assert job.status == "running"
        job.complete()
        assert job.status == "completed"

    def test_job_retry(self) -> None:
        job = ARQJob(tenant_id="t1", request_payload={"crop": "corn"}, max_retries=3)
        job.fail("error 1")
        assert job.retry_count == 1
        assert job.status == "pending"
        job.fail("error 2")
        assert job.retry_count == 2
        assert job.status == "pending"
        job.fail("error 3")
        assert job.retry_count == 3
        assert job.status == "failed"
        assert job.should_move_to_dlq() is True


class TestDeadLetterJob:
    def test_dlq_creation(self) -> None:
        dlq = DeadLetterJob(
            original_job_id="job-123",
            failure_reason="Max retries exceeded",
            retry_history=["err1", "err2", "err3"],
            original_payload={"crop": "corn"},
            enqueued_at="2024-01-01T00:00:00+00:00",
        )
        assert dlq.status == "pending"

    def test_discard(self) -> None:
        dlq = DeadLetterJob(
            original_job_id="job-123",
            failure_reason="Max retries exceeded",
            retry_history=["err1"],
            original_payload={},
            enqueued_at="2024-01-01T00:00:00+00:00",
        )
        dlq.discard()
        assert dlq.status == "discarded"


class TestCircuitBreaker:
    def test_closed_state(self) -> None:
        cb = CircuitBreaker(service_name="weather-api")
        assert cb.can_execute() is True

    def test_opens_after_failures(self) -> None:
        cb = CircuitBreaker(service_name="weather-api", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_half_open_recovery(self) -> None:
        cb = CircuitBreaker(service_name="weather-api", failure_threshold=1)
        cb.record_failure()
        assert cb.state == "open"
        cb.record_success()
        assert cb.state == "half_open"
        assert cb.can_execute() is True
        cb.record_success()
        assert cb.state == "closed"
