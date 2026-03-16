"""
Module 3: ResearchSpecCompiler

Consolidate UserIntent + DomainFrame into ResearchSpec.
This is the contract between framing and execution.

Mostly mechanical derivation — no LLM needed for v1.
"""

import logging

from src.domain.models import (
    AssumptionCategory,
    AssumptionItem,
    AssumptionSource,
    ClaimLayer,
    Constraints,
    DisqualifyingAppliesTo,
    DisqualifyingFailure,
    DomainFrame,
    EvidenceRequirements,
    MinimumEvidenceStandard,
    RecommendationRequirements,
    ResearchSpec,
    RiskPreference,
    TimeHorizonPreference,
    UserIntent,
    ValidationRequirements,
)

logger = logging.getLogger(__name__)


def compile(user_intent: UserIntent, domain_frame: DomainFrame) -> ResearchSpec:
    """
    Compile ResearchSpec from UserIntent + DomainFrame.

    Mechanical derivation: no LLM required.
    """
    run_id = user_intent.run_id

    # 1. Derive minimum evidence standard
    evidence_standard = _derive_evidence_standard(
        user_intent.risk_preference,
        user_intent.time_horizon_preference,
    )

    # 2. Build assumption space
    assumptions = _build_assumption_space(
        domain_frame.critical_assumptions,
        domain_frame.archetype.value,
        user_intent.open_uncertainties,
    )

    # 3. Derive disqualifying failures from testable claims
    failures = _derive_disqualifying_failures(
        domain_frame.testable_claims,
        user_intent.success_definition,
        evidence_standard,
    )

    # 4. Compile constraints
    constraints = _compile_constraints(user_intent)

    # 5. Infer evidence requirements
    evidence_reqs = _infer_evidence_requirements(
        domain_frame.archetype.value,
        domain_frame.testable_claims,
    )

    # 6. Extract secondary objectives
    secondary = _extract_secondary_objectives(domain_frame)

    # 7. Validation requirements
    validation_reqs = ValidationRequirements(
        must_test=[c.claim for c in domain_frame.testable_claims],
        must_compare=["baseline_candidate"],
        disqualifying_failures=failures,
        minimum_evidence_standard=evidence_standard,
    )

    return ResearchSpec(
        spec_id=f"{run_id}-RS",
        run_id=run_id,
        primary_objective=f"検証: {domain_frame.core_hypothesis}",
        secondary_objectives=secondary,
        problem_frame=domain_frame.reframed_problem,
        assumption_space=assumptions,
        constraints=constraints,
        evidence_requirements=evidence_reqs,
        validation_requirements=validation_reqs,
        recommendation_requirements=RecommendationRequirements(),
    )


def _derive_evidence_standard(
    risk: RiskPreference, horizon: TimeHorizonPreference
) -> MinimumEvidenceStandard:
    """
    Derive minimum evidence standard from risk × time_horizon.
    - very_low risk → strong
    - low + quality_over_speed → strong
    - high + fast → weak (with warning)
    - else → moderate
    """
    if risk == RiskPreference.VERY_LOW:
        return MinimumEvidenceStandard.STRONG
    if risk == RiskPreference.LOW and horizon == TimeHorizonPreference.QUALITY_OVER_SPEED:
        return MinimumEvidenceStandard.STRONG
    if risk == RiskPreference.HIGH and horizon == TimeHorizonPreference.FAST:
        logger.warning("High risk + fast horizon: evidence standard set to weak")
        return MinimumEvidenceStandard.WEAK
    return MinimumEvidenceStandard.MODERATE


# Domain-default assumptions per category
_DOMAIN_DEFAULT_ASSUMPTIONS: list[dict] = [
    {
        "category": "market_efficiency",
        "statement": "対象市場は完全効率的ではなく、一定の非効率性が存在する",
        "falsification": "統計的にランダムウォークと区別できない",
    },
    {
        "category": "stationarity",
        "statement": "過去の統計的関係性が検証期間中にある程度維持される",
        "falsification": "構造変化検定でp < 0.05の有意な変化が検出される",
    },
    {
        "category": "liquidity",
        "statement": "対象銘柄の流動性が戦略実行に十分である",
        "falsification": "想定ポジションサイズが日次出来高の5%を超える",
    },
    {
        "category": "data_quality",
        "statement": "使用するデータが十分な品質・正確性を持つ",
        "falsification": "データ品質レポートでcritical issueが検出される",
    },
    {
        "category": "cost",
        "statement": "取引コストが想定範囲内に収まる",
        "falsification": "実際のコストが想定の2倍以上",
    },
]


