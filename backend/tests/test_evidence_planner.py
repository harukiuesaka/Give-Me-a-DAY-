"""Tests for EvidencePlanner module (Round 2)."""

from src.domain.models import (
    Availability,
    Candidate,
    CandidateAssumption,
    CandidateType,
    EvidenceCategory,
    EvidencePlan,
    GapSeverity,
    MinimumEvidenceStandard,
    PointInTimeStatus,
    RequirementLevel,
    ResearchSpec,
    ValidationBurden,
    ValidationRequirements,
)
from src.pipeline.evidence_planner import plan


def _make_spec() -> ResearchSpec:
    return ResearchSpec(
        spec_id="run_test_ep-RS",
        run_id="run_test_ep",
        primary_objective="検証: モメンタム効果",
        problem_frame="モメンタム効果の検証",
        validation_requirements=ValidationRequirements(
            minimum_evidence_standard=MinimumEvidenceStandard.MODERATE,
        ),
    )


def _make_candidate() -> Candidate:
    return Candidate(
        candidate_id="run_test_ep_C01",
        name="単純モメンタム戦略",
        candidate_type=CandidateType.BASELINE,
        summary="12ヶ月モメンタムに基づく戦略",
        architecture_outline=["リターン計算", "ランキング", "月次リバランス"],
        core_assumptions=[
            CandidateAssumption(
                assumption_id="CA01",
                statement="モメンタム効果が持続する",
                failure_impact="戦略の有効性が消失",
            )
        ],
        required_inputs=["日次株価データ(OHLCV)", "銘柄ユニバース構成情報"],
        validation_burden=ValidationBurden.LOW,
        known_risks=["モメンタムクラッシュ", "取引コスト"],
    )


class TestEvidencePlanner:
    def test_produces_valid_plan(self):
        ep = plan(_make_spec(), _make_candidate())
        assert isinstance(ep, EvidencePlan)
        assert ep.candidate_id == "run_test_ep_C01"

    def test_includes_price_data(self):
        ep = plan(_make_spec(), _make_candidate())
        categories = [it.category for it in ep.evidence_items]
        assert EvidenceCategory.PRICE in categories

    def test_required_optional_proxy_distinction(self):
        ep = plan(_make_spec(), _make_candidate())
        levels = {it.requirement_level for it in ep.evidence_items}
        assert RequirementLevel.REQUIRED in levels

    def test_coverage_metrics_computed(self):
        ep = plan(_make_spec(), _make_candidate())
        assert ep.coverage_metrics.required_total > 0
        assert ep.coverage_metrics.coverage_percentage >= 0

    def test_lkg07_applied_for_pit_none(self):
        ep = plan(_make_spec(), _make_candidate())
        pit_none_items = [
            it for it in ep.evidence_items
            if it.point_in_time_status == PointInTimeStatus.NONE
            and it.category != EvidenceCategory.PRICE
        ]
        for it in pit_none_items:
            assert "LKG-07" in it.leakage_risk_patterns

    def test_gap_severity_not_blocking_for_available_data(self):
        ep = plan(_make_spec(), _make_candidate())
        # With default candidate (price data available), should not be blocking
        assert ep.gap_severity != GapSeverity.BLOCKING
