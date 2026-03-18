"""
Paper Run engine for v1 execution layer.

v1 scope:
- Daily mark-to-market update
- Stop condition evaluation (4 conditions)
- Day count progression
- No real execution, no broker integration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.domain.models import (
    HaltEvent,
    NearestCondition,
    PaperRunState,
    PaperRunStatus,
    SafetyStatus,
)

# Stop condition thresholds (v1 fixed)
SC01_MAX_DRAWDOWN = -0.20
SC02_UNDERPERF_MONTHS = 3
SC03_SIGNAL_SIGMA = 3.0
SC04_DATA_FAIL_DAYS = 3


def update_paper_run(
    state: PaperRunState,
    latest_prices: dict[str, float] | None = None,
    benchmark_return: float = 0.0,
    data_quality_ok: bool = True,
) -> PaperRunState:
    """
    Advance Paper Run state by one day.

    Args:
        state: Current PaperRunState
        latest_prices: Dict of ticker -> latest close price (optional)
        benchmark_return: Daily benchmark return for underperformance check
        data_quality_ok: Whether today's data quality check passed
    """
    if state.status in (PaperRunStatus.HALTED, PaperRunStatus.RE_EVALUATING):
        return state

    snap = state.current_snapshot
    day_count = snap.day_count + 1

    # Simulate daily portfolio return
    daily_return = _simulate_daily_return(latest_prices, day_count)

    # Update capital
    new_capital = snap.virtual_capital_current * (1 + daily_return)
    total_return = (new_capital / snap.virtual_capital_initial - 1) * 100

    # Update drawdown
    peak_capital = max(snap.virtual_capital_initial, snap.virtual_capital_current)
    if new_capital > peak_capital:
        peak_capital = new_capital
    current_dd = (new_capital - peak_capital) / peak_capital if peak_capital > 0 else 0.0

    # Update snapshot
    snap.day_count = day_count
    snap.virtual_capital_current = round(new_capital, 2)
    snap.total_return_pct = round(total_return, 4)
    snap.current_drawdown_pct = round(current_dd * 100, 4)

    # Evaluate stop conditions
    breach = evaluate_stop_conditions(
        current_drawdown_pct=current_dd,
        daily_return=daily_return,
        benchmark_return=benchmark_return,
        day_count=day_count,
        data_quality_ok=data_quality_ok,
    )

    if breach:
        state.safety_status = SafetyStatus(
            any_breached=True,
            nearest_condition=NearestCondition(
                id=breach["condition_id"],
                current_value=breach["current_value"],
                threshold=breach["threshold"],
                distance_pct=0.0,
            ),
        )

        if breach["action"] == "halt_and_notify":
            state.status = PaperRunStatus.HALTED
            state.halt_history.append(HaltEvent(
                halted_at=datetime.utcnow().isoformat(),
                condition_id=breach["condition_id"],
            ))
        elif breach["action"] == "pause_and_notify":
            state.status = PaperRunStatus.PAUSED
            state.halt_history.append(HaltEvent(
                halted_at=datetime.utcnow().isoformat(),
                condition_id=breach["condition_id"],
            ))
    else:
        # Update nearest condition (closest to threshold)
        nearest = _find_nearest_condition(current_dd, day_count)
        state.safety_status = SafetyStatus(
            any_breached=False,
            nearest_condition=nearest,
        )

    return state


def evaluate_stop_conditions(
    current_drawdown_pct: float,
    daily_return: float = 0.0,
    benchmark_return: float = 0.0,
    day_count: int = 0,
    data_quality_ok: bool = True,
    consecutive_underperf_months: int = 0,
    consecutive_data_fail_days: int = 0,
) -> dict | None:
    """
    Evaluate all 4 stop conditions.

    Returns breach info dict if any condition triggered, None otherwise.
    """
    # SC-01: Max drawdown
    if current_drawdown_pct <= SC01_MAX_DRAWDOWN:
        return {
            "condition_id": "SC-01",
            "type": "max_drawdown",
            "current_value": current_drawdown_pct,
            "threshold": SC01_MAX_DRAWDOWN,
            "action": "halt_and_notify",
        }

    # SC-02: Consecutive underperformance (simplified — use month approximation)
    if consecutive_underperf_months >= SC02_UNDERPERF_MONTHS:
        return {
            "condition_id": "SC-02",
            "type": "consecutive_underperformance",
            "current_value": float(consecutive_underperf_months),
            "threshold": float(SC02_UNDERPERF_MONTHS),
            "action": "halt_and_notify",
        }

    # SC-03: Signal anomaly (simplified — large daily return as proxy)
    if abs(daily_return) > 0.05:  # 5% daily move as simplified anomaly
        return {
            "condition_id": "SC-03",
            "type": "signal_anomaly",
            "current_value": abs(daily_return),
            "threshold": 0.05,
            "action": "pause_and_notify",
        }

    # SC-04: Data quality failure
    if consecutive_data_fail_days >= SC04_DATA_FAIL_DAYS:
        return {
            "condition_id": "SC-04",
            "type": "data_quality_failure",
            "current_value": float(consecutive_data_fail_days),
            "threshold": float(SC04_DATA_FAIL_DAYS),
            "action": "pause_and_notify",
        }

    return None


def _simulate_daily_return(
    latest_prices: dict[str, float] | None,
    day_count: int,
) -> float:
    """
    Compute daily portfolio return.

    If no latest_prices provided, simulate a small random return
    (Paper Run without live data feed).
    """
    if latest_prices and len(latest_prices) > 0:
        # Simple: average price change (would need previous prices for real calc)
        # For v1, this is a placeholder — real implementation needs price history
        return 0.0

    # Synthetic daily return for Paper Run demonstration
    rng = np.random.default_rng(day_count)
    return float(rng.normal(0.0003, 0.01))  # ~7% annual, ~16% vol


def _find_nearest_condition(
    current_drawdown_pct: float,
    day_count: int,
) -> NearestCondition:
    """Find the stop condition closest to being triggered."""
    dd_distance = abs(current_drawdown_pct - SC01_MAX_DRAWDOWN) / abs(SC01_MAX_DRAWDOWN)

    return NearestCondition(
        id="SC-01",
        current_value=round(current_drawdown_pct, 4),
        threshold=SC01_MAX_DRAWDOWN,
        distance_pct=round(dd_distance * 100, 2),
    )
