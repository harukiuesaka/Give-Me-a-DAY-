"""Tests for DomainFramer module (Round 2)."""

import pytest

from src.domain.models import (
    Archetype,
    ClaimLayer,
    DomainFrame,
    RiskPreference,
    TimeHorizonPreference,
    UserIntent,
)
from src.llm.fallbacks import fallback_classify_archetype, fallback_domain_frame
from src.pipeline.domain_framer import frame


def _make_intent(
    goal: str = "日本株でモメンタム戦略を検証したい",
    summary: str = "日本株モメンタム戦略の検証",
    risk: RiskPreference = RiskPreference.MEDIUM,
) -> UserIntent:
    from datetime import datetime
    return UserIntent(
        run_id="run_test_df",
        created_at=datetime.utcnow(),
        raw_goal=goal,
        domain="investment_research",
        user_goal_summary=summary,
        success_definition="年率8-12%のリターン",
        risk_preference=risk,
        time_horizon_preference=TimeHorizonPreference.ONE_WEEK,
        must_not_do=[],
        available_inputs=[],
        open_uncertainties=[],
    )


class TestFallbackArchetypeClassification:
    def test_factor_keywords(self):
        assert fallback_classify_archetype("モメンタムファクター投資") == Archetype.FACTOR

    def test_stat_arb_keywords(self):
        assert fallback_classify_archetype("ペアトレードによる裁定") == Archetype.STAT_ARB

    def test_event_keywords(self):
        assert fallback_classify_archetype("決算イベント戦略") == Archetype.EVENT

    def test_macro_keywords(self):
        assert fallback_classify_archetype("マクロ経済指標で金利を活用") == Archetype.MACRO

    def test_unclassified(self):
        assert fallback_classify_archetype("何か投資戦略") == Archetype.UNCLASSIFIED


class TestFallbackDomainFrame:
    def test_produces_valid_frame(self):
        intent = _make_intent()
        frame_result = fallback_domain_frame(intent)

        assert isinstance(frame_result, DomainFrame)
        assert frame_result.run_id == "run_test_df"
        assert frame_result.archetype == Archetype.FACTOR

    def test_claims_cover_all_layers(self):
        intent = _make_intent()
        frame_result = fallback_domain_frame(intent)

        layers = {c.layer for c in frame_result.testable_claims}
        assert ClaimLayer.PREMISE in layers
        assert ClaimLayer.CORE in layers
        assert ClaimLayer.PRACTICAL in layers

    def test_claims_have_falsification(self):
        intent = _make_intent()
        frame_result = fallback_domain_frame(intent)

        for claim in frame_result.testable_claims:
            assert claim.falsification_condition, f"Claim {claim.claim_id} missing falsification"

    def test_regime_dependencies_non_empty(self):
        intent = _make_intent()
        frame_result = fallback_domain_frame(intent)
        assert len(frame_result.regime_dependencies) >= 2

    def test_comparable_approaches_present(self):
        intent = _make_intent()
        frame_result = fallback_domain_frame(intent)
        assert len(frame_result.comparable_known_approaches) >= 1


class TestDomainFramerIntegration:
    """Test frame() using fallback path (no LLM)."""

    def test_frame_returns_valid_domain_frame(self):
        intent = _make_intent()
        result = frame(intent)

        assert isinstance(result, DomainFrame)
        assert result.run_id == intent.run_id
        assert len(result.testable_claims) >= 3
        assert len(result.regime_dependencies) >= 2

    def test_frame_with_macro_goal(self):
        intent = _make_intent(
            goal="マクロ経済指標を使った金利ベースの資産配分戦略",
            summary="マクロ経済指標による資産配分",
        )
        result = frame(intent)
        assert result.archetype == Archetype.MACRO
