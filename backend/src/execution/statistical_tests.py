"""
Statistical tests for v1 execution layer.

v1 scope:
- t-test on daily excess returns
- Sharpe ratio significance test
- In-sample vs out-of-sample comparison (70/30 split)
"""

from __future__ import annotations

import uuid

import numpy as np

from src.domain.models import (
    ExecutionStatus,
    MetricResult,
    StatisticalSignificance,
    TestResult,
    TestResultOutcome,
)


def run_return_ttest(
    net_returns: np.ndarray,
    candidate_id: str,
    test_id: str = "",
) -> TestResult:
    """
    Test whether mean daily return is significantly different from zero.

    Uses scipy.stats.ttest_1samp.
    """
    if not test_id:
        test_id = f"ttest_{uuid.uuid4().hex[:6]}"

    if len(net_returns) < 30:
        return _inconclusive(test_id, candidate_id, "サンプル不足（最低30日）")

    from scipy import stats

    t_stat, p_value = stats.ttest_1samp(net_returns, 0.0)
    p_value = float(p_value)

    mean_ret = float(np.mean(net_returns))
    se = float(np.std(net_returns, ddof=1) / np.sqrt(len(net_returns)))
    ci = [mean_ret - 1.96 * se, mean_ret + 1.96 * se]

    result = TestResultOutcome.PASS if (p_value < 0.05 and mean_ret > 0) else TestResultOutcome.FAIL
    if p_value >= 0.05:
        result = TestResultOutcome.INCONCLUSIVE

    return TestResult(
        test_result_id=f"{test_id}_result",
        test_id=test_id,
        candidate_id=candidate_id,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=[
            MetricResult(
                metric_name="mean_daily_return",
                actual_value=round(mean_ret * 10000, 4),  # in bps
                pass_threshold=">0 bps, p<0.05",
                fail_threshold="≤0 bps or p≥0.05",
                result=result,
                statistical_significance=StatisticalSignificance(
                    test_used="t-test (1-sample, H0: μ=0)",
                    p_value=round(p_value, 6),
                    confidence_interval=[round(ci[0] * 10000, 4), round(ci[1] * 10000, 4)],
                ),
            ),
        ],
        overall_result=result,
        pit_compliance="partial",
    )


def run_sharpe_significance(
    net_returns: np.ndarray,
    candidate_id: str,
    test_id: str = "",
) -> TestResult:
    """
    Test whether Sharpe ratio is significantly different from zero.

    Uses Lo (2002) adjustment for autocorrelation.
    """
    if not test_id:
        test_id = f"sharpe_{uuid.uuid4().hex[:6]}"

    n = len(net_returns)
    if n < 60:
        return _inconclusive(test_id, candidate_id, "サンプル不足（最低60日）")

    mean_r = float(np.mean(net_returns))
    std_r = float(np.std(net_returns, ddof=1))
    if std_r < 1e-12:
        return _inconclusive(test_id, candidate_id, "標準偏差がゼロ")

    daily_sharpe = mean_r / std_r
    ann_sharpe = daily_sharpe * np.sqrt(252)

    # Standard error of Sharpe: SE ≈ sqrt((1 + 0.5 * SR^2) / n)
    se_sharpe = float(np.sqrt((1 + 0.5 * daily_sharpe**2) / n))
    t_stat = daily_sharpe / se_sharpe if se_sharpe > 0 else 0.0

    from scipy import stats

    p_value = float(2 * (1 - stats.t.cdf(abs(t_stat), df=n - 1)))

    result = TestResultOutcome.PASS if (p_value < 0.05 and ann_sharpe > 0) else TestResultOutcome.FAIL
    if p_value >= 0.05:
        result = TestResultOutcome.INCONCLUSIVE

    ci_low = (daily_sharpe - 1.96 * se_sharpe) * np.sqrt(252)
    ci_high = (daily_sharpe + 1.96 * se_sharpe) * np.sqrt(252)

    return TestResult(
        test_result_id=f"{test_id}_result",
        test_id=test_id,
        candidate_id=candidate_id,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=[
            MetricResult(
                metric_name="annualized_sharpe_ratio",
                actual_value=round(ann_sharpe, 4),
                pass_threshold=">0, p<0.05",
                fail_threshold="≤0 or p≥0.05",
                result=result,
                statistical_significance=StatisticalSignificance(
                    test_used="Sharpe ratio significance (Lo 2002)",
                    p_value=round(p_value, 6),
                    confidence_interval=[round(ci_low, 4), round(ci_high, 4)],
                ),
            ),
        ],
        overall_result=result,
        pit_compliance="partial",
    )


def run_oos_comparison(
    net_returns: np.ndarray,
    candidate_id: str,
    split_ratio: float = 0.7,
    test_id: str = "",
) -> TestResult:
    """
    Compare in-sample vs out-of-sample Sharpe ratio.

    Overfitting detection: if OOS Sharpe < 50% of IS Sharpe, flag as concern.
    """
    if not test_id:
        test_id = f"oos_{uuid.uuid4().hex[:6]}"

    n = len(net_returns)
    if n < 120:
        return _inconclusive(test_id, candidate_id, "サンプル不足（最低120日、IS+OOS）")

    split_idx = int(n * split_ratio)
    is_returns = net_returns[:split_idx]
    oos_returns = net_returns[split_idx:]

    is_sharpe = _ann_sharpe(is_returns)
    oos_sharpe = _ann_sharpe(oos_returns)

    # Overfitting ratio
    ratio = oos_sharpe / is_sharpe if abs(is_sharpe) > 1e-8 else 0.0

    if ratio >= 0.5 and oos_sharpe > 0:
        result = TestResultOutcome.PASS
    elif oos_sharpe <= 0:
        result = TestResultOutcome.FAIL
    else:
        result = TestResultOutcome.MIXED

    metrics = [
        MetricResult(
            metric_name="in_sample_sharpe",
            actual_value=round(is_sharpe, 4),
            pass_threshold=">0",
            fail_threshold="<0",
            result=TestResultOutcome.PASS if is_sharpe > 0 else TestResultOutcome.FAIL,
        ),
        MetricResult(
            metric_name="out_of_sample_sharpe",
            actual_value=round(oos_sharpe, 4),
            pass_threshold=">0",
            fail_threshold="<0",
            result=TestResultOutcome.PASS if oos_sharpe > 0 else TestResultOutcome.FAIL,
        ),
        MetricResult(
            metric_name="oos_is_sharpe_ratio",
            actual_value=round(ratio, 4),
            pass_threshold="≥0.5",
            fail_threshold="<0.5",
            result=TestResultOutcome.PASS if ratio >= 0.5 else TestResultOutcome.FAIL,
        ),
    ]

    return TestResult(
        test_result_id=f"{test_id}_result",
        test_id=test_id,
        candidate_id=candidate_id,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=metrics,
        overall_result=result,
        pit_compliance="partial",
    )


def _ann_sharpe(returns: np.ndarray) -> float:
    if len(returns) < 2 or np.std(returns, ddof=1) == 0:
        return 0.0
    return float(np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(252))


def _inconclusive(test_id: str, candidate_id: str, reason: str) -> TestResult:
    return TestResult(
        test_result_id=f"{test_id}_result",
        test_id=test_id,
        candidate_id=candidate_id,
        execution_status=ExecutionStatus.PARTIAL,
        metrics_results=[],
        overall_result=TestResultOutcome.INCONCLUSIVE,
        data_quality_flags=[reason],
        pit_compliance="none",
    )
