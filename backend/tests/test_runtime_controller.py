"""Tests for RuntimeController module (Round 2.5)."""

from datetime import datetime

from src.domain.models import (
    Approval,
    PaperRunState,
    PaperRunStatus,
    RuntimeConfig,
    UserConfirmations,
)
from src.pipeline.runtime_controller import initialize_paper_run


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
