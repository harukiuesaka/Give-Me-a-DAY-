"""Tests for RuntimeController module."""

from datetime import datetime, timedelta

import pytest

from src.domain.models import (
    AuditEvent,
    ConfidenceLabel,
    CriticalCondition,
    Approval,
    CurrentSnapshot,
    ExpiryType,
    HaltEvent,
    MonthlyReport,
    OpenUnknown,
    PaperRunAttentionState,
    PaperRunState,
    PaperRunStatus,
    RankingLogicItem,
    Recommendation,
    RecommendationExpiry,
    ReEvaluationOutcome,
    ReEvaluationResult,
    RuntimeConfig,
    UserConfirmations,
)
from src.persistence.store import PersistenceStore
from src.pipeline.runtime_controller import (
    RuntimeRunnerHeartbeat,
    ensure_runtime_runner_lease,
    get_paper_run_alert_summary,
    get_runtime_health,
    halt_paper_run,
    initialize_paper_run,
    reconcile_active_paper_runs,
    reconcile_paper_run,
    resume_paper_run,
    sync_paper_run_attention,
    RuntimeResumeError,
)


def _make_approval(capital: float = 1_000_000) -> Approval:
    return Approval(
        approval_id="run_rt_test_AP_abc123",
        run_id="run_rt_test",
        candidate_id="C01",
        approved_at=datetime.utcnow(),
        user_confirmations=UserConfirmations(
            risks_reviewed=True,
            stop_conditions_reviewed=True,
            paper_run_understood=True,
        ),
        runtime_config=RuntimeConfig(initial_virtual_capital=capital),
    )


