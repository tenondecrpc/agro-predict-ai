from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph

from backend.predictions.agents.data_analyst import DataAnalystAgent
from backend.predictions.agents.explainability import ExplainabilityAgent
from backend.predictions.agents.ml_executor import MLExecutorAgent
from backend.predictions.agents.recommendation_engine import RecommendationEngineAgent
from backend.predictions.agents.reviewer import ReviewerAgent
from backend.predictions.models import (
    AgentExecutionRecord,
    DataProvenanceEntry,
    ExplanationArtifactModel,
    PredictionInput,
    PredictionOutput,
    PredictionState,
    PredictionStatus,
)

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency when shadow comparisons are not needed.
_ShadowComparisonRepository: Any | None = None


def _get_shadow_repo() -> Any | None:
    global _ShadowComparisonRepository
    if _ShadowComparisonRepository is None:
        try:
            from backend.ml_models.shadow_repository import ShadowComparisonRepository

            _ShadowComparisonRepository = ShadowComparisonRepository
        except ImportError:
            _ShadowComparisonRepository = None
    return _ShadowComparisonRepository


class PredictionGraph:
    """LangGraph StateGraph-based prediction pipeline orchestrating five agents.

    Pipeline: data_analyst -> ml_executor -> recommendation_engine -> explainability -> reviewer

    Each node receives the accumulated PredictionState dict and returns a partial
    dict to merge into the state. Execution records are tracked in agent_executions_raw.
    """

    def __init__(
        self,
        *,
        data_analyst: DataAnalystAgent | None = None,
        ml_executor: MLExecutorAgent | None = None,
        recommendation_engine: RecommendationEngineAgent | None = None,
        explainability: ExplainabilityAgent | None = None,
        reviewer: ReviewerAgent | None = None,
        checkpointer: Any = None,
        llm_adapter: Any = None,
        database_url: str | None = None,
    ) -> None:
        self.data_analyst = data_analyst or DataAnalystAgent()
        self.ml_executor = ml_executor or MLExecutorAgent()
        self.recommendation_engine = recommendation_engine or RecommendationEngineAgent()
        self.explainability = explainability or ExplainabilityAgent()
        self.reviewer = reviewer or ReviewerAgent()
        self._checkpointer = checkpointer
        self._llm_adapter = llm_adapter
        self._database_url = database_url

        # Build and compile the LangGraph StateGraph
        self._graph = self._build_graph()
        self._compiled = self._graph.compile(checkpointer=self._checkpointer)

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(PredictionState)
        workflow.add_node("data_analyst", self._node_data_analyst)
        workflow.add_node("ml_executor", self._node_ml_executor)
        workflow.add_node("recommendation_engine", self._node_recommendation_engine)
        workflow.add_node("explainability", self._node_explainability)
        workflow.add_node("reviewer", self._node_reviewer)
        workflow.set_entry_point("data_analyst")
        workflow.add_edge("data_analyst", "ml_executor")
        workflow.add_edge("ml_executor", "recommendation_engine")
        workflow.add_edge("recommendation_engine", "explainability")
        workflow.add_edge("explainability", "reviewer")
        workflow.add_edge("reviewer", END)
        return workflow

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self, input_data: PredictionInput, *, model_version: str, thread_id: str | None = None
    ) -> PredictionOutput:
        result, _executions = self.execute_with_metadata(input_data, model_version=model_version, thread_id=thread_id)
        return result

    def execute_with_metadata(
        self,
        input_data: PredictionInput,
        *,
        model_version: str,
        thread_id: str | None = None,
    ) -> tuple[PredictionOutput, list[AgentExecutionRecord]]:
        tid = thread_id or str(uuid4())
        config: dict[str, Any] = {"configurable": {"thread_id": tid}}

        initial_state: PredictionState = {
            "tenant_id": input_data.tenant_id,
            "team_id": input_data.team_id,
            "crop": input_data.crop,
            "region": input_data.region,
            "input_data": dict(input_data.input_data),
            "model_version": model_version,
            "degradation_flags": [],
            "agent_executions_raw": [],
        }

        # Store input on state for legacy compat (nodes read from input_data key)
        initial_state["input"] = input_data  # type: ignore[assignment]

        final_state: PredictionState = self._compiled.invoke(initial_state, config=config)

        output = self._state_to_output(input_data, final_state)

        # Persist shadow comparison if shadow output was produced.
        ml_output = final_state.get("ml_output", {})
        shadow_output = ml_output.get("shadow_output")
        if shadow_output is not None and self._database_url:
            self._persist_shadow_comparison(
                prediction_id=output.prediction_id,
                ml_output=ml_output,
            )

        executions = self._raw_executions_to_records(final_state.get("agent_executions_raw", []), output.prediction_id)
        return output, executions

    # ------------------------------------------------------------------
    # LangGraph nodes
    # ------------------------------------------------------------------

    def _node_data_analyst(self, state: PredictionState) -> dict:
        input_data = state.get("input") or self._rebuild_input(state)
        executions = list(state.get("agent_executions_raw") or [])
        tenant_id = state.get("tenant_id", "unknown")
        start = perf_counter()
        started_at = datetime.now(UTC).isoformat()
        try:
            result = self.data_analyst.execute(input_data)
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "data_analyst", "success", duration_ms,
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "validated_data": result,
                "quality_flags": result.get("uncertainty_reasons", []),
                "data_provenance_raw": result.get("data_sources", []),
                "agent_executions_raw": executions,
            }
        except Exception as exc:
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "data_analyst", "error", duration_ms, str(exc),
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            # Escalate by setting escalation_reason
            return {
                "escalation_reason": str(exc),
                "agent_executions_raw": executions,
            }

    def _node_ml_executor(self, state: PredictionState) -> dict:
        # If escalation already set, skip
        if state.get("escalation_reason"):
            return {}

        input_data = state.get("input") or self._rebuild_input(state)
        model_version = state.get("model_version", "v1.2.0")
        executions = list(state.get("agent_executions_raw") or [])
        tenant_id = state.get("tenant_id", "unknown")
        start = perf_counter()
        started_at = datetime.now(UTC).isoformat()
        try:
            result = self.ml_executor.execute(input_data, model_version=model_version)
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "ml_executor", "success", duration_ms,
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            flags = list(state.get("degradation_flags") or [])
            flags.extend(result.get("degradation_flags", []))
            return {
                "ml_output": result,
                "confidence_interval": result.get("confidence_interval", {}),
                "feature_importance": result.get("feature_importance", {}),
                "degradation_flags": flags,
                "agent_executions_raw": executions,
            }
        except Exception:
            # Try fallback
            try:
                start2 = perf_counter()
                result = self.ml_executor.execute_with_fallback(input_data, primary_version=model_version)
                duration_ms = int((perf_counter() - start2) * 1000)
                executions.append(
                    self._make_exec_record(
                        "ml_executor", "degraded", duration_ms,
                        tenant_id=tenant_id, started_at=started_at,
                    )
                )
                flags = list(state.get("degradation_flags") or [])
                flags.extend(result.get("degradation_flags", []))
                return {
                    "ml_output": result,
                    "confidence_interval": result.get("confidence_interval", {}),
                    "feature_importance": result.get("feature_importance", {}),
                    "degradation_flags": flags,
                    "agent_executions_raw": executions,
                }
            except Exception as exc2:
                duration_ms2 = int((perf_counter() - start) * 1000)
                executions.append(
                    self._make_exec_record(
                        "ml_executor", "error", duration_ms2, str(exc2),
                        tenant_id=tenant_id, started_at=started_at,
                    )
                )
                return {
                    "escalation_reason": str(exc2),
                    "agent_executions_raw": executions,
                }

    def _node_recommendation_engine(self, state: PredictionState) -> dict:
        if state.get("escalation_reason"):
            return {}

        input_data = state.get("input") or self._rebuild_input(state)
        ml_output = state.get("ml_output", {})
        executions = list(state.get("agent_executions_raw") or [])
        tenant_id = state.get("tenant_id", "unknown")
        start = perf_counter()
        started_at = datetime.now(UTC).isoformat()
        try:
            result = self.recommendation_engine.execute(input_data, ml_output)
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "recommendation_engine", "success", duration_ms,
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "recommendation": result.get("recommendation", ""),
                "priority": result.get("priority", "low"),
                "actions": result.get("actions", []),
                "agent_executions_raw": executions,
            }
        except Exception as exc:
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "recommendation_engine", "error", duration_ms, str(exc),
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "escalation_reason": str(exc),
                "agent_executions_raw": executions,
            }

    def _node_explainability(self, state: PredictionState) -> dict:
        if state.get("escalation_reason"):
            return {}

        input_data = state.get("input") or self._rebuild_input(state)
        ml_output = state.get("ml_output", {})
        validated_data = state.get("validated_data", {})
        executions = list(state.get("agent_executions_raw") or [])
        tenant_id = state.get("tenant_id", "unknown")
        start = perf_counter()
        started_at = datetime.now(UTC).isoformat()
        try:
            result = self.explainability.execute(input_data, ml_output, validated_data)
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "explainability", "success", duration_ms,
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "explanation_artifact": result,
                "agent_executions_raw": executions,
            }
        except Exception as exc:
            duration_ms = int((perf_counter() - start) * 1000)
            flags = list(state.get("degradation_flags") or [])
            flags.extend(["explainability_failure", "missing_explanation_artifact"])
            executions.append(
                self._make_exec_record(
                    "explainability", "error", duration_ms, str(exc),
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "degradation_flags": flags,
                "agent_executions_raw": executions,
            }

    def _node_reviewer(self, state: PredictionState) -> dict:
        if state.get("escalation_reason"):
            return {}

        degradation_flags = list(state.get("degradation_flags") or [])

        # If explainability already failed, the pipeline is degraded.
        # Skip reviewer's mandatory checks (which require an explanation artifact)
        # and return a pre-approved degraded result to avoid spurious escalation.
        if "explainability_failure" in degradation_flags:
            executions = list(state.get("agent_executions_raw") or [])
            tenant_id = state.get("tenant_id", "unknown")
            executions.append(
                self._make_exec_record(
                    "reviewer", "degraded", 0, tenant_id=tenant_id,
                )
            )
            return {
                "review_result": {
                    "approved": True,
                    "review_status": "approved_with_caution",
                    "reviewer_notes": "Review skipped: explainability failure - degraded path.",
                    "degraded": True,
                    "confidence_level_at_review": 0.0,
                },
                "agent_executions_raw": executions,
            }

        input_data = state.get("input") or self._rebuild_input(state)
        ml_output = state.get("ml_output", {})
        expl_artifact = state.get("explanation_artifact", {})
        rec_result = {
            "recommendation": state.get("recommendation", ""),
            "priority": state.get("priority", "low"),
            "actions": state.get("actions", []),
        }
        executions = list(state.get("agent_executions_raw") or [])
        tenant_id = state.get("tenant_id", "unknown")
        start = perf_counter()
        started_at = datetime.now(UTC).isoformat()
        try:
            result = self.reviewer.execute(input_data, ml_output, expl_artifact, rec_result)
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "reviewer", "success", duration_ms,
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "review_result": result,
                "agent_executions_raw": executions,
            }
        except Exception as exc:
            duration_ms = int((perf_counter() - start) * 1000)
            executions.append(
                self._make_exec_record(
                    "reviewer", "error", duration_ms, str(exc),
                    tenant_id=tenant_id, started_at=started_at,
                )
            )
            return {
                "escalation_reason": str(exc),
                "agent_executions_raw": executions,
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_exec_record(
        agent_name: str,
        status: str,
        duration_ms: int,
        error: str | None = None,
        *,
        tenant_id: str = "unknown",
        started_at: str | None = None,
    ) -> dict:
        return {
            "agent_name": agent_name,
            "status": status,
            "duration_ms": duration_ms,
            "error_message": error,
            "completed_at": datetime.now(UTC).isoformat(),
            "tenant_id": tenant_id,
            "started_at": started_at or datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _rebuild_input(state: PredictionState) -> PredictionInput:
        """Reconstruct a PredictionInput from loose state keys when 'input' is missing."""
        return PredictionInput(
            tenant_id=state.get("tenant_id", "unknown"),
            team_id=state.get("team_id", "unknown"),
            crop=state.get("crop", "unknown"),
            region=state.get("region", "unknown"),
            time_horizon_days=30,
            input_data=state.get("input_data", {}),
        )

    def _state_to_output(self, input_data: PredictionInput, state: PredictionState) -> PredictionOutput:
        """Convert final LangGraph state to a PredictionOutput."""
        prediction_id = str(uuid4())
        escalation_reason = state.get("escalation_reason")
        ml_output = state.get("ml_output", {})
        expl_artifact = state.get("explanation_artifact", {})
        degradation_flags = list(state.get("degradation_flags") or [])
        review_result = state.get("review_result", {})

        if escalation_reason:
            return PredictionOutput(
                prediction_id=prediction_id,
                tenant_id=input_data.tenant_id,
                team_id=input_data.team_id,
                model_version="unknown",
                status=PredictionStatus.ESCALATED,
                output={},
                data_provenance=[],
                escalation_reason=escalation_reason,
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )

        # Build data provenance
        provenance_entries = [
            DataProvenanceEntry(
                source_id=p["source_id"],
                ingested_at=(
                    datetime.fromisoformat(p["ingested_at"])
                    if isinstance(p.get("ingested_at"), str)
                    else datetime.now(UTC)
                ),
                validation_status=p.get("validation_status", "passed"),
                checksum=p.get("checksum", ""),
            )
            for p in state.get("data_provenance_raw", [])
        ]

        is_degraded = ml_output.get("staleness_warning", False) or bool(degradation_flags)

        # Build explanation artifact if present
        explanation: ExplanationArtifactModel | None = None
        if expl_artifact:
            explanation = ExplanationArtifactModel(
                feature_scores=expl_artifact.get("feature_scores", {}),
                data_sources_used=expl_artifact.get("data_sources_used", []),
                confidence_level=expl_artifact.get("confidence_level", 0.0),
                uncertainty_factors=expl_artifact.get("uncertainty_factors", []),
                human_readable_summary=expl_artifact.get("human_readable_summary", ""),
            )

        if review_result.get("degraded"):
            degradation_flags.append("reviewer_flagged_degraded")

        status = PredictionStatus.DEGRADED if is_degraded else PredictionStatus.COMPLETED

        return PredictionOutput(
            prediction_id=prediction_id,
            tenant_id=input_data.tenant_id,
            team_id=input_data.team_id,
            model_version=ml_output.get("model_version", "unknown"),
            status=status,
            output={
                "yield_tons_per_hectare": ml_output.get("prediction"),
                "recommendation": state.get("recommendation"),
                "priority": state.get("priority"),
                "actions": state.get("actions"),
            },
            confidence_interval=ml_output.get("confidence_interval"),
            feature_importance=ml_output.get("feature_importance"),
            data_provenance=provenance_entries,
            explanation_artifact=explanation,
            degradation_flags=degradation_flags,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

    @staticmethod
    def _raw_executions_to_records(
        raw_executions: list[dict],
        prediction_id: str,
    ) -> list[AgentExecutionRecord]:
        # Map internal status names to AgentExecutionRecord Literal values
        _STATUS_MAP = {
            "error": "failure",
            "success": "success",
            "degraded": "degraded",
            "timeout": "timeout",
            "failure": "failure",
        }
        records = []
        for raw in raw_executions:
            agent_name = raw.get("agent_name", "unknown")
            # AgentExecutionRecord.agent_name is a Literal - only accept known names
            valid_names = {"data_analyst", "ml_executor", "recommendation_engine", "explainability", "reviewer"}
            if agent_name not in valid_names:
                continue
            raw_status = raw.get("status", "success")
            status = _STATUS_MAP.get(raw_status, "failure")
            records.append(
                AgentExecutionRecord(
                    prediction_id=prediction_id,
                    agent_name=agent_name,  # type: ignore[arg-type]
                    input_state={},
                    output_state={},
                    duration_ms=raw.get("duration_ms", 0),
                    status=status,  # type: ignore[arg-type]
                    error_message=raw.get("error_message"),
                )
            )
        return records

    def _persist_shadow_comparison(
        self,
        *,
        prediction_id: str,
        ml_output: dict,
    ) -> None:
        """Persist a shadow-mode comparison record to PostgreSQL."""
        shadow_output = ml_output.get("shadow_output")
        if shadow_output is None:
            return

        active_output = {
            "point_estimate": ml_output.get("prediction"),
            "confidence_interval": ml_output.get("confidence_interval", {}),
        }

        repo_cls = _get_shadow_repo()
        if repo_cls is None:
            logger.warning("shadow_comparison_repo_unavailable")
            return

        try:
            repo = repo_cls(database_url=self._database_url)
            repo.save_comparison(
                prediction_id=prediction_id,
                active_version=ml_output.get("model_version", "unknown"),
                shadow_version="shadow",
                active_output=active_output,
                shadow_output=shadow_output,
            )
        except Exception as exc:
            logger.warning("shadow_comparison_persist_failed", extra={"error": str(exc)})
