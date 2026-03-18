"""
Backtest engine for v1 execution layer.

v1 scope:
- Daily-bar simulation only
- Monthly rebalance (fixed)
- Cost model: 10bps commission + 10bps spread (fixed)
- T+1 open execution timing
- Max 20 years, max 500 instruments
- Simple momentum/factor signal generation per archetype
"""

from __future__ import annotations

import uuid
from datetime import datetime

import numpy as np
import pandas as pd

from src.domain.models import (
    Candidate,
    ExecutionStatus,
    MetricResult,
    ReturnTimeseries,
    StatisticalSignificance,
    TestResult,
    TestResultOutcome,
)

# Fixed v1 cost model
COMMISSION_BPS = 10
SPREAD_BPS = 10
TOTAL_COST_BPS = COMMISSION_BPS + SPREAD_BPS  # 20bps round-trip


def run_backtest(
    candidate: Candidate,
    price_data: dict[str, pd.DataFrame],
    test_id: str = "",
) -> TestResult:
    """
    Run a simple daily-bar backtest for a candidate.

    Uses momentum signal (12-month return rank) for portfolio construction.
    Monthly rebalance, equal-weight, fixed cost model.
    """
    if not test_id:
        test_id = f"bt_{uuid.uuid4().hex[:6]}"

    tickers = list(price_data.keys())
    if len(tickers) == 0:
        return _failed_result(test_id, candidate.candidate_id, "データなし")

    # Build aligned close price matrix
    closes = _build_close_matrix(price_data)
    if closes is None or len(closes) < 252:
        return _failed_result(test_id, candidate.candidate_id, "データ不足（最低252日必要）")

    # Generate signals and run simulation
    try:
        gross_returns, net_returns, benchmark_returns = _simulate(
            closes, candidate.candidate_type.value,
        )
    except Exception as e:
        return _failed_result(test_id, candidate.candidate_id, str(e))

    # Compute metrics
    metrics = _compute_metrics(net_returns, benchmark_returns)

    # Determine overall result
    sharpe = _annualized_sharpe(net_returns)
    overall = TestResultOutcome.PASS if sharpe > 0 else TestResultOutcome.FAIL
    if any(m.result == TestResultOutcome.FAIL for m in metrics):
        overall = TestResultOutcome.FAIL
    elif any(m.result == TestResultOutcome.INCONCLUSIVE for m in metrics):
        overall = TestResultOutcome.MIXED

    dates = closes.index.strftime("%Y-%m-%d").tolist()

    return TestResult(
        test_result_id=f"{test_id}_result",
        test_id=test_id,
        candidate_id=candidate.candidate_id,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=metrics,
        overall_result=overall,
        return_timeseries=ReturnTimeseries(
            dates=dates[-len(net_returns):],
            gross_returns=gross_returns.tolist(),
            net_returns=net_returns.tolist(),
            benchmark_returns=benchmark_returns.tolist(),
        ),
        data_quality_flags=[],
        pit_compliance="partial",
    )


