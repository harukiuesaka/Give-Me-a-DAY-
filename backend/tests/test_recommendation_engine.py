"""Tests for RecommendationEngine module (Round 2.5)."""

from src.domain.models import (
    Audit,
    AuditCategory,
    AuditIssue,
    AuditStatus,
    Candidate,
    CandidateAssumption,
    CandidateType,
    ComparisonMatrixData,
    ComparisonResult,
    ConfidenceLabel,
    CoverageMetrics,
    EvidencePlan,
    ExecutionBasedRanking,
    GapSeverity,
    ImplementationComplexity,
    MinimumEvidenceStandard,
    RankingRationale,
    Recommendation,
    ResearchSpec,
    Severity,
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


def _make_audit(
    cid: str,
    status: AuditStatus,
    residual_risks: list[str] | None = None,
    issues: list[AuditIssue] | None = None,
) -> Audit:
    return Audit(
        candidate_id=cid,
        audit_status=status,
        issues=issues or [],
        residual_risks=residual_risks or ["監査リスク1", "監査リスク2"],
        surviving_assumptions=["テスト前提"] if status != AuditStatus.REJECTED else [],
        rejection_reason=f"{cid} は監査で棄却されました。" if status == AuditStatus.REJECTED else None,
    )


def _make_comparison_result(
    *,
    best: str | None = None,
    runner_up: str | None = None,
    rationale: list[RankingRationale] | None = None,
) -> ComparisonResult:
    return ComparisonResult(
        comparison_id="cmp_rec_test",
        run_id="run_rec_test",
        comparison_matrix=ComparisonMatrixData(candidates=["C01", "C02", "C03"], baseline_candidate_id="C01"),
        execution_based_ranking=ExecutionBasedRanking(
            recommended_best=best,
            recommended_runner_up=runner_up,
            ranking_rationale=rationale or [],
        ),
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

    def test_audit_rejected_candidate_is_not_ranked(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit("C01", AuditStatus.PASSED),
            _make_audit("C02", AuditStatus.REJECTED),
            _make_audit("C03", AuditStatus.PASSED_WITH_WARNINGS),
        ]

        rec = build_recommendation("run_rec_test", _make_spec(), candidates, eps, vps, audits=audits)
        assert rec.best_candidate_id in {"C01", "C03"}
        assert rec.runner_up_candidate_id in {"C01", "C03", None}
        assert "C02" in rec.rejected_candidate_ids

    def test_execution_based_ranking_is_preferred_among_survivors(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit("C01", AuditStatus.PASSED),
            _make_audit("C02", AuditStatus.PASSED),
            _make_audit("C03", AuditStatus.PASSED_WITH_WARNINGS),
        ]
        comparison_result = _make_comparison_result(
            best="C02",
            runner_up="C03",
            rationale=[
                RankingRationale(comparison_axis="sharpe_ratio", winner="C02", margin="0.45"),
                RankingRationale(comparison_axis="excess_return_vs_benchmark", winner="C03", margin="3.10"),
            ],
        )

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=comparison_result,
        )
        assert rec.best_candidate_id == "C02"
        assert rec.runner_up_candidate_id == "C03"
        assert rec.ranking_logic[0].comparison_axis.startswith("実行比較/")

    def test_falls_back_to_planning_heuristics_when_execution_ranking_absent(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit("C01", AuditStatus.PASSED),
            _make_audit("C02", AuditStatus.PASSED),
        ]
        comparison_result = _make_comparison_result()

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=comparison_result,
        )
        assert rec.best_candidate_id == "C01"
        assert rec.runner_up_candidate_id == "C02"

    def test_confidence_is_reduced_when_best_candidate_has_material_audit_warnings(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 90.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit(
                "C01",
                AuditStatus.PASSED_WITH_WARNINGS,
                issues=[
                    AuditIssue(
                        issue_id="C01-ovf-warning",
                        severity=Severity.HIGH,
                        category=AuditCategory.OVERFITTING_RISK,
                        title="OOSで性能低下が見られる",
                        explanation="過学習懸念が残る",
                    )
                ],
            ),
            _make_audit("C02", AuditStatus.PASSED),
        ]
        comparison_result = _make_comparison_result(best="C01", runner_up="C02")

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=comparison_result,
        )
        assert rec.best_candidate_id == "C01"
        assert rec.confidence_label == ConfidenceLabel.LOW
        assert "過学習" in rec.confidence_explanation or "実行根拠" in rec.confidence_explanation

    def test_execution_ranking_still_excludes_rejected_candidates(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit("C01", AuditStatus.PASSED),
            _make_audit("C02", AuditStatus.REJECTED),
            _make_audit("C03", AuditStatus.PASSED_WITH_WARNINGS),
        ]
        comparison_result = _make_comparison_result(best="C02", runner_up="C03")

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=comparison_result,
        )
        assert rec.best_candidate_id == "C03"
        assert rec.runner_up_candidate_id == "C01"
        assert "C02" in rec.rejected_candidate_ids

    def test_zero_survivor_case_returns_no_recommendation_candidates(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit("C01", AuditStatus.REJECTED),
            _make_audit("C02", AuditStatus.REJECTED),
        ]

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=_make_comparison_result(best="C01", runner_up="C02"),
        )
        assert rec.best_candidate_id is None
        assert rec.runner_up_candidate_id is None
        assert set(rec.rejected_candidate_ids) == {"C01", "C02"}
        assert rec.confidence_label == ConfidenceLabel.LOW

    def test_single_audit_survivor_is_returned_without_fake_alternative(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
            _make_candidate("C03", CandidateType.EXPLORATORY, ValidationBurden.HIGH),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            _make_audit("C01", AuditStatus.REJECTED),
            _make_audit("C02", AuditStatus.PASSED_WITH_WARNINGS),
            _make_audit("C03", AuditStatus.REJECTED),
        ]

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=_make_comparison_result(best="C01", runner_up="C02"),
        )
        assert rec.best_candidate_id == "C02"
        assert rec.runner_up_candidate_id is None
        assert set(rec.rejected_candidate_ids) == {"C01", "C03"}

    def test_overfitting_rejected_candidate_is_excluded_from_survivors(self):
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE, ValidationBurden.LOW),
            _make_candidate("C02", CandidateType.CONSERVATIVE, ValidationBurden.MEDIUM),
        ]
        eps = [_make_evidence_plan(c.candidate_id, 70.0, GapSeverity.NONE) for c in candidates]
        vps = [_make_validation_plan(c.candidate_id) for c in candidates]
        audits = [
            Audit(
                candidate_id="C01",
                audit_status=AuditStatus.REJECTED,
                rejection_reason="C01 は OOS で性能が崩れており過学習リスクが高いため棄却されました。",
                surviving_assumptions=[],
                residual_risks=[],
            ),
            _make_audit("C02", AuditStatus.PASSED),
        ]

        rec = build_recommendation(
            "run_rec_test",
            _make_spec(),
            candidates,
            eps,
            vps,
            audits=audits,
            comparison_result=_make_comparison_result(best="C01", runner_up="C02"),
        )
        assert rec.best_candidate_id == "C02"
        assert rec.runner_up_candidate_id is None
        assert "C01" in rec.rejected_candidate_ids
