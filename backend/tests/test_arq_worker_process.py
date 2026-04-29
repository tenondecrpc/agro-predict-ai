from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from backend.persistence.testing.worker import InMemoryWorkerController
from backend.predictions.models import DataProvenanceEntry, PredictionOutput, PredictionStatus
from backend.worker import WorkerSettings, on_shutdown, on_startup, process_prediction_run


class _Repo:
    def __init__(self) -> None:
        self.saved: list[PredictionOutput] = []

    def save(self, prediction: PredictionOutput) -> PredictionOutput:
        self.saved.append(prediction)
        return prediction


class _Graph:
    def execute(self, prediction_input, *, model_version: str):
        return PredictionOutput(
            tenant_id=prediction_input.tenant_id,
            team_id=prediction_input.team_id,
            model_version=model_version,
            status=PredictionStatus.COMPLETED,
            output={"recommendation": "irrigate"},
            data_provenance=[
                DataProvenanceEntry(
                    source_id="manual",
                    ingested_at="2026-04-29T00:00:00Z",
                    validation_status="passed",
                    checksum="abc",
                )
            ],
        )


class _FailingGraph:
    def execute(self, prediction_input, *, model_version: str):
        raise RuntimeError("graph exploded")


def _persistence(controller: InMemoryWorkerController, repo: _Repo):
    return SimpleNamespace(
        worker_controller=controller,
        prediction_repository=repo,
        redis=SimpleNamespace(configured=False),
    )


def test_worker_settings_registers_prediction_handler() -> None:
    assert process_prediction_run in WorkerSettings.functions
    assert WorkerSettings.on_startup is on_startup
    assert WorkerSettings.on_shutdown is on_shutdown
    assert WorkerSettings.job_timeout == 300


def test_process_prediction_run_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = InMemoryWorkerController()
    repo = _Repo()
    monkeypatch.setattr("backend.worker._persistence", _persistence(controller, repo))
    monkeypatch.setattr("backend.worker._worker_id", "worker-test")
    monkeypatch.setattr("backend.worker.PredictionGraph", _Graph)

    result = asyncio.run(
        process_prediction_run(
            {"job_id": "job-1"},
            tenant_id="tenant-1",
            team_id="team-1",
            run_id="run-1",
            crop="corn",
            region="north",
            input_data={"temperature": 22.0},
            model_version="v1.2.0",
        )
    )

    assert result["status"] == "completed"
    assert len(repo.saved) == 1
    assert controller.active_jobs == {}


def test_process_prediction_run_failure_captures_dlq(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = InMemoryWorkerController()
    repo = _Repo()
    monkeypatch.setattr("backend.worker._persistence", _persistence(controller, repo))
    monkeypatch.setattr("backend.worker._worker_id", "worker-test")
    monkeypatch.setattr("backend.worker.PredictionGraph", _FailingGraph)

    with pytest.raises(RuntimeError, match="graph exploded"):
        asyncio.run(
            process_prediction_run(
                {"job_id": "job-1"},
                tenant_id="tenant-1",
                team_id="team-1",
                run_id="run-1",
                crop="corn",
                region="north",
                input_data={"temperature": 22.0},
            )
        )

    assert controller.dead_letter_records
    assert controller.dead_letter_records[0].run_id == "run-1"


def test_worker_lifecycle_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    controller = InMemoryWorkerController()
    repo = _Repo()
    persistence = _persistence(controller, repo)
    monkeypatch.setattr("backend.worker.build_persistence_adapters", lambda: persistence)
    monkeypatch.setattr("backend.worker._persistence", None)
    monkeypatch.setattr("backend.worker._worker_id", "worker-test")
    ctx: dict[str, object] = {}

    asyncio.run(on_startup(ctx))
    asyncio.run(on_shutdown(ctx))

    assert ctx["worker_id"] == "worker-test"
    assert "worker-test" in controller.draining_workers
