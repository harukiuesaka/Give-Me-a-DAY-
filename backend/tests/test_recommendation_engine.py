"""Tests for RecommendationEngine module (Round 2.5)."""

from src.domain.models import (
    Candidate,
    CandidateAssumption,
    CandidateType,
    ConfidenceLabel,
    CoverageMetrics,
    EvidencePlan,
    GapSeverity,
    ImplementationComplexity,
    MinimumEvidenceStandard,
    Recommendation,
    ResearchSpec,
    ValidationBurden,
    ValidationPlan,
    ValidationRequirements,
)
from src.pipeline.recommendation_engine import build_recommendation


def _make_spec() -> ResearchSpec:
    return ResearchSpec(
        spec_id="run_rec_test-RS",
        run_id="run_rec_test",
        primary_objective="テスト用目的",
        problem_frame="テスト用フレーム",
        validation_requirements=ValidationRequirements(
            must_test=["テスト項目"],
            minimum_evidence_standard=MinimumEvidenceStandard.MODERATE,
        ),
    )


def _make_candidate(cid: str, ctype: CandidateType, burden: ValidationBurden) -> Candidate:
    return Candidate(
        candidate_id=cid,
        name=f"Candidate {cid}",
        candidate_type=ctype,
        summary=f"Summary for {cid}",
        architecture_outline=["アーキテクチャ概要"],
        core_assumptions=[
            CandidateAssumption(
                assumption_id=f"{cid}-A1",
                statement="テスト前提",
                failure_impact="テスト影響",
            )
        ],
        validation_burden=burden,
        implementation_complexity=ImplementationComplexity.MEDIUM,
        known_risks=["リスク1", "リスク2"],
    )


def _make_evidence_plan(cid: str, coverage: float, gap: GapSeverity) -> EvidencePlan:
    return EvidencePlan(
        evidence_plan_id=f"{cid}-EP",
        candidate_id=cid,
        gap_severity=gap,
        coverage_metrics=CoverageMetrics(
            required_total=5,
            required_available=3,
            coverage_percentage=coverage,
        ),
    )


def _make_validation_plan(cid: str) -> ValidationPlan:
    return ValidationPlan(
        validation_plan_id=f"{cid}-VP",
        candidate_id=cid,
    )


class TestBuildRecommendation:
    def test_returns_recommendation(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert isinstance(rec, Recommendation)
        assert rec.run_id == "run_rec_test"

    def test_selects_best_and_runner_up(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert rec.best_candidate_id is not None
        assert rec.runner_up_candidate_id is not None
        assert rec.best_candidate_id != rec.runner_up_candidate_id

    def test_rejects_remaining(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert len(rec.rejected_candidate_ids) == 1

    def test_ranking_logic_min_3_axes(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert len(rec.ranking_logic) >= 3

    def test_open_unknowns_min_1(self):
        candidates = [_make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW)]
        eps = [_make_evidence_plan("C01", 70.0, GapSeverity.NONE)]
        vps = [_make_validation_plan("C01")]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert len(rec.open_unknowns) >= 1

    def test_critical_conditions_min_1(self):
        candidates = [_make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW)]
        eps = [_make_evidence_plan("C01", 70.0, GapSeverity.NONE)]
        vps = [_make_validation_plan("C01")]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert len(rec.critical_conditions) >= 1

    def test_confidence_capped_at_medium(self):
        """Without execution data, confidence must not be HIGH."""
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.LOW),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 95.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert rec.confidence_label != ConfidenceLabel.HIGH

    def test_confidence_low_on_blocking_gap(self):
        candidates = [_make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW)]
        eps = [_make_evidence_plan("C01", 30.0, GapSeverity.BLOCKING)]
        vps = [_make_validation_plan("C01")]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert rec.confidence_label == ConfidenceLabel.LOW

    def test_has_expiry(self):
        candidates = [_make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW)]
        eps = [_make_evidence_plan("C01", 70.0, GapSeverity.NONE)]
        vps = [_make_validation_plan("C01")]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert rec.recommendation_expiry is not None

    def test_raises_on_empty_candidates(self):
        import pytest
        with pytest.raises(ValueError):
            build_recommendation("run_rec_test", _make_spec(), [], [], [])

    def test_single_candidate_no_runner_up(self):
        candidates = [_make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW)]
        eps = [_make_evidence_plan("C01", 70.0, GapSeverity.NONE)]
        vps = [_make_validation_plan("C01")]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps)
        assert rec.best_candidate_id == "C01"
        assert rec.runner_up_candidate_id is None
        assert len(rec.rejected_candidate_ids) == 0
