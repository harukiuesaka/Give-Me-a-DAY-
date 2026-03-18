"""
Runtime Controller — Paper Run state management for v1.

This module handles:
- approval → paper_run_initialized
- lazy runtime reconciliation on status/report access
- minimal monthly report generation
- minimal quarterly re-evaluation outcomes
- narrow changed-candidate resumption after explicit re-approval

It does NOT implement background scheduling or notifications.
"""

import logging
import uuid
from datetime import date, datetime, timedelta

from pydantic import BaseModel

from src.config import settings
from src.domain.models import (
    Approval,
    AuditEvent,
    CurrentSnapshot,
    HaltEvent,
    MonthlyReport,
    PaperRunSchedule,
    PaperRunState,
    PaperRunStatus,
    PaperRunAttentionState,
    Recommendation,
    ReEvaluationOutcome,
    ReEvaluationResult,
    ReEvaluationTrigger,
    ReportNumbers,
    ReportPeriod,
    SafetyStatus,
)
from src.execution.paper_run_engine import update_paper_run
from src.persistence.store import PersistenceStore
from src.pipeline.approval_controller import extract_run_id_from_approval_id

logger = logging.getLogger(__name__)


class RuntimeNotInitializedError(Exception):
    """Raised when runtime status is requested but Paper Run is not initialized."""
    pass


class RuntimeResumeError(Exception):
    """Raised when a Paper Run cannot be resumed."""
    pass


class RuntimeRunnerHeartbeat(BaseModel):
    runner_id: str
    acquired_at: datetime
    last_heartbeat_at: datetime


def initialize_paper_run(approval: Approval) -> PaperRunState:
    """
    Initialize a PaperRunState from an Approval.

    This creates the initial state. Actual execution (daily cycles,
    signal generation, rebalancing) is NOT implemented here.
    That belongs to the Execution Layer (Round 3+).
    """
    now = datetime.utcnow()
    paper_run_id = f"pr_{uuid.uuid4().hex[:8]}"

    return PaperRunState(
        paper_run_id=paper_run_id,
        approval_id=approval.approval_id,
        candidate_id=approval.candidate_id,
        started_at=now,
        status=PaperRunStatus.RUNNING,
        current_snapshot=CurrentSnapshot(
            day_count=0,
            virtual_capital_initial=approval.runtime_config.initial_virtual_capital,
            virtual_capital_current=approval.runtime_config.initial_virtual_capital,
            total_return_pct=0.0,
            current_drawdown_pct=0.0,
            positions_count=0,
        ),
        safety_status=SafetyStatus(any_breached=False),
        schedule=PaperRunSchedule(
            next_monthly_report=(now + timedelta(days=30)).isoformat(),
            next_quarterly_re_evaluation=(now + timedelta(days=90)).isoformat(),
        ),
    )


def reconcile_paper_run(
    store: PersistenceStore,
    paper_run_id: str,
    as_of: datetime | None = None,
) -> PaperRunState:
    """
    Reconcile persisted Paper Run state up to ``as_of``.

    v1 keeps this mechanism simple and deterministic:
    - advance one simulated day per elapsed business day
    - persist daily snapshots
    - generate monthly report artifacts when due
    """
    state = PaperRunState(**store.load_paper_run_state(paper_run_id))
    as_of = as_of or datetime.utcnow()
    state_changed = False
    generated_events: list[AuditEvent] = []

    state, snapshots, halt_events = _advance_running_state(state, as_of)
    for snapshot_date, snapshot in snapshots:
        store.save_paper_run_snapshot(paper_run_id, snapshot_date, snapshot)
        state_changed = True
    generated_events.extend(halt_events)

    generated_reports, report_events = _generate_due_monthly_reports(store, state, as_of)
    if generated_reports:
        state_changed = True
    generated_events.extend(report_events)

    generated_re_evaluations, re_evaluation_events = _run_due_quarterly_re_evaluations(
        store,
        state,
        as_of,
    )
    if generated_re_evaluations:
        state_changed = True
    generated_events.extend(re_evaluation_events)

    if state_changed:
        store.save_paper_run_state(paper_run_id, state)
    _persist_lifecycle_events(store, state.paper_run_id, generated_events)
    sync_paper_run_attention(store, state.paper_run_id, state=state)

    return state