def _build_close_matrix(price_data: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    """Build aligned close price matrix from per-ticker DataFrames."""
    frames = {}
    for ticker, df in price_data.items():
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
        if col in df.columns:
            frames[ticker] = df[col]

    if not frames:
        return None

    closes = pd.DataFrame(frames)
    closes = closes.dropna(how="all")
    closes = closes.ffill().bfill()
    return closes


def _simulate(
    closes: pd.DataFrame,
    candidate_type: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Run momentum-based simulation.

    Returns (gross_returns, net_returns, benchmark_returns) as daily arrays.
    """
    n_days = len(closes)
    tickers = closes.columns.tolist()
    n_tickers = len(tickers)

    # Daily returns
    daily_rets = closes.pct_change().fillna(0.0)

    # Benchmark: equal-weight buy-and-hold
    benchmark_returns = daily_rets.mean(axis=1).values

    # Monthly rebalance dates (~21 trading days)
    rebalance_days = list(range(0, n_days, 21))

    # Momentum lookback (by candidate type)
    lookback = {"baseline": 252, "conservative": 126, "exploratory": 63}.get(
        candidate_type, 252,
    )

    # Strategy portfolio weights (updated monthly)
    weights = np.ones(n_tickers) / max(n_tickers, 1)
    gross = np.zeros(n_days)
    net = np.zeros(n_days)

    prev_weights = weights.copy()

    for i in range(1, n_days):
        # Portfolio return for the day
        day_rets = daily_rets.iloc[i].values
        port_ret = np.nansum(weights * day_rets)
        gross[i] = port_ret

        # Rebalance check
        if i in rebalance_days and i >= lookback:
            # Momentum signal: past-N return rank
            past_returns = (closes.iloc[i] / closes.iloc[max(0, i - lookback)] - 1).values
            valid = ~np.isnan(past_returns)

            if valid.sum() > 0:
                # Top half gets equal weight (simple momentum)
                ranked = np.argsort(-past_returns)
                n_select = max(1, valid.sum() // 2)
                new_weights = np.zeros(n_tickers)
                for j in range(n_select):
                    if valid[ranked[j]]:
                        new_weights[ranked[j]] = 1.0 / n_select
                weights = new_weights

            # Cost: turnover * cost_bps
            turnover = np.sum(np.abs(weights - prev_weights))
            cost = turnover * TOTAL_COST_BPS / 10_000
            net[i] = port_ret - cost
            prev_weights = weights.copy()
        else:
            net[i] = port_ret

    return gross, net, benchmark_returns


def _compute_metrics(
    net_returns: np.ndarray,
    benchmark_returns: np.ndarray,
) -> list[MetricResult]:
    """Compute standard performance metrics."""
    metrics = []
    n = len(net_returns)
    if n < 2:
        return metrics

    # Annualized return
    cumret = np.prod(1 + net_returns) - 1
    ann_ret = (1 + cumret) ** (252 / n) - 1 if n > 0 else 0.0
    metrics.append(MetricResult(
        metric_name="annualized_return",
        actual_value=round(ann_ret * 100, 2),
        pass_threshold=">0%",
        fail_threshold="<-10%",
        result=TestResultOutcome.PASS if ann_ret > 0 else TestResultOutcome.FAIL,
    ))

    # Annualized volatility
    ann_vol = np.std(net_returns, ddof=1) * np.sqrt(252)
    metrics.append(MetricResult(
        metric_name="annualized_volatility",
        actual_value=round(ann_vol * 100, 2),
        pass_threshold="<30%",
        fail_threshold=">50%",
        result=TestResultOutcome.PASS if ann_vol < 0.30 else TestResultOutcome.FAIL,
    ))

    # Sharpe ratio
    sharpe = _annualized_sharpe(net_returns)
    metrics.append(MetricResult(
        metric_name="sharpe_ratio",
        actual_value=round(sharpe, 3),
        pass_threshold=">0.3",
        fail_threshold="<0",
        result=(
            TestResultOutcome.PASS if sharpe > 0.3
            else TestResultOutcome.FAIL if sharpe < 0
            else TestResultOutcome.INCONCLUSIVE
        ),
    ))

    # Max drawdown
    cum = np.cumprod(1 + net_returns)
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    max_dd = float(np.min(dd))
    metrics.append(MetricResult(
        metric_name="max_drawdown",
        actual_value=round(max_dd * 100, 2),
        pass_threshold=">-20%",
        fail_threshold="<-40%",
        result=TestResultOutcome.PASS if max_dd > -0.20 else TestResultOutcome.FAIL,
    ))

    # Excess return vs benchmark
    bench_cumret = np.prod(1 + benchmark_returns) - 1
    bench_ann = (1 + bench_cumret) ** (252 / n) - 1 if n > 0 else 0.0
    excess = ann_ret - bench_ann
    metrics.append(MetricResult(
        metric_name="excess_return_vs_benchmark",
        actual_value=round(excess * 100, 2),
        pass_threshold=">0%",
        fail_threshold="<-5%",
        result=TestResultOutcome.PASS if excess > 0 else TestResultOutcome.FAIL,
    ))

    return metrics


def _annualized_sharpe(returns: np.ndarray) -> float:
    """Compute annualized Sharpe ratio (assuming risk-free = 0)."""
    if len(returns) < 2 or np.std(returns, ddof=1) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252))


def _failed_result(test_id: str, candidate_id: str, reason: str) -> TestResult:
    """Create a failed TestResult."""
    return TestResult(
        test_result_id=f"{test_id}_result",
        test_id=test_id,
        candidate_id=candidate_id,
        execution_status=ExecutionStatus.FAILED,
        metrics_results=[],
        overall_result=TestResultOutcome.INCONCLUSIVE,
        data_quality_flags=[reason],
        pit_compliance="none",
    )
