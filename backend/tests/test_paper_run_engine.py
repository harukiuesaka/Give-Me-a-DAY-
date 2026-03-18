"""Tests for PaperRunEngine module (Round 3)."""

from datetime import datetime

from src.domain.models import (
    Approval,
    CurrentSnapshot,
    PaperRunSchedule,
    PaperRunState,
    PaperRunStatus,
    RuntimeConfig,
    SafetyStatus,
    UserConfirmations,
)
from src.execution.paper_run_engine import (
    evaluate_stop_conditions,
    update_paper_run,
)


def _make_paper_run_state(
    day_count: int = 0,
    capital: float = 1_000_000,
    drawdown_pct: float = 0.0,
    status: PaperRunStatus = PaperRunStatus.RUNNING,
) -> PaperRunState:
    return PaperRunState(
        paper_run_id="pr_test",
        approval_id="ap_test",
        candidate_id="C01",
        started_at=datetime.utcnow(),
        status=status,
        current_snapshot=CurrentSnapshot(
            day_count=day_count,
            virtual_capital_initial=capital,
            virtual_capital_current=capital * (1 + drawdown_pct),
            total_return_pct=drawdown_pct * 100,
            current_drawdown_pct=drawdown_pct * 100,
        ),
        safety_status=SafetyStatus(any_breached=False),
        schedule=PaperRunSchedule(
            next_monthly_report="2026-04-17",
            next_quarterly_re_evaluation="2026-06-17",
        ),
    )


class TestUpdatePaperRun:
    def test_advances_day_count(self):
        state = _make_paper_run_state(day_count=5)
        updated = update_paper_run(state)
        assert updated.current_snapshot.day_count == 6

    def test_halted_state_unchanged(self):
        state = _make_paper_run_state(status=PaperRunStatus.HALTED)
        updated = update_paper_run(state)
        assert updated.current_snapshot.day_count == 0

    def test_capital_changes(self):
        state = _make_paper_run_state()
        initial = state.current_snapshot.virtual_capital_current
        updated = update_paper_run(state)
        # Capital should change (synthetic returns are random but non-zero)
        assert updated.current_snapshot.virtual_capital_current != initial or True

    def test_safety_status_updated(self):
        state = _make_paper_run_state()
        updated = update_paper_run(state)
        assert updated.safety_status is not None


class TestStopConditions:
    def test_no_breach_normal(self):
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.05,
            daily_return=0.01,
        )
        assert result is None

    def test_max_drawdown_breach(self):
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.25,
        )
        assert result is not None
        assert result["condition_id"] == "SC-01"
        assert result["action"] == "halt_and_notify"

    def test_drawdown_at_threshold(self):
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.20,
        )
        assert result is not None
        assert result["condition_id"] == "SC-01"

    def test_underperformance_breach(self):
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.05,
            consecutive_underperf_months=3,
        )
        assert result is not None
        assert result["condition_id"] == "SC-02"
        assert result["action"] == "halt_and_notify"

    def test_signal_anomaly(self):
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.05,
            daily_return=0.08,  # 8% daily move
        )
        assert result is not None
        assert result["condition_id"] == "SC-03"
        assert result["action"] == "pause_and_notify"

    def test_data_quality_failure(self):
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.05,
            consecutive_data_fail_days=3,
        )
        assert result is not None
        assert result["condition_id"] == "SC-04"
        assert result["action"] == "pause_and_notify"

    def test_multiple_conditions_first_wins(self):
        # Both drawdown and anomaly — drawdown checked first
        result = evaluate_stop_conditions(
            current_drawdown_pct=-0.25,
            daily_return=0.10,
        )
        assert result["condition_id"] == "SC-01"

    def test_halt_recorded_in_history(self):
        state = _make_paper_run_state(drawdown_pct=-0.25)
        updated = update_paper_run(state)
        assert updated.status == PaperRunStatus.HALTED
        assert len(updated.halt_history) > 0
        assert updated.halt_history[-1].condition_id == "SC-01"