def halt_paper_run(
    store: PersistenceStore,
    paper_run_id: str,
    halted_at: datetime | None = None,
) -> PaperRunState:
    """Persist a manual halt for a Paper Run."""
    state = reconcile_paper_run(store, paper_run_id, as_of=halted_at)
    if state.status == PaperRunStatus.HALTED:
        return state

    halted_at = halted_at or datetime.utcnow()
    state.status = PaperRunStatus.HALTED
    state.halt_history.append(
        HaltEvent(
            halted_at=halted_at.isoformat(),
            condition_id="MANUAL_STOP",
        )
    )
    store.save_paper_run_state(paper_run_id, state)
    _persist_lifecycle_events(
        store,
        state.paper_run_id,
        [
            _build_halt_lifecycle_event(
                state=state,
                occurred_at=halted_at,
                condition_id="MANUAL_STOP",
                status_label=state.status.value,
                source="manual_stop",
            )
        ],
    )
    sync_paper_run_attention(store, state.paper_run_id, state=state)
    return state


def resume_paper_run(
    store: PersistenceStore,
    paper_run_id: str,
    approval_id: str,
    candidate_id: str | None = None,
    resumed_at: datetime | None = None,
) -> PaperRunState:
    """Resume a halted/paused run or apply an approved candidate change."""
    state = reconcile_paper_run(store, paper_run_id, as_of=resumed_at)
    if state.status == PaperRunStatus.RUNNING:
        raise RuntimeResumeError("この Paper Run はすでに稼働中です。")
    if state.status not in {
        PaperRunStatus.HALTED,
        PaperRunStatus.PAUSED,
        PaperRunStatus.RE_EVALUATING,
    }:
        raise RuntimeResumeError(
            f"status='{state.status.value}' の Paper Run は再承認で再開できません。"
        )

    resumed_at = resumed_at or datetime.utcnow()
    prior_status = state.status
    state.approval_id = approval_id
    state.status = PaperRunStatus.RUNNING
    state.safety_status = SafetyStatus(any_breached=False)

    if prior_status == PaperRunStatus.RE_EVALUATING:
        if not candidate_id:
            raise RuntimeResumeError("候補変更の再承認には新しい候補IDが必要です。")
        state.candidate_id = candidate_id
        state.schedule = PaperRunSchedule(
            next_monthly_report=(resumed_at + timedelta(days=30)).isoformat(),
            next_quarterly_re_evaluation=(resumed_at + timedelta(days=90)).isoformat(),
        )

    if prior_status in {PaperRunStatus.HALTED, PaperRunStatus.PAUSED} and state.halt_history:
        latest = state.halt_history[-1]
        latest.resumed_at = resumed_at.isoformat()
        latest.re_approval_id = approval_id

    store.save_paper_run_state(paper_run_id, state)
    sync_paper_run_attention(store, state.paper_run_id, state=state)
    return state


def reconcile_active_paper_runs(
    store: PersistenceStore,
    as_of: datetime | None = None,
) -> list[str]:
    """
    Reconcile every active Paper Run once.

    Returns the list of Paper Run IDs that were considered active for this cycle.
    """
    as_of = as_of or datetime.utcnow()
    reconciled_ids: list[str] = []

    for paper_run_id in store.list_paper_run_ids():
        state = PaperRunState(**store.load_paper_run_state(paper_run_id))
        if state.status not in {PaperRunStatus.RUNNING, PaperRunStatus.PAUSED}:
            continue
        reconcile_paper_run(store, paper_run_id, as_of=as_of)
        reconciled_ids.append(paper_run_id)

    return reconciled_ids


def ensure_runtime_runner_lease(
    store: PersistenceStore,
    runner_id: str,
    as_of: datetime | None = None,
) -> bool:
    """
    Refresh the runtime lease when owned by this runner or when the previous lease is stale.

    Returns True when this runner is allowed to proceed with reconciliation.
    """
    as_of = as_of or datetime.utcnow()
    heartbeat = _load_runtime_runner_heartbeat(store)

    if heartbeat is None:
        store.save_runtime_heartbeat(
            RuntimeRunnerHeartbeat(
                runner_id=runner_id,
                acquired_at=as_of,
                last_heartbeat_at=as_of,
            )
        )
        return True

    if heartbeat.runner_id == runner_id or _runtime_heartbeat_is_stale(heartbeat, as_of):
        acquired_at = heartbeat.acquired_at if heartbeat.runner_id == runner_id else as_of
        store.save_runtime_heartbeat(
            RuntimeRunnerHeartbeat(
                runner_id=runner_id,
                acquired_at=acquired_at,
                last_heartbeat_at=as_of,
            )
        )
        return True

    return False