def _build_assumption_space(
    critical_assumptions: list[str],
    archetype: str,
    open_uncertainties: list[str],
) -> list[AssumptionItem]:
    """
    Build assumption_space from frame + domain defaults.
    Max 15 items.
    """
    items: list[AssumptionItem] = []
    idx = 1

    # User-stated assumptions from critical_assumptions
    for stmt in critical_assumptions[:5]:
        items.append(AssumptionItem(
            assumption_id=f"A-{idx:02d}",
            statement=stmt,
            category=AssumptionCategory.MARKET_EFFICIENCY,  # default category
            falsification_condition="この仮定が実証的に否定される",
            source=AssumptionSource.SYSTEM_INFERRED,
        ))
        idx += 1

    # Open uncertainties as assumptions
    for unc in open_uncertainties[:3]:
        items.append(AssumptionItem(
            assumption_id=f"A-{idx:02d}",
            statement=f"不確実性: {unc}",
            category=AssumptionCategory.DATA_QUALITY,
            falsification_condition="この不確実性が負の方向に解消される",
            source=AssumptionSource.USER_STATED,
        ))
        idx += 1

    # Domain defaults
    for default in _DOMAIN_DEFAULT_ASSUMPTIONS:
        if idx > 15:
            break
        items.append(AssumptionItem(
            assumption_id=f"A-{idx:02d}",
            statement=default["statement"],
            category=AssumptionCategory(default["category"]),
            falsification_condition=default["falsification"],
            source=AssumptionSource.DOMAIN_DEFAULT,
        ))
        idx += 1

    return items[:15]


def _derive_disqualifying_failures(
    claims: list, success_definition: str, standard: MinimumEvidenceStandard
) -> list[DisqualifyingFailure]:
    """Map falsification_conditions to disqualifying failure entries."""
    failures: list[DisqualifyingFailure] = []

    for i, claim in enumerate(claims):
        failures.append(DisqualifyingFailure(
            failure_id=f"DF-{i+1:02d}",
            description=f"Claim棄却: {claim.claim}",
            metric=claim.falsification_condition,
            threshold=claim.falsification_condition,
            applies_to=DisqualifyingAppliesTo.ALL_CANDIDATES,
        ))

    # Add standard-derived failure
    if standard == MinimumEvidenceStandard.STRONG:
        failures.append(DisqualifyingFailure(
            failure_id=f"DF-{len(failures)+1:02d}",
            description="エビデンスカバレッジが不十分",
            metric="evidence_coverage_percentage",
            threshold="< 70%",
            applies_to=DisqualifyingAppliesTo.ALL_CANDIDATES,
        ))

    return failures


def _compile_constraints(intent: UserIntent) -> Constraints:
    """Compile constraints from UserIntent."""
    time_map = {
        TimeHorizonPreference.FAST: "最短（数時間）",
        TimeHorizonPreference.ONE_DAY: "1日以内",
        TimeHorizonPreference.ONE_WEEK: "1週間以内",
        TimeHorizonPreference.ONE_MONTH: "1ヶ月以内",
        TimeHorizonPreference.QUALITY_OVER_SPEED: "品質優先（期限なし）",
    }
    return Constraints(
        time=time_map.get(intent.time_horizon_preference, "1週間以内"),
        budget="v1標準（仮想資金100万円）",
        tooling=["Python", "pandas", "numpy"],
        forbidden_behaviors=intent.must_not_do,
    )


def _infer_evidence_requirements(archetype: str, claims: list) -> EvidenceRequirements:
    """Infer evidence requirements from archetype and claims."""
    # All archetypes need price data
    required = ["日次株価データ（OHLCV）", "銘柄ユニバース構成データ"]
    optional = []

    archetype_reqs = {
        "FACTOR": (["ファクターデータ（PBR, ROE, モメンタム等）"], ["セクター分類データ"]),
        "STAT_ARB": (["銘柄間相関データ"], ["出来高データ"]),
        "EVENT": (["コーポレートイベントデータ"], ["ニュースデータ"]),
        "MACRO": (["マクロ経済指標データ"], ["金利データ"]),
        "ML_SIGNAL": (["特徴量データ"], ["オルタナティブデータ"]),
        "ALT_DATA": (["オルタナティブデータソース"], ["テキストデータ"]),
    }

    extra_req, extra_opt = archetype_reqs.get(archetype, ([], []))
    required.extend(extra_req)
    optional.extend(extra_opt)

    return EvidenceRequirements(
        required_data=required,
        optional_data=optional,
        proxy_data_allowed=True,
        evidence_gaps=[],  # Filled by EvidencePlanner
    )


def _extract_secondary_objectives(frame: DomainFrame) -> list[str]:
    """Extract secondary objectives from DomainFrame."""
    secondary = []
    for claim in frame.testable_claims:
        if claim.layer == ClaimLayer.PRACTICAL:
            secondary.append(f"実用性検証: {claim.claim}")
    if frame.regime_dependencies:
        secondary.append(f"レジーム依存性の評価: {', '.join(frame.regime_dependencies[:2])}")
    return secondary
