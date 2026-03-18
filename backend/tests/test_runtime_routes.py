"""Focused tests for Paper Run runtime routes."""

from datetime import datetime, timedelta

from fastapi import HTTPException

from src.api import routes
from src.api.schemas import ReApproveRequest
from src.domain.models import (
    Approval,
    AuditEvent,
    ConfidenceLabel,
    CriticalCondition,
    ExpiryType,
    HaltEvent,
    OpenUnknown,
    PaperRunState,
    PaperRunStatus,
    RankingLogicItem,
    Recommendation,
    RecommendationExpiry,
    ReEvaluationOutcome,
    ReEvaluationResult,
    ReEvaluationTrigger,
    RuntimeConfig,
    UserConfirmations,
)
from src.persistence.audit_log import AuditLogger
from src.persistence.store import PersistenceStore
from src.pipeline.runtime_controller import RuntimeRunnerHeartbeat, initialize_paper_run


def _make_approval(capital: float = 1_000_000) -> Approval:
    return Approval(
        approval_id="run_rt_routes_AP_abc123",
        run_id="run_rt_routes",
        candidate_id="C01",
        approved_at=datetime.utcnow(),
        user_confirmations=UserConfirmations(
            risks_reviewed=True,
            stop_conditions_reviewed=True,
            paper_run_understood=True,
        ),
        runtime_config=RuntimeConfig(initial_virtual_capital=capital),
    )


def _seed_paper_run(store: PersistenceStore, age_days: int = 0) -> PaperRunState:
    state = initialize_paper_run(_make_approval())
    if age_days > 0:
        started_at = datetime.utcnow() - timedelta(days=age_days)
        state = state.model_copy(
            update={
                "started_at": started_at,
                "schedule": state.schedule.model_copy(
                    update={
                        "next_monthly_report": (started_at + timedelta(days=30)).isoformat(),
                        "next_quarterly_re_evaluation": (started_at + timedelta(days=90)).isoformat(),
                    }
                ),
            }
        )
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_paper_run_snapshot(
        state.paper_run_id,
        state.started_at.date().isoformat(),
        state.current_snapshot,
    )
    return state


def _make_recommendation(best_id: str = "C01", runner_up_id: str | None = "C02") -> Recommendation:
    return Recommendation(
        run_id="run_rt_routes",
        best_candidate_id=best_id,
        runner_up_candidate_id=runner_up_id,
        rejected_candidate_ids=[],
        ranking_logic=[
            RankingLogicItem(
                comparison_axis="execution",
                best_assessment="best",
                runner_up_assessment="runner",
                verdict="execution-first",
            ),
            RankingLogicItem(
                comparison_axis="validation",
                best_assessment="best",
                runner_up_assessment="runner",
                verdict="validated",
            ),
            RankingLogicItem(
                comparison_axis="risk",
                best_assessment="best",
                runner_up_assessment="runner",
                verdict="risk-balanced",
            ),
        ],
        open_unknowns=[
            OpenUnknown(
                unknown_id="OU-01",
                description="unknown",
                impact_if_resolved_positively="upside",
                impact_if_resolved_negatively="downside",
                resolution_method="monitor",
            )
        ],
        critical_conditions=[
            CriticalCondition(
                condition_id="CC-01",
                statement="condition",
                verification_method="method",
                verification_timing="timing",
                source="source",
            )
        ],
        confidence_label=ConfidenceLabel.MEDIUM,
        confidence_explanation="説明",
        recommendation_expiry=RecommendationExpiry(
            type=ExpiryType.TIME_BASED,
            description="3ヶ月後",
        ),
    )


def test_get_paper_run_status_reconciles_state(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store, age_days=3)
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.get_paper_run_status(state.paper_run_id)
    persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

    assert response.candidate_id == state.candidate_id
    assert response.day_count >= 1
    assert persisted.current_snapshot.day_count == response.day_count
    assert response.status == PaperRunStatus.RUNNING.value


def test_get_paper_run_status_includes_monthly_report_event(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store, age_days=35)
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.get_paper_run_status(state.paper_run_id)

    assert response.events
    assert response.events[0].event_type == "monthly_report_ready"
    assert "月次レポート" in response.events[0].summary
    assert response.alert_summary.alert_type == "report_ready"
    assert "月次レポート" in response.alert_summary.message


