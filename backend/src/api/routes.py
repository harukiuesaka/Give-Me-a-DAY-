"""
All API endpoints for Give Me a DAY v1.

Endpoint spec follows api_data_flow.md §5.
"""

import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.api.dependencies import get_audit_logger, get_store
from src.api.schemas import (
    ApproveRequest,
    ApproveResponse,
    CreateRunRequest,
    CreateRunResponse,
    PaperRunStatusResponse,
    ReApproveRequest,
    ReApproveResponse,
    RunStatusResponse,
    StopResponse,
)
from src.domain.models import AuditEvent, RunMeta, RunStatus
from src.pipeline.orchestrator import execute_pipeline

router = APIRouter()


# ---- Health check ----

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "give-me-a-day", "version": "1.0.0"}


# ---- Pipeline endpoints ----

@router.post("/runs", response_model=CreateRunResponse, status_code=202)
def create_run(request: CreateRunRequest):
    """Start a new pipeline run. Returns immediately with run_id."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    store = get_store()
    audit_logger = get_audit_logger()

    # Save initial run metadata
    meta = RunMeta(
        run_id=run_id,
        created_at=datetime.utcnow(),
        status=RunStatus.PENDING,
    )
    store.save_run_meta(run_id, meta)

    # Log pipeline start event
    audit_logger.append_event(AuditEvent(
        event_id=f"evt_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.utcnow(),
        run_id=run_id,
        event_type="pipeline.started",
        module="orchestrator",
        details={"raw_goal": request.goal},
    ))

    # Execute pipeline in background thread
    thread = threading.Thread(
        target=execute_pipeline,
        args=(run_id, request),
        daemon=True,
    )
    thread.start()

    return CreateRunResponse(
        run_id=run_id,
        status_url=f"/api/v1/runs/{run_id}/status",
    )


@router.get("/runs/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(run_id: str):
    """Poll pipeline progress."""
    store = get_store()
    if not store.run_exists(run_id):
        raise HTTPException(status_code=404, detail="Run not found")

    meta = store.load_run_meta(run_id)
    return RunStatusResponse(**meta)


@router.get("/runs/{run_id}/planning")
def get_planning_result(run_id: str):
    """Get planning pipeline results (Round 2: domain frame, spec, candidates, plans)."""
    store = get_store()
    if not store.run_exists(run_id):
        raise HTTPException(status_code=404, detail="Run not found")

    meta = store.load_run_meta(run_id)
    if meta.get("status") not in ("completed", "executing"):
        raise HTTPException(
            status_code=409,
            detail=f"Run status is '{meta.get('status')}', planning not available",
        )

    result: dict = {"run_id": run_id}

    # Load each planning artifact if available
    for key in ["user_intent", "domain_frame", "research_spec"]:
        try:
            result[key] = store.load_run_object(run_id, key)
        except FileNotFoundError:
            pass

    # Load per-candidate objects
    result["candidates"] = store.load_all_candidate_objects(run_id, "candidates")
    result["evidence_plans"] = store.load_all_candidate_objects(run_id, "evidence_plans")
    result["validation_plans"] = store.load_all_candidate_objects(run_id, "validation_plans")

    return result


@router.get("/runs/{run_id}/result")
def get_run_result(run_id: str):
    """Get candidate presentation after pipeline completion."""
    store = get_store()
    if not store.run_exists(run_id):
        raise HTTPException(status_code=404, detail="Run not found")

    meta = store.load_run_meta(run_id)
    if meta.get("status") != "completed":
        raise HTTPException(status_code=409, detail=f"Run status is '{meta.get('status')}', not 'completed'")

    try:
        cards = store.load_presentation(run_id, "candidate_cards.json")
        context = store.load_presentation(run_id, "presentation_context.json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Results not yet available")

    return {
        "run_id": run_id,
        "candidate_cards": cards,
        "presentation_context": context,
        "approval_url": f"/api/v1/runs/{run_id}/approve",
    }


@router.get("/runs/{run_id}/export")
def get_run_export(run_id: str):
    """Download Markdown export of recommendation package."""
    store = get_store()
    if not store.run_exists(run_id):
        raise HTTPException(status_code=404, detail="Run not found")

    try:
        content = store.load_markdown_export(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Export not available")

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=content, media_type="text/markdown")


# ---- Approval endpoint ----

@router.post("/runs/{run_id}/approve", response_model=ApproveResponse, status_code=201)
def approve_run(run_id: str, request: ApproveRequest):
    """Approve a candidate and start Paper Run."""
    store = get_store()
    if not store.run_exists(run_id):
        raise HTTPException(status_code=404, detail="Run not found")

    # Validate all confirmations are true
    required_keys = ["risks_reviewed", "stop_conditions_reviewed", "paper_run_understood"]
    for key in required_keys:
        if not request.user_confirmations.get(key, False):
            raise HTTPException(
                status_code=400, detail=f"Confirmation '{key}' must be true"
            )

    # TODO: Round 2+ — Create Approval object, initialize PaperRunState, register scheduler
    approval_id = f"{run_id}_AP"
    paper_run_id = f"pr_{uuid.uuid4().hex[:8]}"

    return ApproveResponse(
        approval_id=approval_id,
        paper_run_id=paper_run_id,
        status_url=f"/api/v1/paper-runs/{paper_run_id}",
    )


# ---- Paper Run endpoints ----

@router.get("/paper-runs/{pr_id}", response_model=PaperRunStatusResponse)
def get_paper_run_status(pr_id: str):
    """Get Paper Run status card."""
    store = get_store()
    if not store.paper_run_exists(pr_id):
        raise HTTPException(status_code=404, detail="Paper Run not found")

    state = store.load_paper_run_state(pr_id)
    snapshot = state.get("current_snapshot", {})
    safety = state.get("safety_status", {})
    schedule = state.get("schedule", {})

    return PaperRunStatusResponse(
        status=state.get("status", "unknown"),
        day_count=snapshot.get("day_count", 0),
        current_value=snapshot.get("virtual_capital_current", 0.0),
        total_return_pct=snapshot.get("total_return_pct", 0.0),
        safety_status="breached" if safety.get("any_breached") else "all_clear",
        next_report=schedule.get("next_monthly_report"),
        next_re_eval=schedule.get("next_quarterly_re_evaluation"),
    )


@router.post("/paper-runs/{pr_id}/stop", response_model=StopResponse)
def stop_paper_run(pr_id: str):
    """Manually stop a Paper Run."""
    store = get_store()
    if not store.paper_run_exists(pr_id):
        raise HTTPException(status_code=404, detail="Paper Run not found")

    # TODO: Round 6 — Update PaperRunState to halted, record in halt_history
    return StopResponse(status="halted")


@router.post("/paper-runs/{pr_id}/re-approve", response_model=ReApproveResponse, status_code=201)
def re_approve_paper_run(pr_id: str, request: ReApproveRequest):
    """Re-approve after halt or re-evaluation."""
    store = get_store()
    if not store.paper_run_exists(pr_id):
        raise HTTPException(status_code=404, detail="Paper Run not found")

    # TODO: Round 6 — Create new Approval, resume or start new PaperRun
    new_approval_id = f"reap_{uuid.uuid4().hex[:8]}"
    return ReApproveResponse(new_approval_id=new_approval_id, status="running")


@router.get("/paper-runs/{pr_id}/reports")
def list_monthly_reports(pr_id: str):
    """List all monthly reports for a Paper Run."""
    store = get_store()
    if not store.paper_run_exists(pr_id):
        raise HTTPException(status_code=404, detail="Paper Run not found")

    reports = store.load_monthly_reports(pr_id)
    return reports


@router.get("/paper-runs/{pr_id}/reports/{report_id}")
def get_monthly_report(pr_id: str, report_id: str):
    """Get a specific monthly report."""
    store = get_store()
    try:
        return store.load_monthly_report(pr_id, report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