def _make_recommendation(best_id: str = "C01", runner_up_id: str | None = "C02") -> Recommendation:
    return Recommendation(
        run_id="run_rt_test",
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


class TestInitializePaperRun:
    def test_returns_paper_run_state(self):
        state = initialize_paper_run(_make_approval())
        assert isinstance(state, PaperRunState)

    def test_status_is_running(self):
        state = initialize_paper_run(_make_approval())
        assert state.status == PaperRunStatus.RUNNING

    def test_day_count_starts_at_zero(self):
        state = initialize_paper_run(_make_approval())
        assert state.current_snapshot.day_count == 0

    def test_capital_matches_approval(self):
        state = initialize_paper_run(_make_approval(capital=2_000_000))
        assert state.current_snapshot.virtual_capital_initial == 2_000_000
        assert state.current_snapshot.virtual_capital_current == 2_000_000

    def test_no_breach_initially(self):
        state = initialize_paper_run(_make_approval())
        assert state.safety_status.any_breached is False

    def test_schedule_set(self):
        state = initialize_paper_run(_make_approval())
        assert state.schedule.next_monthly_report is not None
        assert state.schedule.next_quarterly_re_evaluation is not None

    def test_paper_run_id_generated(self):
        state = initialize_paper_run(_make_approval())
        assert state.paper_run_id.startswith("pr_")

    def test_links_to_approval(self):
        approval = _make_approval()
        state = initialize_paper_run(approval)
        assert state.approval_id == approval.approval_id
        assert state.candidate_id == approval.candidate_id


class TestReconcilePaperRun:
    def test_advances_running_state_and_persists_snapshots(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=3)
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
            started_at.date().isoformat(),
            state.current_snapshot,
        )

        updated = reconcile_paper_run(store, state.paper_run_id, as_of=datetime.utcnow())

        assert updated.current_snapshot.day_count >= 1
        assert store.load_paper_run_state(state.paper_run_id)["current_snapshot"]["day_count"] >= 1
        assert len(store.load_paper_run_snapshots(state.paper_run_id)) >= 2

    def test_generates_monthly_report_artifact_when_due(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=35)
        next_report = started_at + timedelta(days=30)
        state = state.model_copy(
            update={
                "started_at": started_at,
                "schedule": state.schedule.model_copy(
                    update={
                        "next_monthly_report": next_report.isoformat(),
                        "next_quarterly_re_evaluation": (started_at + timedelta(days=90)).isoformat(),
                    }
                ),
            }
        )
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            started_at.date().isoformat(),
            state.current_snapshot,
        )

        reconcile_paper_run(store, state.paper_run_id, as_of=datetime.utcnow())
        reports = [MonthlyReport(**report) for report in store.load_monthly_reports(state.paper_run_id)]
        events = store.load_paper_run_lifecycle_events(state.paper_run_id)

        assert len(reports) == 1
        assert reports[0].summary
        assert reports[0].paper_run_id == state.paper_run_id
        assert events[0]["event_type"] == "monthly_report_ready"
        assert events[0]["details"]["report_id"] == reports[0].report_id

    def test_manual_halt_persists_halted_state(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        halted = halt_paper_run(store, state.paper_run_id)
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))
        events = store.load_paper_run_lifecycle_events(state.paper_run_id)

        assert halted.status == PaperRunStatus.HALTED
        assert persisted.status == PaperRunStatus.HALTED
        assert persisted.halt_history[-1].condition_id == "MANUAL_STOP"
        assert events[0]["event_type"] == "halted"
        assert events[0]["details"]["condition_id"] == "MANUAL_STOP"

    def test_resume_paper_run_sets_running_and_updates_halt_history(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state.status = PaperRunStatus.HALTED
        state.halt_history.append(
            HaltEvent(
                halted_at=datetime.utcnow().isoformat(),
                condition_id="MANUAL_STOP",
            ),
        )
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        resumed = resume_paper_run(store, state.paper_run_id, approval_id="run_rt_test_AP_new123")
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

        assert resumed.status == PaperRunStatus.RUNNING
        assert persisted.approval_id == "run_rt_test_AP_new123"
        assert persisted.halt_history[-1].re_approval_id == "run_rt_test_AP_new123"
        assert persisted.halt_history[-1].resumed_at is not None

    def test_resume_paper_run_applies_changed_candidate_from_re_evaluating(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state.status = PaperRunStatus.RE_EVALUATING
        state.schedule.next_monthly_report = None
        state.schedule.next_quarterly_re_evaluation = None
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        resumed = resume_paper_run(
            store,
            state.paper_run_id,
            approval_id="run_rt_test_AP_new123",
            candidate_id="C02",
        )
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

        assert resumed.status == PaperRunStatus.RUNNING
        assert persisted.candidate_id == "C02"
        assert persisted.approval_id == "run_rt_test_AP_new123"
        assert persisted.schedule.next_monthly_report is not None
        assert persisted.schedule.next_quarterly_re_evaluation is not None

    def test_resume_rejects_running_state(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        with pytest.raises(RuntimeResumeError):
            resume_paper_run(store, state.paper_run_id, approval_id="run_rt_test_AP_new123")


class TestActivePaperRunRunner:
    def test_runner_advances_active_run_without_endpoint_access(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=3)
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

        reconciled = reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

        assert reconciled == [state.paper_run_id]
        assert persisted.current_snapshot.day_count >= 1
        assert len(store.load_paper_run_snapshots(state.paper_run_id)) >= 2

    def test_runner_skips_halted_runs(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state = state.model_copy(update={"status": PaperRunStatus.HALTED})
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        reconciled = reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))

        assert reconciled == []
        assert persisted.current_snapshot.day_count == 0
        assert len(store.load_paper_run_snapshots(state.paper_run_id)) == 1

    def test_runner_generates_due_monthly_reports(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=35)
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

        reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        reports = [MonthlyReport(**report) for report in store.load_monthly_reports(state.paper_run_id)]

        assert len(reports) == 1
        assert reports[0].paper_run_id == state.paper_run_id
        assert reports[0].summary

    def test_runner_generates_continue_re_evaluation_and_keeps_run_active(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=95)
        state = state.model_copy(
            update={
                "started_at": started_at,
                "current_snapshot": CurrentSnapshot(
                    day_count=999,
                    virtual_capital_initial=1_000_000,
                    virtual_capital_current=1_080_000,
                    total_return_pct=8.0,
                    current_drawdown_pct=-4.0,
                    positions_count=5,
                ),
                "schedule": state.schedule.model_copy(
                    update={
                        "next_monthly_report": (started_at + timedelta(days=120)).isoformat(),
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

        reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))
        results = [ReEvaluationResult(**item) for item in store.load_re_evaluation_results(state.paper_run_id)]

        assert persisted.status == PaperRunStatus.RUNNING
        assert len(results) == 1
        assert results[0].outcome == ReEvaluationOutcome.CONTINUE
        assert persisted.schedule.next_quarterly_re_evaluation is not None

    def test_runner_generates_change_re_evaluation_and_pauses_runtime(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        store.save_run_object("run_rt_test", "recommendation", _make_recommendation())
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=95)
        state = state.model_copy(
            update={
                "started_at": started_at,
                "current_snapshot": CurrentSnapshot(
                    day_count=999,
                    virtual_capital_initial=1_000_000,
                    virtual_capital_current=960_000,
                    total_return_pct=-4.0,
                    current_drawdown_pct=-9.0,
                    positions_count=5,
                ),
                "schedule": state.schedule.model_copy(
                    update={
                        "next_monthly_report": (started_at + timedelta(days=120)).isoformat(),
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

        reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))
        results = [ReEvaluationResult(**item) for item in store.load_re_evaluation_results(state.paper_run_id)]
        events = store.load_paper_run_lifecycle_events(state.paper_run_id)

        assert persisted.status == PaperRunStatus.RE_EVALUATING
        assert len(results) == 1
        assert results[0].outcome == ReEvaluationOutcome.CHANGE_CANDIDATE
        assert results[0].new_best_candidate_id == "C02"
        assert results[0].new_runner_up_candidate_id == "C01"
        assert persisted.schedule.next_monthly_report is None
        assert persisted.schedule.next_quarterly_re_evaluation is None
        assert [event["event_type"] for event in events] == [
            "quarterly_re_evaluation_outcome",
            "reapproval_required",
        ]

    def test_runner_stops_when_change_candidate_has_no_alternative(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        store.save_run_object("run_rt_test", "recommendation", _make_recommendation(best_id="C01", runner_up_id=None))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=95)
        state = state.model_copy(
            update={
                "started_at": started_at,
                "current_snapshot": CurrentSnapshot(
                    day_count=999,
                    virtual_capital_initial=1_000_000,
                    virtual_capital_current=960_000,
                    total_return_pct=-4.0,
                    current_drawdown_pct=-9.0,
                    positions_count=5,
                ),
                "schedule": state.schedule.model_copy(
                    update={
                        "next_monthly_report": (started_at + timedelta(days=120)).isoformat(),
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

        reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))
        results = [ReEvaluationResult(**item) for item in store.load_re_evaluation_results(state.paper_run_id)]
        events = store.load_paper_run_lifecycle_events(state.paper_run_id)

        assert persisted.status == PaperRunStatus.HALTED
        assert len(results) == 1
        assert results[0].outcome == ReEvaluationOutcome.STOP_ALL
        assert [event["event_type"] for event in events] == [
            "quarterly_re_evaluation_outcome",
            "halted",
        ]

    def test_runner_generates_stop_re_evaluation_and_halts_run(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=95)
        state = state.model_copy(
            update={
                "started_at": started_at,
                "current_snapshot": CurrentSnapshot(
                    day_count=999,
                    virtual_capital_initial=1_000_000,
                    virtual_capital_current=850_000,
                    total_return_pct=-15.0,
                    current_drawdown_pct=-16.0,
                    positions_count=5,
                ),
                "schedule": state.schedule.model_copy(
                    update={
                        "next_monthly_report": (started_at + timedelta(days=120)).isoformat(),
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

        reconcile_active_paper_runs(store, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))
        results = [ReEvaluationResult(**item) for item in store.load_re_evaluation_results(state.paper_run_id)]
        events = store.load_paper_run_lifecycle_events(state.paper_run_id)

        assert persisted.status == PaperRunStatus.HALTED
        assert len(results) == 1
        assert results[0].outcome == ReEvaluationOutcome.STOP_ALL
        assert persisted.halt_history[-1].condition_id == "RE_EVALUATION_STOP"
        assert [event["event_type"] for event in events] == [
            "quarterly_re_evaluation_outcome",
            "halted",
        ]


class TestRuntimeRunnerHeartbeat:
    def test_heartbeat_persists_when_lease_is_acquired(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        now = datetime.utcnow()

        acquired = ensure_runtime_runner_lease(store, "runner_a", as_of=now)
        persisted = RuntimeRunnerHeartbeat(**store.load_runtime_heartbeat())

        assert acquired is True
        assert persisted.runner_id == "runner_a"
        assert persisted.acquired_at == now
        assert persisted.last_heartbeat_at == now

    def test_stale_heartbeat_can_be_taken_over_after_restart(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        now = datetime.utcnow()
        stale_at = now - timedelta(minutes=10)
        store.save_runtime_heartbeat(
            RuntimeRunnerHeartbeat(
                runner_id="runner_old",
                acquired_at=stale_at,
                last_heartbeat_at=stale_at,
            )
        )

        acquired = ensure_runtime_runner_lease(store, "runner_new", as_of=now)
        persisted = RuntimeRunnerHeartbeat(**store.load_runtime_heartbeat())

        assert acquired is True
        assert persisted.runner_id == "runner_new"
        assert persisted.acquired_at == now
        assert persisted.last_heartbeat_at == now

    def test_runtime_health_reflects_freshness(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        store.save_runtime_heartbeat(
            RuntimeRunnerHeartbeat(
                runner_id="runner_fresh",
                acquired_at=datetime.utcnow(),
                last_heartbeat_at=datetime.utcnow(),
            )
        )

        healthy = get_runtime_health(store, as_of=datetime.utcnow())
        assert healthy["status"] == "healthy"
        assert healthy["last_heartbeat_at"] is not None

        stale_at = datetime.utcnow() - timedelta(minutes=10)
        store.save_runtime_heartbeat(
            RuntimeRunnerHeartbeat(
                runner_id="runner_stale",
                acquired_at=stale_at,
                last_heartbeat_at=stale_at,
            )
        )
        stale = get_runtime_health(store, as_of=datetime.utcnow())
        assert stale["status"] == "stale"
        assert stale["last_heartbeat_at"] == stale_at


class TestPaperRunAlertSummary:
    def test_alert_summary_none_when_no_actionable_events(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        summary = get_paper_run_alert_summary(store, state.paper_run_id, state=state)

        assert summary["alert_type"] == "none"
        assert "対応が必要なイベントはありません" in summary["message"]

    def test_alert_summary_report_ready_for_monthly_report(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=35)
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

        reconcile_paper_run(store, state.paper_run_id, as_of=datetime.utcnow())
        persisted = PaperRunState(**store.load_paper_run_state(state.paper_run_id))
        summary = get_paper_run_alert_summary(store, state.paper_run_id, state=persisted)

        assert summary["alert_type"] == "report_ready"
        assert "月次レポート" in summary["message"]

    def test_alert_summary_halted_for_manual_stop(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        halted = halt_paper_run(store, state.paper_run_id)
        summary = get_paper_run_alert_summary(store, state.paper_run_id, state=halted)

        assert summary["alert_type"] == "halted"
        assert "停止" in summary["message"]

    def test_alert_summary_reapproval_required_for_re_evaluating_run(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state = state.model_copy(update={"status": PaperRunStatus.RE_EVALUATING})
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )
        store.save_paper_run_lifecycle_event(
            state.paper_run_id,
            "evt_test_reapproval",
            AuditEvent(
                event_id="evt_test_reapproval",
                timestamp=datetime.utcnow(),
                run_id="run_rt_test",
                paper_run_id=state.paper_run_id,
                event_type="reapproval_required",
                module="runtime_controller",
                details={
                    "re_evaluation_id": "re_test",
                    "candidate_id": "C02",
                    "previous_candidate_id": "C01",
                    "reason": "候補変更が必要です。",
                },
            ),
        )

        summary = get_paper_run_alert_summary(store, state.paper_run_id, state=state)

        assert summary["alert_type"] == "reapproval_required"
        assert "再承認" in summary["message"]

    def test_alert_summary_review_required_when_quarterly_change_needs_review(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state = state.model_copy(update={"status": PaperRunStatus.RE_EVALUATING})
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )
        store.save_paper_run_lifecycle_event(
            state.paper_run_id,
            "evt_test_quarterly",
            AuditEvent(
                event_id="evt_test_quarterly",
                timestamp=datetime.utcnow(),
                run_id="run_rt_test",
                paper_run_id=state.paper_run_id,
                event_type="quarterly_re_evaluation_outcome",
                module="runtime_controller",
                details={
                    "re_evaluation_id": "re_test",
                    "outcome": ReEvaluationOutcome.CHANGE_CANDIDATE.value,
                    "explanation": "候補見直しが必要です。",
                    "re_approval_required": True,
                    "new_best_candidate_id": "C02",
                    "new_runner_up_candidate_id": "C01",
                },
            ),
        )

        summary = get_paper_run_alert_summary(store, state.paper_run_id, state=state)

        assert summary["alert_type"] == "review_required"
        assert "見直し" in summary["message"]


class TestPaperRunAttentionPersistence:
    def test_attention_none_when_no_actionable_events(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        persisted = sync_paper_run_attention(store, state.paper_run_id, state=state)
        loaded = PaperRunAttentionState(**store.load_paper_run_attention(state.paper_run_id))

        assert persisted.requires_attention is False
        assert loaded.requires_attention is False
        assert loaded.event_type is None

    def test_monthly_report_ready_becomes_attention(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        started_at = datetime.utcnow() - timedelta(days=35)
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

        reconcile_paper_run(store, state.paper_run_id, as_of=datetime.utcnow())
        loaded = PaperRunAttentionState(**store.load_paper_run_attention(state.paper_run_id))

        assert loaded.requires_attention is True
        assert loaded.event_type == "report_ready"
        assert loaded.source_event_type == "monthly_report_ready"

    def test_halted_becomes_attention(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )

        halt_paper_run(store, state.paper_run_id)
        loaded = PaperRunAttentionState(**store.load_paper_run_attention(state.paper_run_id))

        assert loaded.requires_attention is True
        assert loaded.event_type == "halted"
        assert loaded.summary and "停止" in loaded.summary

    def test_reapproval_required_becomes_attention(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state = state.model_copy(update={"status": PaperRunStatus.RE_EVALUATING})
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )
        store.save_paper_run_lifecycle_event(
            state.paper_run_id,
            "evt_test_reapproval_attention",
            AuditEvent(
                event_id="evt_test_reapproval_attention",
                timestamp=datetime.utcnow(),
                run_id="run_rt_test",
                paper_run_id=state.paper_run_id,
                event_type="reapproval_required",
                module="runtime_controller",
                details={
                    "re_evaluation_id": "re_test",
                    "candidate_id": "C02",
                    "previous_candidate_id": "C01",
                    "reason": "候補変更が必要です。",
                },
            ),
        )

        sync_paper_run_attention(store, state.paper_run_id, state=state)
        loaded = PaperRunAttentionState(**store.load_paper_run_attention(state.paper_run_id))

        assert loaded.requires_attention is True
        assert loaded.event_type == "reapproval_required"
        assert loaded.source_event_type == "reapproval_required"

    def test_review_required_becomes_attention(self, tmp_path):
        store = PersistenceStore(data_dir=str(tmp_path))
        state = initialize_paper_run(_make_approval())
        state = state.model_copy(update={"status": PaperRunStatus.RE_EVALUATING})
        store.save_paper_run_state(state.paper_run_id, state)
        store.save_paper_run_snapshot(
            state.paper_run_id,
            state.started_at.date().isoformat(),
            state.current_snapshot,
        )
        store.save_paper_run_lifecycle_event(
            state.paper_run_id,
            "evt_test_review_attention",
            AuditEvent(
                event_id="evt_test_review_attention",
                timestamp=datetime.utcnow(),
                run_id="run_rt_test",
                paper_run_id=state.paper_run_id,
                event_type="quarterly_re_evaluation_outcome",
                module="runtime_controller",
                details={
                    "re_evaluation_id": "re_test",
                    "outcome": ReEvaluationOutcome.CHANGE_CANDIDATE.value,
                    "explanation": "候補見直しが必要です。",
                    "re_approval_required": True,
                    "new_best_candidate_id": "C02",
                    "new_runner_up_candidate_id": "C01",
                },
            ),
        )

        sync_paper_run_attention(store, state.paper_run_id, state=state)
        loaded = PaperRunAttentionState(**store.load_paper_run_attention(state.paper_run_id))

        assert loaded.requires_attention is True
        assert loaded.event_type == "review_required"
        assert loaded.source_event_type == "quarterly_re_evaluation_outcome"
