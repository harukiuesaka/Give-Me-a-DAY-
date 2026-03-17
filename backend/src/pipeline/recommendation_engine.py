"""
Module 8: RecommendationEngine

Produce a Recommendation from planning outputs.

Without execution-phase data (Round 3+), ranking is based on:
- validation_burden (lower = better)
- evidence coverage (higher = better)
- known_risks count (fewer = better, but zero is suspicious)
- candidate_type diversity

This is a planning-stage heuristic. With backtest results (Round 3+),
ranking will be evidence-based.
"""

import logging

from src.domain.models import (
    Candidate,
    CandidateType,
    ConfidenceLabel,
    CriticalCondition,
    EvidencePlan,
    ExpiryType,
    GapSeverity,
    MinimumEvidenceStandard,
    NextValidationPriority,
    NextValidationStep,
    OpenUnknown,
    RankingLogicItem,
    Recommendation,
    RecommendationExpiry,
    ResearchSpec,
    ValidationBurden,
    ValidationPlan,
)

logger = logging.getLogger(__name__)


def build_recommendation(
    run_id: str,
    research_spec: ResearchSpec,
    candidates: list[Candidate],
    evidence_plans: list[EvidencePlan],
    validation_plans: list[ValidationPlan],
) -> Recommendation:
    """
    Build a Recommendation from planning outputs.

    Selects best + runner_up candidates. Rejects the rest.
    Produces ranking logic, open unknowns, critical conditions,
    confidence label, and expiry.
    """
    if not candidates:
        raise ValueError("Cannot build recommendation with zero candidates")

    # 1. Score and rank candidates
    scored = _score_candidates(candidates, evidence_plans, validation_plans)
    ranked = sorted(scored, key=lambda x: x[1], reverse=True)

    best_candidate = ranked[0][0]
    runner_up = ranked[1][0] if len(ranked) > 1 else None
    rejected = [c for c, _ in ranked[2:]]

    # 2. Build ranking logic (min 3 axes)
    ranking_logic = _build_ranking_logic(best_candidate, runner_up, scored)

    # 3. Build open unknowns (min 1)
    open_unknowns = _build_open_unknowns(research_spec, evidence_plans)

    # 4. Build critical conditions (min 1)
    critical_conditions = _build_critical_conditions(research_spec, best_candidate)

    # 5. Derive confidence label
    confidence = _derive_confidence(
        research_spec.validation_requirements.minimum_evidence_standard,
        evidence_plans,
        validation_plans,
    )

    # 6. Expiry
    expiry = RecommendationExpiry(
        type=ExpiryType.TIME_BASED,
        description="3ヶ月後に自動で再評価します。市場環境の変化により、推奨が変わる可能性があります。",
        expiry_trigger="quarterly_re_evaluation",
    )

    # 7. Next validation steps
    next_steps = _build_next_steps(research_spec)

    return Recommendation(
        run_id=run_id,
        best_candidate_id=best_candidate.candidate_id,
        runner_up_candidate_id=runner_up.candidate_id if runner_up else None,
        rejected_candidate_ids=[c.candidate_id for c in rejected],
        ranking_logic=ranking_logic,
        open_unknowns=open_unknowns,
        critical_conditions=critical_conditions,
        confidence_label=confidence,
        confidence_explanation=_confidence_explanation(confidence),
        next_validation_steps=next_steps,
        recommendation_expiry=expiry,
    )


def _score_candidates(
    candidates: list[Candidate],
    evidence_plans: list[EvidencePlan],
    validation_plans: list[ValidationPlan],
) -> list[tuple[Candidate, float]]:
    """
    Score each candidate based on planning-stage heuristics.

    Scoring axes (planning-stage, pre-execution):
    - validation_burden: low=3, medium=2, high=1
    - evidence coverage: percentage / 100
    - risk balance: 2-3 risks = 1.0, 1 = 0.7, 4+ = 0.8, 0 = 0.3
    - type bonus: baseline=0.1 (known approach advantage)
    """
    ep_map = {ep.candidate_id: ep for ep in evidence_plans}

    scored = []
    for c in candidates:
        score = 0.0

        # Validation burden
        burden_scores = {
            ValidationBurden.LOW: 3.0,
            ValidationBurden.MEDIUM: 2.0,
            ValidationBurden.HIGH: 1.0,
        }
        score += burden_scores.get(c.validation_burden, 2.0)

        # Evidence coverage
        ep = ep_map.get(c.candidate_id)
        if ep:
            score += ep.coverage_metrics.coverage_percentage / 100.0

        # Risk balance
        n_risks = len(c.known_risks)
        if n_risks == 0:
            score += 0.3  # Suspicious — no risks claimed
        elif 2 <= n_risks <= 3:
            score += 1.0
        elif n_risks == 1:
            score += 0.7
        else:
            score += 0.8

        # Type bonus for baseline (known approach)
        if c.candidate_type == CandidateType.BASELINE:
            score += 0.1

        scored.append((c, round(score, 3)))

    return scored


