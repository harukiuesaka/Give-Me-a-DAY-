"""Tests for ResearchSpecCompiler module (Round 2)."""

from datetime import datetime

from src.domain.models import (
    Archetype,
    ClaimLayer,
    ComparableApproach,
    DomainFrame,
    MinimumEvidenceStandard,
    ResearchSpec,
    RiskPreference,
    TestableClaim,
    TimeHorizonPreference,
    UserIntent,
)
from src.pipeline.research_spec_compiler import compile


def _make_intent(
    risk: RiskPreference = RiskPreference.MEDIUM,
    horizon: TimeHorizonPreference = TimeHorizonPreference.ONE_WEEK,
) -> UserIntent:
    return UserIntent(
        run_id="run_test_rsc",
        created_at=datetime.utcnow(),
        raw_goal="日本株でモメンタム戦略を検証したい",
        domain="investment_research",
        user_goal_summary="日本株モメンタム戦略の検証",
        success_definition="年率8-12%のリターン",
        risk_preference=risk,
        time_horizon_preference=horizon,
        must_not_do=["空売り禁止"],
        open_uncertainties=["成功基準が不明確"],
    )


def _make_frame() -> DomainFrame:
    return DomainFrame(
        run_id="run_test_rsc",
        archetype=Archetype.FACTOR,
        reframed_problem="日本株モメンタム効果の検証可能性",
        core_hypothesis="モメンタム効果が有意なリターンを生む",
        testable_claims=[
            TestableClaim(
                claim_id="TC-01", layer=ClaimLayer.PREMISE,
                claim="モメンタム効果が存在する",
                falsification_condition="リターンプレミアムがp > 0.05"),
            TestableClaim(
                claim_id="TC-02", layer=ClaimLayer.CORE,
                claim="ベンチマークを上回る",
                falsification_condition="リスク調整後リターンが負"),
            TestableClaim(
                claim_id="TC-03", layer=ClaimLayer.PRACTICAL,
                claim="コスト後も実行可能",
                falsification_condition="ネットリターンが負"),
        ],
        critical_assumptions=["モメンタム効果が持続する", "十分な流動性がある"],
        regime_dependencies=["市場トレンド", "ボラティリティ"],
        comparable_known_approaches=[
            ComparableApproach(name="FF3", relevance="ベース", known_outcome="長期有意")
        ],
    )


class TestResearchSpecCompiler:
    def test_produces_valid_spec(self):
        spec = compile(_make_intent(), _make_frame())
        assert isinstance(spec, ResearchSpec)
        assert spec.run_id == "run_test_rsc"
        assert spec.spec_id == "run_test_rsc-RS"

    def test_evidence_standard_moderate(self):
        spec = compile(_make_intent(), _make_frame())
        assert spec.validation_requirements.minimum_evidence_standard == MinimumEvidenceStandard.MODERATE

    def test_evidence_standard_strong_for_very_low_risk(self):
        spec = compile(_make_intent(risk=RiskPreference.VERY_LOW), _make_frame())
        assert spec.validation_requirements.minimum_evidence_standard == MinimumEvidenceStandard.STRONG

    def test_evidence_standard_weak_for_high_fast(self):
        spec = compile(
            _make_intent(risk=RiskPreference.HIGH, horizon=TimeHorizonPreference.FAST),
            _make_frame(),
        )
        assert spec.validation_requirements.minimum_evidence_standard == MinimumEvidenceStandard.WEAK

    def test_disqualifying_failures_present(self):
        spec = compile(_make_intent(), _make_frame())
        assert len(spec.validation_requirements.disqualifying_failures) >= 3

    def test_assumption_space_within_limit(self):
        spec = compile(_make_intent(), _make_frame())
        assert len(spec.assumption_space) <= 15

    def test_constraints_include_forbidden(self):
        spec = compile(_make_intent(), _make_frame())
        assert "空売り禁止" in spec.constraints.forbidden_behaviors

    def test_recommendation_requirements_defaults(self):
        spec = compile(_make_intent(), _make_frame())
        assert spec.recommendation_requirements.must_return_runner_up is True
        assert spec.recommendation_requirements.must_return_rejections is True
        assert spec.recommendation_requirements.must_surface_unknowns is True
        assert spec.recommendation_requirements.allow_no_valid_candidate is True
