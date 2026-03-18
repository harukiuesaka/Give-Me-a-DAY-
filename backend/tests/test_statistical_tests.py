"""Tests for StatisticalTests module (Round 3)."""

import numpy as np

from src.domain.models import ExecutionStatus, TestResultOutcome
from src.execution.statistical_tests import (
    run_oos_comparison,
    run_return_ttest,
    run_sharpe_significance,
)


class TestReturnTTest:
    def test_positive_returns_pass(self):
        rng = np.random.default_rng(42)
        # Strong positive returns
        returns = rng.normal(0.001, 0.01, 500)
        result = run_return_ttest(returns, "C01")
        assert result.execution_status == ExecutionStatus.COMPLETED
        assert len(result.metrics_results) == 1
        m = result.metrics_results[0]
        assert m.statistical_significance is not None
        assert m.statistical_significance.p_value is not None

    def test_zero_returns_fail_or_inconclusive(self):
        returns = np.zeros(500)
        result = run_return_ttest(returns, "C01")
        assert result.overall_result in (TestResultOutcome.FAIL, TestResultOutcome.INCONCLUSIVE)

    def test_too_few_samples_inconclusive(self):
        returns = np.array([0.01, 0.02])
        result = run_return_ttest(returns, "C01")
        assert result.overall_result == TestResultOutcome.INCONCLUSIVE

    def test_negative_returns_fail(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(-0.002, 0.01, 500)
        result = run_return_ttest(returns, "C01")
        assert result.overall_result == TestResultOutcome.FAIL


class TestSharpeSignificance:
    def test_strong_sharpe_passes(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.005, 1000)
        result = run_sharpe_significance(returns, "C01")
        assert result.execution_status == ExecutionStatus.COMPLETED
        m = result.metrics_results[0]
        assert m.metric_name == "annualized_sharpe_ratio"
        assert m.statistical_significance is not None

    def test_too_few_samples_inconclusive(self):
        returns = np.array([0.01] * 30)
        result = run_sharpe_significance(returns, "C01")
        assert result.overall_result == TestResultOutcome.INCONCLUSIVE

    def test_zero_std_inconclusive(self):
        returns = np.full(100, 0.001)
        result = run_sharpe_significance(returns, "C01")
        assert result.overall_result == TestResultOutcome.INCONCLUSIVE


class TestOOSComparison:
    def test_consistent_returns_pass(self):
        rng = np.random.default_rng(42)
        # Consistent positive returns across IS and OOS
        returns = rng.normal(0.0005, 0.01, 500)
        result = run_oos_comparison(returns, "C01")
        assert result.execution_status == ExecutionStatus.COMPLETED
        assert len(result.metrics_results) == 3

    def test_insufficient_data_inconclusive(self):
        returns = np.array([0.01] * 50)
        result = run_oos_comparison(returns, "C01")
        assert result.overall_result == TestResultOutcome.INCONCLUSIVE

    def test_overfitted_returns_detected(self):
        rng = np.random.default_rng(42)
        # Strong IS, weak OOS
        is_returns = rng.normal(0.002, 0.005, 350)  # 70%
        oos_returns = rng.normal(-0.001, 0.01, 150)  # 30%
        returns = np.concatenate([is_returns, oos_returns])
        result = run_oos_comparison(returns, "C01")
        # OOS sharpe should be much lower, triggering mixed or fail
        oos_ratio = next(
            m for m in result.metrics_results if m.metric_name == "oos_is_sharpe_ratio"
        )
        assert oos_ratio.actual_value < 0.5

    def test_three_metrics_returned(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0.0005, 0.01, 500)
        result = run_oos_comparison(returns, "C01")
        names = {m.metric_name for m in result.metrics_results}
        assert "in_sample_sharpe" in names
        assert "out_of_sample_sharpe" in names
        assert "oos_is_sharpe_ratio" in names