def _build_ranking_logic(
    best: Candidate,
    runner_up: Candidate | None,
    scored: list[tuple[Candidate, float]],
) -> list[RankingLogicItem]:
    """Build ranking rationale (min 3 axes)."""
    runner_up_name = runner_up.name if runner_up else "該当なし"

    items = [
        RankingLogicItem(
            comparison_axis="実装複雑性",
            best_assessment=f"{best.name}: {best.implementation_complexity.value}",
            runner_up_assessment=f"{runner_up_name}: {runner_up.implementation_complexity.value}" if runner_up else "該当なし",
            verdict=f"{best.name}の実装複雑性が{'同等' if runner_up and best.implementation_complexity == runner_up.implementation_complexity else '優位'}",
        ),
        RankingLogicItem(
            comparison_axis="検証負担",
            best_assessment=f"{best.name}: {best.validation_burden.value}",
            runner_up_assessment=f"{runner_up_name}: {runner_up.validation_burden.value}" if runner_up else "該当なし",
            verdict=f"{best.name}の検証コストが{'同等' if runner_up and best.validation_burden == runner_up.validation_burden else '有利'}",
        ),
        RankingLogicItem(
            comparison_axis="既知リスク数",
            best_assessment=f"{best.name}: {len(best.known_risks)}件",
            runner_up_assessment=f"{runner_up_name}: {len(runner_up.known_risks)}件" if runner_up else "該当なし",
            verdict="リスクが認識されており、検証計画に反映済み",
        ),
    ]

    return items


def _build_open_unknowns(
    spec: ResearchSpec, evidence_plans: list[EvidencePlan]
) -> list[OpenUnknown]:
    """Build open unknowns (min 1)."""
    unknowns = [
        OpenUnknown(
            unknown_id="OU-01",
            description="バックテスト未実施のため、過去データでの実際のパフォーマンスは未検証",
            impact_if_resolved_positively="推奨の信頼度が上昇し、Paper Runの根拠が強化される",
            impact_if_resolved_negatively="推奨が棄却され、別の候補が選ばれる可能性がある",
            resolution_method="過去データでのバックテスト実施（Round 3で予定）",
        ),
    ]

    # Add evidence gap unknowns
    for ep in evidence_plans:
        if ep.gap_severity != GapSeverity.NONE:
            unknowns.append(OpenUnknown(
                unknown_id=f"OU-EP-{ep.candidate_id[-3:]}",
                description=f"候補 {ep.candidate_id} のエビデンスカバレッジに未解決のギャップあり（{ep.gap_severity.value}）",
                impact_if_resolved_positively="検証精度の向上",
                impact_if_resolved_negatively="候補の信頼度低下または棄却",
                resolution_method="追加データの取得または代替データの評価",
            ))

    return unknowns


def _build_critical_conditions(
    spec: ResearchSpec, best: Candidate
) -> list[CriticalCondition]:
    """Build critical conditions (min 1)."""
    conditions = [
        CriticalCondition(
            condition_id="CC-01",
            statement="バックテストで戦略がベンチマークを上回ること",
            verification_method="過去データでのバックテスト（Round 3）",
            verification_timing="Paper Run開始前",
            source="validation_requirements",
        ),
        CriticalCondition(
            condition_id="CC-02",
            statement="この推奨は計画段階の評価に基づいており、実行段階の検証により変更される可能性がある",
            verification_method="バックテスト + 統計的検定（Round 3）",
            verification_timing="3ヶ月以内の再評価",
            source="recommendation_expiry",
        ),
    ]
    return conditions


def _derive_confidence(
    evidence_standard: MinimumEvidenceStandard,
    evidence_plans: list[EvidencePlan],
    validation_plans: list[ValidationPlan],
) -> ConfidenceLabel:
    """
    Derive confidence mechanically.

    Without execution results (Round 3+), confidence is capped at MEDIUM.
    Planning-stage factors:
    - Evidence coverage
    - Gap severity
    - Plan completeness
    """
    # Without backtest results, confidence is at most MEDIUM
    # Check if any blocking gaps exist
    has_blocking = any(ep.gap_severity == GapSeverity.BLOCKING for ep in evidence_plans)
    if has_blocking:
        return ConfidenceLabel.LOW

    avg_coverage = sum(
        ep.coverage_metrics.coverage_percentage for ep in evidence_plans
    ) / max(len(evidence_plans), 1)

    if avg_coverage < 50:
        return ConfidenceLabel.LOW

    # Without execution, max is MEDIUM
    return ConfidenceLabel.MEDIUM


def _confidence_explanation(confidence: ConfidenceLabel) -> str:
    """Generate confidence explanation. No false confidence."""
    explanations = {
        ConfidenceLabel.LOW: "計画段階の評価のみに基づいており、バックテスト未実施。エビデンスのギャップがあるため、信頼度は低い。",
        ConfidenceLabel.MEDIUM: "計画段階の評価では妥当だが、バックテストによる実証は未完了。過去データでの検証後に信頼度が変わる可能性がある。",
        ConfidenceLabel.HIGH: "計画段階および実行段階の検証を通過。ただし、過去の実績は将来の成果を保証しない。",
    }
    return explanations[confidence]


def _build_next_steps(spec: ResearchSpec) -> list[NextValidationStep]:
    """Build next validation steps."""
    return [
        NextValidationStep(
            step_id="NVS-01",
            who="system",
            what_data="過去20年の日次株価データ",
            what_test="オフラインバックテスト",
            threshold="ベンチマーク対比の超過リターンが正",
            priority=NextValidationPriority.CRITICAL,
        ),
        NextValidationStep(
            step_id="NVS-02",
            who="system",
            what_data="バックテスト結果",
            what_test="ウォークフォワード検証",
            threshold="各期間の50%以上で正のリターン",
            priority=NextValidationPriority.HIGH,
        ),
    ]
