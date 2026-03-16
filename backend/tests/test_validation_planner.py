"""Tests for ValidationPlanner module (Round 2)."""

from src.domain.models import (
    Candidate,
    CandidateAssumption,
    CandidateType,
    CoverageMetrics,
    EvidencePlan,
    GapSeverity,
    MinimumEvidenceStandard,
    PlanCompleteness,
    ResearchSpec,
    TestType,
    ValidationBurden,
    ValidationPlan,
    ValidationRequirements,
)
from src.pipeline.validation_planner import plan


def _make_spec() -> ResearchSpec:
    return ResearchSpec(
        spec_id="run_test_vp-RS",
        run_id="run_test_vp",
        primary_objective="検証: モメンタム効果",
        problem_frame="モメンタム効果の検証",
        validation_requirements=ValidationRequirements(
            must_test=["モメンタム効果"],
            must_compare=["baseline_candidate"],
            minimum_evidence_standard=MinimumEvidenceStandard.MODERATE,
        ),
    )


def _make_candidate(burden: ValidationBurden = ValidationBurden.MEDIUM) -> Candidate:
    return Candidate(
        candidate_id="run_test_vp_C01",
        name="単純モメンタム戦略",
        candidate_type=CandidateType.BASELINE,
        summary="テスト用候補",
        validation_burden=burden,
        core_assumptions=[
            CandidateAssumption(
                assumption_id="CA01",
                statement="仮定",
                failure_impact="影響",
            )
        ],
        known_risks=["リスク1"],
    )


def _make_evidence(gap_severity: GapSeverity = GapSeverity.NONE) -> EvidencePlan:
    return EvidencePlan(
        evidence_plan_id="run_test_vp-EP-C01",
        candidate_id="run_test_vp_C01",
        gap_severity=gap_severity,
        coverage_metrics=CoverageMetrics(
            required_total=2,
            required_available=2,
            coverage_percentage=100.0,
        ),
    )


class TestValidationPlanner:
    def test_produces_valid_plan(self):
        vp = plan(_make_spec(), _make_candidate(), _make_evidence())
        assert isinstance(vp, ValidationPlan)
        assert vp.candidate_id == "run_test_vp_C01"

    def test_mandatory_tests_present(self):
        vp = plan(_make_spec(), _make_candidate(), _make_evidence())
        test_types = {t.test_type for t in vp.test_sequence}
        assert TestType.OFFLINE_BACKTEST in test_types
        assert TestType.OUT_OF_SAMPLE in test_types
        assert TestType.WALK_FORWARD in test_types
        assert TestType.REGIME_SPLIT in test_types

    def test_every_test_has_failure_conditions(self):
        vp = plan(_make_spec(), _make_candidate(), _make_evidence())
        for test in vp.test_sequence:
            assert len(test.failure_conditions) >= 1, \
                f"Test {test.test_id} has no failure conditions"

    def test_sensitivity_included_for_medium_burden(self):
        vp = plan(_make_spec(), _make_candidate(ValidationBurden.MEDIUM), _make_evidence())
        test_types = {t.test_type for t in vp.test_sequence}
        assert TestType.SENSITIVITY in test_types

    def test_sensitivity_excluded_for_low_burden(self):
        vp = plan(_make_spec(), _make_candidate(ValidationBurden.LOW), _make_evidence())
        test_types = {t.test_type for t in vp.test_sequence}
        assert TestType.SENSITIVITY not in test_types

    def test_completeness_complete_with_no_gaps(self):
        vp = plan(_make_spec(), _make_candidate(), _make_evidence())
        assert vp.plan_completeness == PlanCompleteness.COMPLETE

    def test_completeness_partial_with_manageable_gaps(self):
        evidence = _make_evidence(GapSeverity.MANAGEABLE)
        vp = plan(_make_spec(), _make_candidate(), evidence)
        assert vp.plan_completeness == PlanCompleteness.PARTIAL_DUE_TO_EVIDENCE_GAPS

    def test_completeness_minimal_with_blocking_gaps(self):
        evidence = _make_evidence(GapSeverity.BLOCKING)
        vp = plan(_make_spec(), _make_candidate(), evidence)
        assert vp.plan_completeness == PlanCompleteness.MINIMAL

    def test_comparison_matrix_includes_baseline(self):
        vp = plan(_make_spec(), _make_candidate(), _make_evidence())
        assert "baseline_candidate" in vp.comparison_matrix.candidates_compared

    def test_backtest_is_prerequisite(self):
        vp = plan(_make_spec(), _make_candidate(), _make_evidence())
        backtest_id = None
        for t in vp.test_sequence:
            if t.test_type == TestType.OFFLINE_BACKTEST:
                backtest_id = t.test_id
                break
        assert backtest_id is not None

        for t in vp.test_sequence:
            if t.test_type != TestType.OFFLINE_BACKTEST:
                assert backtest_id in t.execution_prerequisites