def get_runtime_health(
    store: PersistenceStore,
    as_of: datetime | None = None,
) -> dict:
    """Return a small runtime-health signal based on the persisted runner heartbeat."""
    as_of = as_of or datetime.utcnow()
    heartbeat = _load_runtime_runner_heartbeat(store)

    if heartbeat is None:
        return {"status": "missing", "last_heartbeat_at": None}

    status = "stale" if _runtime_heartbeat_is_stale(heartbeat, as_of) else "healthy"
    return {
        "status": status,
        "last_heartbeat_at": heartbeat.last_heartbeat_at,
    }


def get_recent_lifecycle_events(
    store: PersistenceStore,
    paper_run_id: str,
    limit: int = 5,
) -> list[dict]:
    """Return recent Paper Run lifecycle events with small user-facing summaries."""
    events = [AuditEvent(**item) for item in store.load_paper_run_lifecycle_events(paper_run_id)]
    if not events:
        return []

    recent = sorted(events, key=lambda event: event.timestamp)[-limit:]
    return [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "summary": _summarize_lifecycle_event(event),
            "details": event.details,
        }
        for event in reversed(recent)
    ]


def get_paper_run_alert_summary(
    store: PersistenceStore,
    paper_run_id: str,
    state: PaperRunState | None = None,
) -> dict:
    """Return a compact attention summary derived from persisted lifecycle events."""
    attention = get_paper_run_attention_state(store, paper_run_id, state=state)
    return _attention_state_to_alert_summary(attention)


def get_latest_re_evaluation_result(
    store: PersistenceStore,
    paper_run_id: str,
) -> ReEvaluationResult | None:
    """Return the most recent persisted re-evaluation result, if any."""
    results = [
        ReEvaluationResult(**item)
        for item in store.load_re_evaluation_results(paper_run_id)
    ]
    if not results:
        return None
    return max(results, key=lambda result: result.executed_at)


def _advance_running_state(
    state: PaperRunState,
    as_of: datetime,
) -> tuple[PaperRunState, list[tuple[str, CurrentSnapshot]], list[AuditEvent]]:
    if state.status != PaperRunStatus.RUNNING:
        return state, [], []

    pending_days = _pending_business_days(
        started_at=state.started_at,
        completed_day_count=state.current_snapshot.day_count,
        as_of=as_of,
    )
    snapshots: list[tuple[str, CurrentSnapshot]] = []
    lifecycle_events: list[AuditEvent] = []

    for business_day in pending_days:
        prior_status = state.status
        state = update_paper_run(state)
        snapshots.append((business_day.isoformat(), state.current_snapshot.model_copy(deep=True)))
        if prior_status == PaperRunStatus.RUNNING and state.status != PaperRunStatus.RUNNING:
            if state.halt_history:
                latest_halt = state.halt_history[-1]
                lifecycle_events.append(
                    _build_halt_lifecycle_event(
                        state=state,
                        occurred_at=datetime.fromisoformat(latest_halt.halted_at),
                        condition_id=latest_halt.condition_id,
                        status_label=state.status.value,
                        source="execution",
                    )
                )
            break

    return state, snapshots, lifecycle_events


def _pending_business_days(
    started_at: datetime,
    completed_day_count: int,
    as_of: datetime,
) -> list[date]:
    if as_of.date() <= started_at.date():
        return []

    business_days: list[date] = []
    cursor = started_at.date() + timedelta(days=1)
    while cursor <= as_of.date():
        if cursor.weekday() < 5:
            business_days.append(cursor)
        cursor += timedelta(days=1)

    return business_days[completed_day_count:]


def _load_runtime_runner_heartbeat(store: PersistenceStore) -> RuntimeRunnerHeartbeat | None:
    data = store.load_runtime_heartbeat()
    if data is None:
        return None
    return RuntimeRunnerHeartbeat(**data)


def _latest_event_of_type(events: list[AuditEvent], event_type: str) -> AuditEvent | None:
    for event in reversed(events):
        if event.event_type == event_type:
            return event
    return None