def test_stop_paper_run_persists_halt(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.stop_paper_run(state.paper_run_id)
    status_response = routes.get_paper_run_status(state.paper_run_id)
    persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

    assert response.status == "halted"
    assert persisted.status == PaperRunStatus.HALTED
    assert persisted.halt_history[-1].condition_id == "MANUAL_STOP"
    assert status_response.events[0].event_type == "halted"
    assert "停止" in status_response.events[0].summary
    assert status_response.alert_summary.alert_type == "halted"
    assert "停止" in status_response.alert_summary.message


def test_get_paper_run_status_includes_reapproval_required_alert(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state = state.model_copy(update={"status": PaperRunStatus.RE_EVALUATING})
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_paper_run_lifecycle_event(
        state.paper_run_id,
        "evt_reapproval_required",
        AuditEvent(
            event_id="evt_reapproval_required",
            timestamp=datetime.utcnow(),
            run_id="run_rt_routes",
            paper_run_id=state.paper_run_id,
            event_type="reapproval_required",
            module="runtime_controller",
            details={
                "re_evaluation_id": "re_001",
                "candidate_id": "C02",
                "previous_candidate_id": "C01",
                "reason": "候補変更が必要です。",
            },
        ),
    )
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.get_paper_run_status(state.paper_run_id)

    assert response.alert_summary.alert_type == "reapproval_required"
    assert "再承認" in response.alert_summary.message


def test_get_paper_run_status_includes_review_required_alert(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state = state.model_copy(update={"status": PaperRunStatus.RE_EVALUATING})
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_paper_run_lifecycle_event(
        state.paper_run_id,
        "evt_quarterly_review_required",
        AuditEvent(
            event_id="evt_quarterly_review_required",
            timestamp=datetime.utcnow(),
            run_id="run_rt_routes",
            paper_run_id=state.paper_run_id,
            event_type="quarterly_re_evaluation_outcome",
            module="runtime_controller",
            details={
                "re_evaluation_id": "re_002",
                "outcome": ReEvaluationOutcome.CHANGE_CANDIDATE.value,
                "explanation": "候補見直しが必要です。",
                "re_approval_required": True,
                "new_best_candidate_id": "C02",
                "new_runner_up_candidate_id": "C01",
            },
        ),
    )
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.get_paper_run_status(state.paper_run_id)

    assert response.alert_summary.alert_type == "review_required"
    assert "見直し" in response.alert_summary.message


def test_list_monthly_reports_generates_due_artifact(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store, age_days=35)
    monkeypatch.setattr(routes, "get_store", lambda: store)

    reports = routes.list_monthly_reports(state.paper_run_id)

    assert len(reports) == 1
    assert reports[0]["paper_run_id"] == state.paper_run_id
    assert reports[0]["summary"]


def test_reapprove_paper_run_resumes_halted_run(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    audit_logger = AuditLogger(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state.status = PaperRunStatus.HALTED
    state.halt_history.append(
        HaltEvent(
            halted_at=datetime.utcnow().isoformat(),
            condition_id="MANUAL_STOP",
        )
    )
    store.save_paper_run_state(state.paper_run_id, state)
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "get_audit_logger", lambda: audit_logger)

    response = routes.re_approve_paper_run(
        state.paper_run_id,
        ReApproveRequest(
            candidate_id=state.candidate_id,
            user_confirmations={
                "risks_reviewed": True,
                "stop_conditions_reviewed": True,
                "paper_run_understood": True,
            },
        ),
    )
    persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

    assert response.status == "running"
    assert response.new_approval_id == persisted.approval_id
    assert persisted.status == PaperRunStatus.RUNNING
    assert persisted.halt_history[-1].re_approval_id == persisted.approval_id


def test_reapprove_paper_run_rejects_running_state(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    audit_logger = AuditLogger(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "get_audit_logger", lambda: audit_logger)

    try:
        routes.re_approve_paper_run(
            state.paper_run_id,
            ReApproveRequest(
                candidate_id=state.candidate_id,
                user_confirmations={
                    "risks_reviewed": True,
                    "stop_conditions_reviewed": True,
                    "paper_run_understood": True,
                },
            ),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 409


def test_reapprove_paper_run_requires_explicit_confirmations(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    audit_logger = AuditLogger(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state.status = PaperRunStatus.HALTED
    store.save_paper_run_state(state.paper_run_id, state)
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "get_audit_logger", lambda: audit_logger)

    try:
        routes.re_approve_paper_run(
            state.paper_run_id,
            ReApproveRequest(
                candidate_id=state.candidate_id,
                user_confirmations={
                    "risks_reviewed": True,
                    "stop_conditions_reviewed": False,
                    "paper_run_understood": True,
                },
            ),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_get_paper_run_status_includes_pending_candidate_for_re_evaluating(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state.status = PaperRunStatus.RE_EVALUATING
    state.schedule.next_monthly_report = None
    state.schedule.next_quarterly_re_evaluation = None
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_re_evaluation_result(
        state.paper_run_id,
        "re_pending",
        ReEvaluationResult(
            re_evaluation_id="re_pending",
            paper_run_id=state.paper_run_id,
            executed_at=datetime.utcnow(),
            trigger=ReEvaluationTrigger.QUARTERLY_SCHEDULE,
            outcome=ReEvaluationOutcome.CHANGE_CANDIDATE,
            new_best_candidate_id="C02",
            new_runner_up_candidate_id="C01",
            explanation="候補 C02 への切り替えを再承認待ちです。",
            re_approval_required=True,
        ),
    )
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.get_paper_run_status(state.paper_run_id)

    assert response.status == PaperRunStatus.RE_EVALUATING.value
    assert response.candidate_id == "C01"
    assert response.pending_candidate_id == "C02"
    assert response.re_evaluation_note == "候補 C02 への切り替えを再承認待ちです。"
    assert response.events == []


def test_get_paper_run_status_includes_quarterly_re_evaluation_events(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store, age_days=95)
    state = state.model_copy(
        update={
            "current_snapshot": state.current_snapshot.model_copy(
                update={
                    "virtual_capital_current": 960_000,
                    "total_return_pct": -4.0,
                    "current_drawdown_pct": -9.0,
                }
            ),
        }
    )
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_run_object("run_rt_routes", "recommendation", _make_recommendation(best_id="C02", runner_up_id="C01"))
    monkeypatch.setattr(routes, "get_store", lambda: store)

    response = routes.get_paper_run_status(state.paper_run_id)

    assert response.status == PaperRunStatus.RE_EVALUATING.value
    assert response.pending_candidate_id == "C02"
    event_types = [event.event_type for event in response.events]
    assert "quarterly_re_evaluation_outcome" in event_types
    assert "reapproval_required" in event_types
    assert any(event.event_type == "reapproval_required" and "再承認" in event.summary for event in response.events)


def test_reapprove_paper_run_applies_changed_candidate(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    audit_logger = AuditLogger(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state.status = PaperRunStatus.RE_EVALUATING
    state.schedule.next_monthly_report = None
    state.schedule.next_quarterly_re_evaluation = None
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_re_evaluation_result(
        state.paper_run_id,
        "re_pending",
        ReEvaluationResult(
            re_evaluation_id="re_pending",
            paper_run_id=state.paper_run_id,
            executed_at=datetime.utcnow(),
            trigger=ReEvaluationTrigger.QUARTERLY_SCHEDULE,
            outcome=ReEvaluationOutcome.CHANGE_CANDIDATE,
            new_best_candidate_id="C02",
            new_runner_up_candidate_id="C01",
            explanation="候補 C02 への切り替えを再承認待ちです。",
            re_approval_required=True,
        ),
    )
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "get_audit_logger", lambda: audit_logger)

    response = routes.re_approve_paper_run(
        state.paper_run_id,
        ReApproveRequest(
            candidate_id="C02",
            user_confirmations={
                "risks_reviewed": True,
                "stop_conditions_reviewed": True,
                "paper_run_understood": True,
            },
        ),
    )
    persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

    assert response.status == "running"
    assert response.new_approval_id == persisted.approval_id
    assert persisted.status == PaperRunStatus.RUNNING
    assert persisted.candidate_id == "C02"
    assert persisted.schedule.next_monthly_report is not None
    assert persisted.schedule.next_quarterly_re_evaluation is not None


def test_reapprove_paper_run_rejects_non_pending_changed_candidate(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    audit_logger = AuditLogger(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    state.status = PaperRunStatus.RE_EVALUATING
    state.schedule.next_monthly_report = None
    state.schedule.next_quarterly_re_evaluation = None
    store.save_paper_run_state(state.paper_run_id, state)
    store.save_re_evaluation_result(
        state.paper_run_id,
        "re_pending",
        ReEvaluationResult(
            re_evaluation_id="re_pending",
            paper_run_id=state.paper_run_id,
            executed_at=datetime.utcnow(),
            trigger=ReEvaluationTrigger.QUARTERLY_SCHEDULE,
            outcome=ReEvaluationOutcome.CHANGE_CANDIDATE,
            new_best_candidate_id="C02",
            new_runner_up_candidate_id="C01",
            explanation="候補 C02 への切り替えを再承認待ちです。",
            re_approval_required=True,
        ),
    )
    monkeypatch.setattr(routes, "get_store", lambda: store)
    monkeypatch.setattr(routes, "get_audit_logger", lambda: audit_logger)

    try:
        routes.re_approve_paper_run(
            state.paper_run_id,
            ReApproveRequest(
                candidate_id="C03",
                user_confirmations={
                    "risks_reviewed": True,
                    "stop_conditions_reviewed": True,
                    "paper_run_understood": True,
                },
            ),
        )
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400


def test_get_paper_run_status_reports_runtime_health_freshness(monkeypatch, tmp_path):
    store = PersistenceStore(data_dir=str(tmp_path))
    state = _seed_paper_run(store)
    monkeypatch.setattr(routes, "get_store", lambda: store)

    fresh = routes.get_paper_run_status(state.paper_run_id)
    assert fresh.runtime_health.status == "missing"
    assert fresh.runtime_health.last_heartbeat_at is None

    now = datetime.utcnow()
    store.save_runtime_heartbeat(
        RuntimeRunnerHeartbeat(
            runner_id="runner_fresh",
            acquired_at=now,
            last_heartbeat_at=now,
        )
    )
    healthy = routes.get_paper_run_status(state.paper_run_id)
    assert healthy.runtime_health.status == "healthy"
    assert healthy.runtime_health.last_heartbeat_at == now

    stale_at = datetime.utcnow() - timedelta(minutes=10)
    store.save_runtime_heartbeat(
        RuntimeRunnerHeartbeat(
            runner_id="runner_stale",
            acquired_at=stale_at,
            last_heartbeat_at=stale_at,
        )
    )
    stale = routes.get_paper_run_status(state.paper_run_id)
    assert stale.runtime_health.status == "stale"
    assert stale.runtime_health.last_heartbeat_at == stale_at
