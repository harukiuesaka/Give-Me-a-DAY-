"""Tests for CandidateGenerator module (Round 2)."""

from datetime import datetime

from src.domain.models import (
    Archetype,
    Candidate,
    CandidateType,
    ClaimLayer,
    ComparableApproach,
    Constraints,
    DomainFrame,
    MinimumEvidenceStandard,
    ResearchSpec,
    TestableClaim,
    ValidationRequirements,
)
from src.llm.fallbacks import fallback_generate_candidates
from src.pipeline.candidate_generator import generate


def _make_spec() -> ResearchSpec:
    return ResearchSpec(
        spec_id="run_test_cg-RS",
        run_id="run_test_cg",
        primary_objective="検証: モメンタム効果が有意なリターンを生む",
        problem_frame="日本株モメンタム効果の検証可能性",
        constraints=Constraints(
            time="1週間以内",
            forbidden_behaviors=["空売り禁止"],
        ),
        validation_requirements=ValidationRequirements(
            must_test=["モメンタム効果が存在する"],
            must_compare=["baseline_candidate"],
            minimum_evidence_standard=MinimumEvidenceStandard.MODERATE,
        ),
    )


def _make_frame() -> DomainFrame:
    return DomainFrame(
        run_id="run_test_cg",
        archetype=Archetype.FACTOR,
        reframed_problem="日本株モメンタム効果の検証可能性",
        core_hypothesis="モメンタム効果が有意なリターンを生む",
        testable_claims=[
            TestableClaim(
                claim_id="TC-01", layer=ClaimLayer.PREMISE,
                claim="前提", falsification_condition="反証条件"),
        ],
        regime_dependencies=["市場トレンド", "ボラティリティ"],
    )


class TestFallbackCandidateGeneration:
    def test_produces_three_candidates(self):
        candidates = fallback_generate_candidates("run_test", Archetype.FACTOR, [])
        assert len(candidates) == 3

    def test_type_diversity(self):
        candidates = fallback_generate_candidates("run_test", Archetype.FACTOR, [])
        types = {c.candidate_type for c in candidates}
        assert CandidateType.BASELINE in types
        assert CandidateType.CONSERVATIVE in types
        assert CandidateType.EXPLORATORY in types

    def test_each_has_known_risks(self):
        candidates = fallback_generate_candidates("run_test", Archetype.FACTOR, [])
        for c in candidates:
            assert len(c.known_risks) >= 1

    def test_each_has_assumptions(self):
        candidates = fallback_generate_candidates("run_test", Archetype.FACTOR, [])
        for c in candidates:
            assert len(c.core_assumptions) >= 1
            for a in c.core_assumptions:
                assert a.failure_impact


class TestCandidateGeneratorIntegration:
    """Test generate() using fallback path (no LLM)."""

    def test_generate_returns_candidates(self):
        candidates = generate(_make_spec(), _make_frame())
        assert len(candidates) >= 3

    def test_generate_type_diversity(self):
        candidates = generate(_make_spec(), _make_frame())
        types = {c.candidate_type for c in candidates}
        assert CandidateType.BASELINE in types
        assert CandidateType.CONSERVATIVE in types
        assert CandidateType.EXPLORATORY in types

    def test_candidates_are_valid_models(self):
        candidates = generate(_make_spec(), _make_frame())
        for c in candidates:
            assert isinstance(c, Candidate)
            assert c.candidate_id
            assert c.name
            assert c.known_risks