def get_paper_run_attention_state(
    store: PersistenceStore,
    paper_run_id: str,
    state: PaperRunState | None = None,
) -> PaperRunAttentionState:
    """Return the persisted Paper Run attention item, deriving and saving it if needed."""
    if state is None:
        try:
            return PaperRunAttentionState(**store.load_paper_run_attention(paper_run_id))
        except FileNotFoundError:
            state = PaperRunState(**store.load_paper_run_state(paper_run_id))

    attention = _derive_paper_run_attention_state(store, state)
    store.save_paper_run_attention(paper_run_id, attention)
    return attention


def sync_paper_run_attention(
    store: PersistenceStore,
    paper_run_id: str,
    state: PaperRunState | None = None,
) -> PaperRunAttentionState:
    """Persist the current Paper Run attention item."""
    return get_paper_run_attention_state(store, paper_run_id, state=state)


def _derive_paper_run_attention_state(
    store: PersistenceStore,
    state: PaperRunState,
) -> PaperRunAttentionState:
    events = [AuditEvent(**item) for item in store.load_paper_run_lifecycle_events(state.paper_run_id)]

    latest_report_ready = _latest_event_of_type(events, "monthly_report_ready")
    latest_halted = _latest_event_of_type(events, "halted")
    latest_reapproval_required = _latest_event_of_type(events, "reapproval_required")
    latest_quarterly_outcome = _latest_event_of_type(events, "quarterly_re_evaluation_outcome")

    if state.status in {PaperRunStatus.HALTED, PaperRunStatus.PAUSED}:
        if latest_halted is not None:
            return _build_attention_state(
                event_type="halted",
                message=_summarize_lifecycle_event(latest_halted),
                source_event=latest_halted,
            )
        return _build_attention_state(
            event_type="halted",
            message="Paper Run を停止しました。",
        )

    if state.status == PaperRunStatus.RE_EVALUATING:
        if latest_reapproval_required is not None:
            return _build_attention_state(
                event_type="reapproval_required",
                message=_summarize_lifecycle_event(latest_reapproval_required),
                source_event=latest_reapproval_required,
            )
        if (
            latest_quarterly_outcome is not None
            and latest_quarterly_outcome.details.get("outcome") == ReEvaluationOutcome.CHANGE_CANDIDATE.value
        ):
            return _build_attention_state(
                event_type="review_required",
                message="四半期再評価の結果、候補の見直しが必要です。再承認してください。",
                source_event=latest_quarterly_outcome,
            )
        return _build_attention_state(event_type="none", message="対応が必要なイベントはありません。")

    if latest_report_ready is not None:
        return _build_attention_state(
            event_type="report_ready",
            message=_summarize_lifecycle_event(latest_report_ready),
            source_event=latest_report_ready,
        )

    return _build_attention_state(event_type="none", message="対応が必要なイベントはありません。")


def _build_attention_state(
    event_type: str,
    message: str,
    source_event: AuditEvent | None = None,
) -> PaperRunAttentionState:
    return PaperRunAttentionState(
        requires_attention=event_type != "none",
        event_type=None if event_type == "none" else event_type,
        summary=None if event_type == "none" else message,
        source_event_id=source_event.event_id if source_event else None,
        source_event_type=source_event.event_type if source_event else None,
        updated_at=source_event.timestamp if source_event else datetime.utcnow(),
    )


def _attention_state_to_alert_summary(attention: PaperRunAttentionState) -> dict:
    return {
        "alert_type": attention.event_type or "none",
        "message": attention.summary or "対応が必要なイベントはありません。",
        "source_event_id": attention.source_event_id,
        "source_event_type": attention.source_event_type,
        "timestamp": attention.updated_at,
    }


def _runtime_heartbeat_is_stale(
    heartbeat: RuntimeRunnerHeartbeat,
    as_of: datetime,
) -> bool:
    stale_after = timedelta(seconds=settings.RUNTIME_RUNNER_INTERVAL_SECONDS * 2)
    return as_of - heartbeat.last_heartbeat_at > stale_after


