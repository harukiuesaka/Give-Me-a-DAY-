"""
Pipeline orchestrator — sequences all pipeline modules.

Currently implements Round 1: Goal Intake only.
Remaining steps are stubbed with TODO markers.
"""

import logging
import uuid
from datetime import datetime

from src.api.dependencies import get_audit_logger, get_store
from src.api.schemas import CreateRunRequest
from src.domain.models import AuditEvent, RunMeta, RunStatus
from src.pipeline.goal_intake import process_goal_intake

logger = logging.getLogger(__name__)


def execute_pipeline(run_id: str, request: CreateRunRequest) -> str:
    """
    Execute the full pipeline synchronously.
    Called in a background thread from the API endpoint.

    Returns run_id on success.
    """
    store = get_store()
    audit_logger = get_audit_logger()

    try:
        # Update status: executing
        _update_status(store, run_id, RunStatus.EXECUTING, "goal_intake", 0)

        # ---- Step 1: Goal Intake ----
        user_intent = process_goal_intake(run_id, request)
        store.save_run_object(run_id, "user_intent", user_intent)

        audit_logger.append_event(AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            run_id=run_id,
            event_type="pipeline.step_completed",
            module="goal_intake",
            details={"step_name": "goal_intake", "output_entity_ids": [run_id]},
        ))

        _update_status(store, run_id, RunStatus.EXECUTING, "domain_framing", 1)

        # ---- Step 2: Domain Framing ----
        # TODO: Round 2 — DomainFramer.frame(user_intent)

        # ---- Step 3: Research Spec Compilation ----
        # TODO: Round 2 — ResearchSpecCompiler.compile(user_intent, domain_frame)

        # ---- Step 4: Candidate Generation ----
        # TODO: Round 2 — CandidateGenerator.generate(research_spec, domain_frame)

        # ---- Step 5: Evidence Planning + Data Acquisition ----
        # TODO: Round 2/3 — EvidencePlanner + ExecutionLayer.DataAcq

        # ---- Step 6: Validation Planning + Execution ----
        # TODO: Round 3 — ValidationPlanner + ExecutionLayer.ValidationExec

        # ---- Step 7: Audit + Recommendation + Reporting ----
        # TODO: Round 4/5 — AuditEngine + RecommendationEngine + ReportingEngine

        # For Round 1: mark as completed after Goal Intake
        _update_status(store, run_id, RunStatus.COMPLETED, "goal_intake", 1)

        logger.info(f"Pipeline completed for run {run_id} (Round 1: Goal Intake only)")
        return run_id

    except Exception as e:
        logger.exception(f"Pipeline failed for run {run_id}: {e}")

        audit_logger.append_event(AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
            run_id=run_id,
            event_type="pipeline.step_failed",
            module="orchestrator",
            details={"error_type": type(e).__name__, "error_message": str(e)},
        ))

        _update_status(store, run_id, RunStatus.FAILED, error=str(e))
        raise


def _update_status(
    store,
    run_id: str,
    status: RunStatus,
    current_step: str = "",
    steps_completed: int = 0,
    error: str | None = None,
) -> None:
    meta = RunMeta(
        run_id=run_id,
        created_at=datetime.utcnow(),
        status=status,
        current_step=current_step,
        steps_completed=steps_completed,
        error=error,
    )
    store.save_run_meta(run_id, meta)
