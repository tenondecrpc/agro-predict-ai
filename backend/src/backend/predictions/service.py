from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.predictions.graph import PredictionGraph
from backend.predictions.models import PredictionInput, PredictionOutput
from backend.predictions.repository import PredictionRepository

if TYPE_CHECKING:
    from backend.predictions.agent_execution_repository import AgentExecutionRepositoryProtocol
    from backend.predictions.field_data_resolver import FieldDataResolver

logger = logging.getLogger(__name__)


class PredictionService:
    """Orchestration layer for prediction requests.

    Coordinates graph execution, result persistence, and retrieval.
    Optionally injects a FieldDataResolver to source input features from APEX.
    """

    def __init__(
        self,
        *,
        repository: PredictionRepository,
        graph: PredictionGraph | None = None,
        field_data_resolver: FieldDataResolver | None = None,
        agent_exec_repository: AgentExecutionRepositoryProtocol | None = None,
    ) -> None:
        self.repository = repository
        self.graph = graph or PredictionGraph()
        self._field_data_resolver = field_data_resolver
        self._agent_exec_repository = agent_exec_repository

    def execute(self, input_data: PredictionInput, *, model_version: str) -> PredictionOutput:
        # If a FieldDataResolver is configured and no manual input, resolve from APEX
        if self._field_data_resolver is not None and not input_data.input_data:
            resolved = self._field_data_resolver.resolve(
                tenant_id=input_data.tenant_id,
                crop=input_data.crop,
                region=input_data.region,
                manual_input=None,
            )
            # Replace input_data with resolved features
            input_data = input_data.model_copy(
                update={
                    "input_data": resolved.feature_dict,
                    "input_data_hash": "",  # Will be recomputed
                }
            )

        result, executions = self.graph.execute_with_metadata(input_data, model_version=model_version)
        self.repository.save(result)

        # Persist agent execution records
        if self._agent_exec_repository is not None:
            for exec_record in executions:
                self._agent_exec_repository.save(exec_record)

        return result

    def get_prediction(self, prediction_id: str, *, tenant_id: str) -> PredictionOutput | None:
        return self.repository.get_by_id(prediction_id, tenant_id=tenant_id)

    def list_predictions(self, tenant_id: str) -> list[PredictionOutput]:
        return self.repository.list_by_tenant(tenant_id)

    def get_dead_letter_record(self, run_id: str, *, tenant_id: str) -> dict | None:
        """Retrieve a dead letter record for retry."""
        return self.repository.get_dead_letter_record(run_id, tenant_id=tenant_id)

    def archive_dead_letter_record(self, run_id: str, *, tenant_id: str) -> None:
        """Archive a dead letter record after successful retry."""
        self.repository.archive_dead_letter_record(run_id, tenant_id=tenant_id)

    def list_failed_predictions(self, tenant_id: str) -> list[PredictionOutput]:
        """List failed predictions for a tenant."""
        return self.repository.list_failed_predictions(tenant_id)