def _generate_due_monthly_reports(
    store: PersistenceStore,
    state: PaperRunState,
    as_of: datetime,
) -> tuple[list[MonthlyReport], list[AuditEvent]]:
    if state.schedule.next_monthly_report is None:
        return [], []
    if state.status not in {PaperRunStatus.RUNNING, PaperRunStatus.PAUSED}:
        return [], []

    snapshots = [
        (date.fromisoformat(snapshot_date), CurrentSnapshot(**snapshot))
        for snapshot_date, snapshot in store.load_paper_run_snapshots(state.paper_run_id)
    ]
    existing_reports = [MonthlyReport(**report) for report in store.load_monthly_reports(state.paper_run_id)]
    generated: list[MonthlyReport] = []
    lifecycle_events: list[AuditEvent] = []

    next_report_at = datetime.fromisoformat(state.schedule.next_monthly_report)
    while next_report_at <= as_of:
        report = _build_monthly_report(
            state,
            report_at=next_report_at,
            snapshots=snapshots,
            existing_reports=existing_reports,
        )
        store.save_monthly_report(state.paper_run_id, report.report_id, report)
        lifecycle_events.append(
            _build_monthly_report_ready_event(
                state=state,
                report=report,
                occurred_at=next_report_at,
            )
        )
        existing_reports.append(report)
        generated.append(report)
        next_report_at = next_report_at + timedelta(days=30)
        state.schedule.next_monthly_report = next_report_at.isoformat()

    return generated, lifecycle_events


def _run_due_quarterly_re_evaluations(
    store: PersistenceStore,
    state: PaperRunState,
    as_of: datetime,
) -> tuple[list[ReEvaluationResult], list[AuditEvent]]:
    if state.schedule.next_quarterly_re_evaluation is None:
        return [], []
    if state.status != PaperRunStatus.RUNNING:
        return [], []

    generated: list[ReEvaluationResult] = []
    lifecycle_events: list[AuditEvent] = []
    next_re_eval_at = datetime.fromisoformat(state.schedule.next_quarterly_re_evaluation)

    while next_re_eval_at <= as_of and state.status == PaperRunStatus.RUNNING:
        result = _build_re_evaluation_result(store, state, executed_at=next_re_eval_at)
        store.save_re_evaluation_result(state.paper_run_id, result.re_evaluation_id, result)
        generated.append(result)
        _apply_re_evaluation_outcome(state, result)
        lifecycle_events.append(
            _build_quarterly_re_evaluation_outcome_event(
                state=state,
                result=result,
            )
        )

        if result.outcome == ReEvaluationOutcome.CONTINUE:
            next_re_eval_at = next_re_eval_at + timedelta(days=90)
            state.schedule.next_quarterly_re_evaluation = next_re_eval_at.isoformat()
        elif result.outcome == ReEvaluationOutcome.CHANGE_CANDIDATE:
            lifecycle_events.append(
                _build_reapproval_required_event(
                    state=state,
                    result=result,
                )
            )
        else:
            lifecycle_events.append(
                _build_halt_lifecycle_event(
                    state=state,
                    occurred_at=result.executed_at,
                    condition_id="RE_EVALUATION_STOP",
                    status_label=state.status.value,
                    source="quarterly_re_evaluation",
                )
            )
            break

    return generated, lifecycle_events


def _build_re_evaluation_result(
    store: PersistenceStore,
    state: PaperRunState,
    executed_at: datetime,
) -> ReEvaluationResult:
    snapshot = state.current_snapshot
    total_return = snapshot.total_return_pct
    drawdown = snapshot.current_drawdown_pct
    new_best_candidate_id: str | None = None
    new_runner_up_candidate_id: str | None = None

    if total_return <= -12.0 or drawdown <= -15.0:
        outcome = ReEvaluationOutcome.STOP_ALL
        explanation = (
            "四半期再評価の結果、累積リターンまたはドローダウンが許容範囲を大きく下回りました。"
            "この候補は現状のまま継続すべきではないため、Paper Run を停止します。"
        )
        re_approval_required = True
    elif total_return < 0.0 or drawdown <= -8.0:
        new_best_candidate_id = _select_changed_candidate_id(store, state)
        if new_best_candidate_id:
            outcome = ReEvaluationOutcome.CHANGE_CANDIDATE
            new_runner_up_candidate_id = state.candidate_id
            explanation = (
                "四半期再評価の結果、現在の候補は継続より候補変更の検討が妥当と判断されました。"
                f"候補 '{new_best_candidate_id}' への切り替えには明示的な再承認が必要です。"
            )
        else:
            outcome = ReEvaluationOutcome.STOP_ALL
            explanation = (
                "四半期再評価の結果、現在の候補は継続より候補変更の検討が妥当と判断されました。"
                "ただし現在の推薦パッケージに切り替え可能な別候補がないため、Paper Run を停止します。"
            )
        re_approval_required = True
    else:
        outcome = ReEvaluationOutcome.CONTINUE
        explanation = (
            "四半期再評価の結果、現在の候補は継続可能と判断されました。"
            "次の四半期再評価まで Paper Run を続行します。"
        )
        re_approval_required = False

    return ReEvaluationResult(
        re_evaluation_id=f"re_{executed_at.strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}",
        paper_run_id=state.paper_run_id,
        executed_at=executed_at,
        trigger=ReEvaluationTrigger.QUARTERLY_SCHEDULE,
        outcome=outcome,
        new_run_id=None,
        new_best_candidate_id=new_best_candidate_id,
        new_runner_up_candidate_id=new_runner_up_candidate_id,
        explanation=explanation,
        re_approval_required=re_approval_required,
    )


