"""
Comparison engine for v1 execution layer.

Compares all candidates on the same metrics after backtest.
Produces ComparisonResult with ranking and rejection signals.
"""

from __future__ import annotations

import uuid

import numpy as np

from src.domain.models import (
    CandidateMetricValue,
    ComparisonMatrixData,
    ComparisonMetric,
    ComparisonResult,
    ExecutionBasedRanking,
    ExecutionBasedRejection,
    RankingRationale,
    TestResult,
    TestResultOutcome,
)

# Metrics that trigger rejection when failed
DISQUALIFYING_METRICS = {"annualized_return", "max_drawdown"}


def compare_candidates(
    run_id: str,
    test_results: dict[str, TestResult],
    baseline_candidate_id: str | None = None,
) -> ComparisonResult:
    """
    Compare backtest results across candidates.

    Args:
        run_id: Run identifier
        test_results: Mapping of candidate_id -> TestResult (backtest)
        baseline_candidate_id: Which candidate is the baseline reference
    """
    candidate_ids = list(test_results.keys())

    if not baseline_candidate_id and candidate_ids:
        baseline_candidate_id = candidate_ids[0]

    # Extract metrics per candidate
    metric_names = _collect_metric_names(test_results)
    comparison_metrics = []

    for mname in metric_names:
        values: dict[str, CandidateMetricValue] = {}
        raw_values = []

        for cid in candidate_ids:
            tr = test_results[cid]
            val = _get_metric_value(tr, mname)
            raw_values.append((cid, val))

        # Rank candidates (higher = better, except volatility/drawdown)
        is_lower_better = mname in {"annualized_volatility", "max_drawdown"}
        sorted_vals = sorted(raw_values, key=lambda x: x[1],
                             reverse=not is_lower_better)

        baseline_val = next(
            (v for cid, v in raw_values if cid == baseline_candidate_id), 0.0,
        )

        for rank_idx, (cid, val) in enumerate(sorted_vals):
            values[cid] = CandidateMetricValue(
                value=round(val, 4),
                vs_baseline=round(val - baseline_val, 4),
                is_significant=False,  # simplified for v1
                p_value=1.0,
                rank=rank_idx + 1,
            )

        comparison_metrics.append(ComparisonMetric(
            metric_name=mname,
            values=values,
        ))

    # Detect rejections
    rejections = _detect_rejections(test_results)

    # Generate ranking
    ranking = _generate_ranking(test_results, candidate_ids, rejections)

    return ComparisonResult(
        comparison_id=f"comp_{uuid.uuid4().hex[:6]}",
        run_id=run_id,
        comparison_matrix=ComparisonMatrixData(
            candidates=candidate_ids,
            baseline_candidate_id=baseline_candidate_id or "",
            metrics=comparison_metrics,
        ),
        execution_based_rejections=rejections,
        execution_based_ranking=ranking,
    )


def _collect_metric_names(test_results: dict[str, TestResult]) -> list[str]:
    """Collect unique metric names across all test results."""
    names: list[str] = []
    seen: set[str] = set()
    for tr in test_results.values():
        for m in tr.metrics_results:
            if m.metric_name not in seen:
                seen.add(m.metric_name)
                names.append(m.metric_name)
    return names


def _get_metric_value(tr: TestResult, metric_name: str) -> float:
    """Extract a specific metric value from a TestResult."""
    for m in tr.metrics_results:
        if m.metric_name == metric_name:
            return m.actual_value
    return 0.0


def _detect_rejections(
    test_results: dict[str, TestResult],
) -> list[ExecutionBasedRejection]:
    """Detect candidates that should be rejected based on disqualifying metrics."""
    rejections = []
    for cid, tr in test_results.items():
        failed_disqualifying = []
        for m in tr.metrics_results:
            if m.metric_name in DISQUALIFYING_METRICS and m.result == TestResultOutcome.FAIL:
                failed_disqualifying.append(tr.test_id)

        if failed_disqualifying:
            rejections.append(ExecutionBasedRejection(
                candidate_id=cid,
                reason=f"不合格メトリクス: {', '.join(DISQUALIFYING_METRICS & {m.metric_name for m in tr.metrics_results if m.result == TestResultOutcome.FAIL})}",
                disqualifying_test_results=failed_disqualifying,
            ))

    return rejections


def _generate_ranking(
    test_results: dict[str, TestResult],
    candidate_ids: list[str],
    rejections: list[ExecutionBasedRejection],
) -> ExecutionBasedRanking:
    """Generate ranking based on composite score."""
    rejected_ids = {r.candidate_id for r in rejections}
    surviving = [cid for cid in candidate_ids if cid not in rejected_ids]

    if not surviving:
        return ExecutionBasedRanking(
            ranking_rationale=[RankingRationale(
                comparison_axis="overall",
                winner="none",
                margin="全候補が不合格基準に抵触",
            )],
        )

    # Score by: Sharpe (40%) + excess return (30%) + max drawdown (30%)
    scores: dict[str, float] = {}
    for cid in surviving:
        tr = test_results[cid]
        sharpe = _get_metric_value(tr, "sharpe_ratio")
        excess = _get_metric_value(tr, "excess_return_vs_benchmark")
        dd = _get_metric_value(tr, "max_drawdown")

        # Normalize drawdown: less negative is better, convert to positive scale
        dd_score = (100 + dd) / 100  # -20% → 0.8
        scores[cid] = sharpe * 0.4 + excess * 0.3 + dd_score * 0.3 * 100

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    best = ranked[0][0] if ranked else None
    runner_up = ranked[1][0] if len(ranked) > 1 else None

    rationale = []
    if best and runner_up:
        for axis in ["sharpe_ratio", "excess_return_vs_benchmark", "max_drawdown"]:
            best_val = _get_metric_value(test_results[best], axis)
            runner_val = _get_metric_value(test_results[runner_up], axis)
            winner = best if best_val >= runner_val else runner_up
            if axis == "max_drawdown":
                winner = best if best_val >= runner_val else runner_up  # less negative is better
            rationale.append(RankingRationale(
                comparison_axis=axis,
                winner=winner,
                margin=f"{abs(best_val - runner_val):.2f}",
            ))
    elif best:
        rationale.append(RankingRationale(
            comparison_axis="overall",
            winner=best,
            margin="唯一の生存候補",
        ))

    return ExecutionBasedRanking(
        recommended_best=best,
        recommended_runner_up=runner_up,
        ranking_rationale=rationale,
    )
