"""Tests for ComparisonEngine module (Round 3)."""

from src.domain.models import (
    ExecutionStatus,
    MetricResult,
    ReturnTimeseries,
    TestResult,
    TestResultOutcome,
)
from src.execution.comparison_engine import compare_candidates


def _make_test_result(
    candidate_id: str,
    sharpe: float = 0.5,
    ann_return: float = 8.0,
    max_dd: float = -15.0,
    excess: float = 2.0,
) -> TestResult:
    return TestResult(
        test_result_id=f"{candidate_id}_bt_result",
        test_id=f"bt_{candidate_id}",
        candidate_id=candidate_id,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=[
            MetricResult(
                metric_name="sharpe_ratio",
                actual_value=sharpe,
                pass_threshold=">0.3",
                fail_threshold="<0",
                result=TestResultOutcome.PASS if sharpe > 0.3 else TestResultOutcome.FAIL,
            ),
            MetricResult(
                metric_name="annualized_return",
                actual_value=ann_return,
                pass_threshold=">0%",
                fail_threshold="<-10%",
                result=TestResultOutcome.PASS if ann_return > 0 else TestResultOutcome.FAIL,
            ),
            MetricResult(
                metric_name="max_drawdown",
                actual_value=max_dd,
                pass_threshold=">-20%",
                fail_threshold="<-40%",
                result=TestResultOutcome.PASS if max_dd > -20 else TestResultOutcome.FAIL,
            ),
            MetricResult(
                metric_name="excess_return_vs_benchmark",
                actual_value=excess,
                pass_threshold=">0%",
                fail_threshold="<-5%",
                result=TestResultOutcome.PASS if excess > 0 else TestResultOutcome.FAIL,
            ),
        ],
        overall_result=TestResultOutcome.PASS,
        pit_compliance="partial",
    )


class TestCompareCandidates:
    def test_produces_comparison_result(self):
        results = {
            "C01": _make_test_result("C01", sharpe=0.6),
            "C02": _make_test_result("C02", sharpe=0.4),
        }
        comp = compare_candidates("run_test", results, "C01")
        assert comp.run_id == "run_test"
        assert len(comp.comparison_matrix.candidates) == 2

    def test_ranks_by_sharpe(self):
        results = {
            "C01": _make_test_result("C01", sharpe=0.6),
            "C02": _make_test_result("C02", sharpe=0.8),
        }
        comp = compare_candidates("run_test", results, "C01")
        sharpe_metric = next(
            m for m in comp.comparison_matrix.metrics
            if m.metric_name == "sharpe_ratio"
        )
        assert sharpe_metric.values["C02"].rank == 1
        assert sharpe_metric.values["C01"].rank == 2

    def test_detects_rejection(self):
        results = {
            "C01": _make_test_result("C01", sharpe=0.5, ann_return=5.0),
            "C02": _make_test_result("C02", sharpe=-0.2, ann_return=-12.0),
        }
        comp = compare_candidates("run_test", results, "C01")
        rejected_ids = {r.candidate_id for r in comp.execution_based_rejections}
        assert "C02" in rejected_ids

    def test_ranking_picks_best(self):
        results = {
            "C01": _make_test_result("C01", sharpe=0.8, ann_return=10.0),
            "C02": _make_test_result("C02", sharpe=0.5, ann_return=5.0),
            "C03": _make_test_result("C03", sharpe=0.3, ann_return=3.0),
        }
        comp = compare_candidates("run_test", results, "C01")
        assert comp.execution_based_ranking.recommended_best == "C01"

    def test_no_candidates_still_works(self):
        comp = compare_candidates("run_test", {})
        assert len(comp.comparison_matrix.candidates) == 0

    def test_all_rejected_ranking_is_none(self):
        results = {
            "C01": _make_test_result("C01", ann_return=-15.0, max_dd=-45.0),
            "C02": _make_test_result("C02", ann_return=-20.0, max_dd=-50.0),
        }
        comp = compare_candidates("run_test", results, "C01")
        assert comp.execution_based_ranking.recommended_best is None

    def test_vs_baseline_computed(self):
        results = {
            "C01": _make_test_result("C01", sharpe=0.5),
            "C02": _make_test_result("C02", sharpe=0.8),
        }
        comp = compare_candidates("run_test", results, "C01")
        sharpe_metric = next(
            m for m in comp.comparison_matrix.metrics
            if m.metric_name == "sharpe_ratio"
        )
        assert sharpe_metric.values["C01"].vs_baseline == 0.0
        assert sharpe_metric.values["C02"].vs_baseline == 0.3