def _apply_re_evaluation_outcome(
    state: PaperRunState,
    result: ReEvaluationResult,
) -> None:
    if result.outcome == ReEvaluationOutcome.CONTINUE:
        return

    state.schedule.next_monthly_report = None
    state.schedule.next_quarterly_re_evaluation = None

    if result.outcome == ReEvaluationOutcome.CHANGE_CANDIDATE:
        state.status = PaperRunStatus.RE_EVALUATING
        return

    state.status = PaperRunStatus.HALTED
    state.halt_history.append(
        HaltEvent(
            halted_at=result.executed_at.isoformat(),
            condition_id="RE_EVALUATION_STOP",
        )
    )


def _persist_lifecycle_events(
    store: PersistenceStore,
    paper_run_id: str,
    events: list[AuditEvent],
) -> None:
    for event in events:
        store.save_paper_run_lifecycle_event(paper_run_id, event.event_id, event)


def _paper_run_event_run_id(state: PaperRunState) -> str:
    run_id = extract_run_id_from_approval_id(state.approval_id)
    return run_id or state.paper_run_id


def _make_lifecycle_event(
    state: PaperRunState,
    event_type: str,
    occurred_at: datetime,
    details: dict,
) -> AuditEvent:
    return AuditEvent(
        event_id=f"evt_{occurred_at.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}",
        timestamp=occurred_at,
        run_id=_paper_run_event_run_id(state),
        paper_run_id=state.paper_run_id,
        event_type=event_type,
        module="runtime_controller",
        details=details,
    )


def _build_halt_lifecycle_event(
    state: PaperRunState,
    occurred_at: datetime,
    condition_id: str,
    status_label: str,
    source: str,
) -> AuditEvent:
    return _make_lifecycle_event(
        state,
        "halted",
        occurred_at,
        {
            "condition_id": condition_id,
            "status": status_label,
            "source": source,
        },
    )


def _build_monthly_report_ready_event(
    state: PaperRunState,
    report: MonthlyReport,
    occurred_at: datetime,
) -> AuditEvent:
    return _make_lifecycle_event(
        state,
        "monthly_report_ready",
        occurred_at,
        {
            "report_id": report.report_id,
            "period_start": report.period.start,
            "period_end": report.period.end,
        },
    )


def _build_quarterly_re_evaluation_outcome_event(
    state: PaperRunState,
    result: ReEvaluationResult,
) -> AuditEvent:
    return _make_lifecycle_event(
        state,
        "quarterly_re_evaluation_outcome",
        result.executed_at,
        {
            "re_evaluation_id": result.re_evaluation_id,
            "outcome": result.outcome.value,
            "explanation": result.explanation,
            "re_approval_required": result.re_approval_required,
            "new_best_candidate_id": result.new_best_candidate_id,
            "new_runner_up_candidate_id": result.new_runner_up_candidate_id,
        },
    )


def _build_reapproval_required_event(
    state: PaperRunState,
    result: ReEvaluationResult,
) -> AuditEvent:
    return _make_lifecycle_event(
        state,
        "reapproval_required",
        result.executed_at,
        {
            "re_evaluation_id": result.re_evaluation_id,
            "candidate_id": result.new_best_candidate_id,
            "previous_candidate_id": result.new_runner_up_candidate_id or state.candidate_id,
            "reason": result.explanation,
        },
    )


