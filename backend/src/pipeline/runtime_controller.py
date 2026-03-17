"""
Runtime Controller — Paper Run state management (contract only).

This module defines the runtime contract for v1 Paper Run.
It does NOT implement actual execution, daily cycles, or data fetching.
Those belong to Round 3+ (Execution Layer).

State transitions:
  planning_complete → recommendation_available → approval_granted → paper_run_initialized

This module handles the last transition: approval → paper_run_initialized.
"""

import logging
import uuid
from datetime import datetime, timedelta

from src.domain.models import (
    Approval,
    CurrentSnapshot,
    PaperRunSchedule,
    PaperRunState,
    PaperRunStatus,
    SafetyStatus,
)

logger = logging.getLogger(__name__)


class RuntimeNotInitializedError(Exception):
    """Raised when runtime status is requested but Paper Run is not initialized."""
    pass


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
