"""Tests for BacktestEngine module (Round 3)."""

import numpy as np
import pandas as pd

from src.domain.models import (
    Candidate,
    CandidateAssumption,
    CandidateType,
    ExecutionStatus,
    ImplementationComplexity,
    TestResultOutcome,
    ValidationBurden,
)
from src.execution.backtest_engine import run_backtest
from src.execution.data_acquisition import _generate_synthetic_ohlcv


def _make_candidate(ctype: CandidateType = CandidateType.BASELINE) -> Candidate:
    return Candidate(
        candidate_id="C01",
        name="テスト候補",
        candidate_type=ctype,
        summary="テスト用",
        core_assumptions=[
            CandidateAssumption(
                assumption_id="A01", statement="テスト前提", failure_impact="テスト影響"
            )
        ],
        validation_burden=ValidationBurden.MEDIUM,
        implementation_complexity=ImplementationComplexity.MEDIUM,
        known_risks=["リスク1"],
    )


def _make_price_data(n_tickers: int = 5) -> dict[str, pd.DataFrame]:
    return {
        f"T{i}": _generate_synthetic_ohlcv(f"T{i}", "2019-01-01", "2024-01-01")
        for i in range(n_tickers)
    }


class TestRunBacktest:
    def test_returns_test_result(self):
        result = run_backtest(_make_candidate(), _make_price_data())
        assert result.candidate_id == "C01"
        assert result.execution_status == ExecutionStatus.COMPLETED

    def test_produces_metrics(self):
        result = run_backtest(_make_candidate(), _make_price_data())
        metric_names = {m.metric_name for m in result.metrics_results}
        assert "annualized_return" in metric_names
        assert "sharpe_ratio" in metric_names
        assert "max_drawdown" in metric_names
        assert "annualized_volatility" in metric_names

    def test_return_timeseries_populated(self):
        result = run_backtest(_make_candidate(), _make_price_data())
        ts = result.return_timeseries
        assert ts is not None
        assert len(ts.dates) > 0
        assert len(ts.net_returns) == len(ts.dates)
        assert len(ts.gross_returns) == len(ts.dates)
        assert len(ts.benchmark_returns) == len(ts.dates)

    def test_empty_data_fails_gracefully(self):
        result = run_backtest(_make_candidate(), {})
        assert result.execution_status == ExecutionStatus.FAILED
        assert result.overall_result == TestResultOutcome.INCONCLUSIVE

    def test_insufficient_data_fails(self):
        # Only 100 days — below 252 minimum
        short_data = {
            "T0": _generate_synthetic_ohlcv("T0", "2024-01-01", "2024-06-01")
        }
        result = run_backtest(_make_candidate(), short_data)
        assert result.execution_status == ExecutionStatus.FAILED

    def test_different_candidate_types_work(self):
        price_data = _make_price_data()
        for ctype in [CandidateType.BASELINE, CandidateType.CONSERVATIVE, CandidateType.EXPLORATORY]:
            result = run_backtest(_make_candidate(ctype), price_data)
            assert result.execution_status == ExecutionStatus.COMPLETED

    def test_metrics_have_thresholds(self):
        result = run_backtest(_make_candidate(), _make_price_data())
        for m in result.metrics_results:
            assert m.pass_threshold
            assert m.fail_threshold