def _summarize_lifecycle_event(event: AuditEvent) -> str:
    details = event.details or {}
    event_type = event.event_type

    if event_type == "monthly_report_ready":
        report_id = details.get("report_id", "monthly report")
        period_end = details.get("period_end")
        if period_end:
            return f"月次レポート {report_id} を生成しました（{period_end}時点）。"
        return f"月次レポート {report_id} を生成しました。"

    if event_type == "quarterly_re_evaluation_outcome":
        outcome = details.get("outcome", "unknown")
        return f"四半期再評価を実施しました。結果: {outcome}。"

    if event_type == "reapproval_required":
        candidate_id = details.get("candidate_id") or "unknown"
        return f"候補 {candidate_id} の再承認が必要です。"

    if event_type == "halted":
        status_label = details.get("status", "halted")
        condition_id = details.get("condition_id")
        if status_label == "paused":
            return f"Paper Run を一時停止しました（{condition_id}）。"
        if condition_id == "MANUAL_STOP":
            return "Paper Run を手動停止しました。"
        if condition_id == "RE_EVALUATION_STOP":
            return "四半期再評価の結果、Paper Run を停止しました。"
        if condition_id:
            return f"Paper Run を停止しました（{condition_id}）。"
        return "Paper Run を停止しました。"

    return event_type


def _select_changed_candidate_id(
    store: PersistenceStore,
    state: PaperRunState,
) -> str | None:
    run_id = extract_run_id_from_approval_id(state.approval_id)
    if not run_id:
        return None

    try:
        recommendation = Recommendation(**store.load_run_object(run_id, "recommendation"))
    except FileNotFoundError:
        return None

    for candidate_id in (
        recommendation.best_candidate_id,
        recommendation.runner_up_candidate_id,
    ):
        if candidate_id and candidate_id != state.candidate_id:
            return candidate_id

    return None


def _build_monthly_report(
    state: PaperRunState,
    report_at: datetime,
    snapshots: list[tuple[date, CurrentSnapshot]],
    existing_reports: list[MonthlyReport],
) -> MonthlyReport:
    report_end = report_at.date()
    end_snapshot = _latest_snapshot_on_or_before(snapshots, report_end) or state.current_snapshot

    if existing_reports:
        previous_end = date.fromisoformat(existing_reports[-1].period.end)
        period_start = previous_end
        start_snapshot = _latest_snapshot_on_or_before(snapshots, previous_end)
        start_value = (
            start_snapshot.virtual_capital_current
            if start_snapshot is not None
            else state.current_snapshot.virtual_capital_initial
        )
    else:
        period_start = state.started_at.date()
        start_value = state.current_snapshot.virtual_capital_initial

    end_value = end_snapshot.virtual_capital_current
    monthly_return_pct = ((end_value / start_value) - 1) * 100 if start_value > 0 else 0.0

    next_step = (
        "再開には再承認が必要です。"
        if state.status == PaperRunStatus.HALTED
        else "次回の月次確認まで Paper Run を継続します。"
    )
    safety_note = (
        "停止条件が発動済みです。"
        if state.safety_status.any_breached
        else "現時点で停止条件の発動は確認されていません。"
    )
    summary = (
        f"{report_end.isoformat()}時点で{end_snapshot.day_count}営業日分のPaper Runを記録しました。"
        f"仮想資産は¥{end_value:,.0f}、累積リターンは{end_snapshot.total_return_pct:.2f}%です。"
    )

    return MonthlyReport(
        report_id=f"mr_{report_end.strftime('%Y%m%d')}",
        paper_run_id=state.paper_run_id,
        period=ReportPeriod(
            start=period_start.isoformat(),
            end=report_end.isoformat(),
        ),
        summary=summary,
        numbers=ReportNumbers(
            monthly_return_pct=round(monthly_return_pct, 4),
            benchmark_return_pct=0.0,
            cumulative_return_pct=end_snapshot.total_return_pct,
            current_drawdown_pct=end_snapshot.current_drawdown_pct,
            positions_count=end_snapshot.positions_count,
            trades_this_month=0,
        ),
        safety_note=safety_note,
        next=next_step,
    )


def _latest_snapshot_on_or_before(
    snapshots: list[tuple[date, CurrentSnapshot]],
    target_date: date,
) -> CurrentSnapshot | None:
    for snapshot_date, snapshot in reversed(snapshots):
        if snapshot_date <= target_date:
            return snapshot
    return None
