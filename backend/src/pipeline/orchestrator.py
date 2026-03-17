"""
Pipeline orchestrator — sequences all pipeline modules.

Round 1: Goal Intake only.
Round 2: Goal Intake → DomainFramer → ResearchSpecCompiler
         → CandidateGenerator → EvidencePlanner → ValidationPlanner
Round 2.5: + RecommendationEngine + PresentationBuilder
Round 3+: Execution, Audit (TODO).
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
        _log_step(audit_logger, run_id, "goal_intake")
        _update_status(store, run_id, RunStatus.EXECUTING, "domain_framing", 1)

        # ---- Step 2: Domain Framing ----
        from src.pipeline.domain_framer import frame
        domain_frame = frame(user_intent)
        store.save_run_object(run_id, "domain_frame", domain_frame)
        _log_step(audit_logger, run_id, "domain_framing")
        _update_status(store, run_id, RunStatus.EXECUTING, "research_spec", 2)

        # ---- Step 3: Research Spec Compilation ----
        from src.pipeline.research_spec_compiler import compile
        research_spec = compile(user_intent, domain_frame)
        store.save_run_object(run_id, "research_spec", research_spec)
        _log_step(audit_logger, run_id, "research_spec")
        _update_status(store, run_id, RunStatus.EXECUTING, "candidate_generation", 3)

        # ---- Step 4: Candidate Generation ----
        from src.pipeline.candidate_generator import generate
        candidates = generate(research_spec, domain_frame)
        for candidate in candidates:
            store.save_candidate_object(
                run_id, "candidates", candidate.candidate_id, candidate
            )
        _log_step(audit_logger, run_id, "candidate_generation",
                  {"candidate_count": len(candidates)})
        _update_status(store, run_id, RunStatus.EXECUTING, "evidence_planning", 4)

        # ---- Step 5: Evidence Planning ----
        from src.pipeline.evidence_planner import plan as plan_evidence
        evidence_plans = []
        for candidate in candidates:
            ep = plan_evidence(research_spec, candidate)
            store.save_candidate_object(
                run_id, "evidence_plans", candidate.candidate_id, ep
            )
            evidence_plans.append(ep)
        _log_step(audit_logger, run_id, "evidence_planning",
                  {"plans_count": len(evidence_plans)})
        _update_status(store, run_id, RunStatus.EXECUTING, "validation_planning", 5)

        # ---- Step 6: Validation Planning ----
        from src.pipeline.validation_planner import plan as plan_validation
        validation_plans = []
        for candidate, ep in zip(candidates, evidence_plans):
            vp = plan_validation(research_spec, candidate, ep)
            store.save_candidate_object(
                run_id, "validation_plans", candidate.candidate_id, vp
            )
            validation_plans.append(vp)
        _log_step(audit_logger, run_id, "validation_planning",
                  {"plans_count": len(validation_plans)})

        # ---- Step 7: Recommendation ----
        _update_status(store, run_id, RunStatus.EXECUTING, "recommendation", 6)
        from src.pipeline.recommendation_engine import build_recommendation
        recommendation = build_recommendation(
            run_id, research_spec, candidates, evidence_plans, validation_plans,
        )
        store.save_run_object(run_id, "recommendation", recommendation)
        _log_step(audit_logger, run_id, "recommendation")

        # ---- Step 8: Presentation ----
        _update_status(store, run_id, RunStatus.EXECUTING, "presentation", 7)
        from src.pipeline.presentation_builder import (
            build_markdown_export,
            build_presentation,
        )
        cards, context = build_presentation(recommendation, candidates)
        store.save_presentation_list(run_id, "candidate_cards.json", cards)
        store.save_presentation(run_id, "presentation_context.json", context)

        # Markdown export
        raw_goal = request.goal if hasattr(request, "goal") else ""
        md_export = build_markdown_export(cards, context, raw_goal)
        store.save_markdown_export(run_id, md_export)
        _log_step(audit_logger, run_id, "presentation",
                  {"cards_count": len(cards)})

        # ---- Done (Round 2.5) ----
        # TODO: Round 3+ — ExecutionLayer, AuditEngine
        _update_status(store, run_id, RunStatus.COMPLETED, "presentation", 8)

        logger.info(
            f"Pipeline completed for run {run_id} "
            f"(Round 2: Planning Intelligence — {len(candidates)} candidates, "
            f"{len(validation_plans)} validation plans)"
        )
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


def _log_step(
    audit_logger, run_id: str, step_name: str, extra: dict | None = None
) -> None:
    """Log a pipeline step completion event."""
    details = {"step_name": step_name}
    if extra:
        details.update(extra)
    audit_logger.append_event(AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.utcnow(),
        run_id=run_id,
        event_type="pipeline.step_completed",
        module=step_name,
        details=details,
    ))


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
