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
    Audit,
    AuditCategory,
    AuditStatus,
    Candidate,
    CandidateType,
    ComparisonResult,
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
    audits: list[Audit] | None = None,
    comparison_result: ComparisonResult | None = None,
) -> Recommendation:
    """
    Build a Recommendation from planning outputs.

    Selects best + runner_up candidates. Rejects the rest.
    Produces ranking logic, open unknowns, critical conditions,
    confidence label, and expiry.
    """
    if not candidates:
        raise ValueError("Cannot build recommendation with zero candidates")

    audit_map = {audit.candidate_id: audit for audit in audits or []}
    eligible_candidates, rejected_candidate_ids = _partition_candidates(candidates, audit_map)

    # 1. Score and rank candidates
    eligible_evidence_plans = [
        plan for plan in evidence_plans
        if plan.candidate_id in {candidate.candidate_id for candidate in eligible_candidates}
    ]
    eligible_validation_plans = [
        plan for plan in validation_plans
        if plan.candidate_id in {candidate.candidate_id for candidate in eligible_candidates}
    ]
    scored = _score_candidates(eligible_candidates, eligible_evidence_plans, eligible_validation_plans)
    planning_ranked = [candidate for candidate, _ in sorted(scored, key=lambda x: x[1], reverse=True)]
    ranked_candidates = _rank_candidates(
        planning_ranked,
        eligible_candidates,
        comparison_result,
    )

    best_candidate = ranked_candidates[0] if ranked_candidates else None
    runner_up = ranked_candidates[1] if len(ranked_candidates) > 1 else None
    rejected = ranked_candidates[2:]
    rejected_candidate_ids.extend(
        candidate.candidate_id for candidate in rejected
        if candidate.candidate_id not in rejected_candidate_ids
    )

    # 2. Build ranking logic (min 3 axes)
    ranking_logic = _build_ranking_logic(
        best_candidate,
        runner_up,
        scored,
        audits,
        comparison_result=comparison_result,
    )

    # 3. Build open unknowns (min 1)
    open_unknowns = _build_open_unknowns(research_spec, evidence_plans)

    # 4. Build critical conditions (min 1)
    critical_conditions = _build_critical_conditions(research_spec, best_candidate, audits)

    # 5. Derive confidence label
    base_confidence = ConfidenceLabel.LOW
    if not eligible_candidates:
        confidence = ConfidenceLabel.LOW
    else:
        base_confidence = _derive_confidence(
            research_spec.validation_requirements.minimum_evidence_standard,
            eligible_evidence_plans,
            eligible_validation_plans,
        )
        confidence = _degrade_confidence_from_audit(
            base_confidence,
            audit_map.get(best_candidate.candidate_id) if best_candidate else None,
        )

    # 6. Expiry
    expiry = RecommendationExpiry(
        type=ExpiryType.TIME_BASED,
        description="3ヶ月後に自動で再評価します。市場環境の変化により、推奨が変わる可能性があります。",
        expiry_trigger="quarterly_re_evaluation",
    )

    # 7. Next validation steps
    next_steps = _build_next_steps(research_spec, audits)

    return Recommendation(
        run_id=run_id,
        best_candidate_id=best_candidate.candidate_id if best_candidate else None,
        runner_up_candidate_id=runner_up.candidate_id if runner_up else None,
        rejected_candidate_ids=rejected_candidate_ids,
        ranking_logic=ranking_logic,
        open_unknowns=open_unknowns,
        critical_conditions=critical_conditions,
        confidence_label=confidence,
        confidence_explanation=_confidence_explanation(
            confidence,
            has_survivors=bool(eligible_candidates),
            degraded_for_audit=bool(best_candidate and confidence != base_confidence),
        ),
        next_validation_steps=next_steps,
        recommendation_expiry=expiry,
    )


def _partition_candidates(
    candidates: list[Candidate],
    audit_map: dict[str, Audit],
) -> tuple[list[Candidate], list[str]]:
    if not audit_map:
        return candidates, []

    eligible: list[Candidate] = []
    rejected_ids: list[str] = []
    for candidate in candidates:
        audit = audit_map.get(candidate.candidate_id)
        if audit and audit.audit_status == AuditStatus.REJECTED:
            rejected_ids.append(candidate.candidate_id)
            continue
        eligible.append(candidate)
    return eligible, rejected_ids


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


def _rank_candidates(
    planning_ranked: list[Candidate],
    eligible_candidates: list[Candidate],
    comparison_result: ComparisonResult | None,
) -> list[Candidate]:
    if not comparison_result:
        return planning_ranked

    candidate_map = {candidate.candidate_id: candidate for candidate in eligible_candidates}
    execution_ranking = comparison_result.execution_based_ranking
    preferred_ids = [
        candidate_id
        for candidate_id in (
            execution_ranking.recommended_best,
            execution_ranking.recommended_runner_up,
        )
        if candidate_id in candidate_map
    ]
    if not preferred_ids:
        return planning_ranked

    ranked: list[Candidate] = []
    seen: set[str] = set()
    for candidate_id in preferred_ids:
        if candidate_id in seen:
            continue
        ranked.append(candidate_map[candidate_id])
        seen.add(candidate_id)

    for candidate in planning_ranked:
        if candidate.candidate_id in seen:
            continue
        ranked.append(candidate)
        seen.add(candidate.candidate_id)

    return ranked


def _build_ranking_logic(
    best: Candidate | None,
    runner_up: Candidate | None,
    scored: list[tuple[Candidate, float]],
    audits: list[Audit] | None = None,
    comparison_result: ComparisonResult | None = None,
) -> list[RankingLogicItem]:
    """Build ranking rationale (min 3 axes)."""
    if best is None:
        rejected = len([audit for audit in audits or [] if audit.audit_status == AuditStatus.REJECTED])
        return [
            RankingLogicItem(
                comparison_axis="監査結果",
                best_assessment="該当なし",
                runner_up_assessment="該当なし",
                verdict=f"監査の結果、提示可能な候補がありません（棄却 {rejected} 件）。",
            ),
            RankingLogicItem(
                comparison_axis="エビデンス充足",
                best_assessment="該当なし",
                runner_up_assessment="該当なし",
                verdict="最低限のエビデンス条件を満たす候補が残りませんでした。",
            ),
            RankingLogicItem(
                comparison_axis="運用実現性",
                best_assessment="該当なし",
                runner_up_assessment="該当なし",
                verdict="v1の運用条件内で承認可能な候補がありません。",
            ),
        ]

    runner_up_name = runner_up.name if runner_up else "該当なし"

    items: list[RankingLogicItem] = []
    if comparison_result and _execution_ranking_available(best, comparison_result):
        items.extend(_build_execution_ranking_items(best, runner_up, comparison_result))

    items.extend([
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
    ])

    return items[:3]


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
    spec: ResearchSpec, best: Candidate | None, audits: list[Audit] | None = None
) -> list[CriticalCondition]:
    """Build critical conditions (min 1)."""
    if best is None:
        return [
            CriticalCondition(
                condition_id="CC-01",
                statement="監査で棄却された論点を解消し、少なくとも1候補を監査通過状態に戻すこと",
                verification_method="不足エビデンスの補完と候補の再検証",
                verification_timing="新しい候補提示の前",
                source="audit",
            )
        ]

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


def _degrade_confidence_from_audit(
    confidence: ConfidenceLabel,
    audit: Audit | None,
) -> ConfidenceLabel:
    if audit is None or confidence == ConfidenceLabel.LOW:
        return confidence

    high_material_categories = {AuditCategory.RECOMMENDATION_RISK, AuditCategory.OVERFITTING_RISK}
    has_high_material_warning = any(
        issue.severity.value in {"high", "critical"}
        and issue.category in high_material_categories
        and not issue.disqualifying
        for issue in audit.issues
    )
    material_warning_count = sum(
        1
        for issue in audit.issues
        if not issue.disqualifying
        and (
            issue.severity.value in {"high", "critical"}
            or (
                issue.category in high_material_categories
                and issue.severity.value == "medium"
            )
        )
    )
    if has_high_material_warning or material_warning_count >= 2:
        return ConfidenceLabel.LOW
    return confidence


def _confidence_explanation(
    confidence: ConfidenceLabel,
    has_survivors: bool = True,
    degraded_for_audit: bool = False,
) -> str:
    """Generate confidence explanation. No false confidence."""
    if not has_survivors:
        return "監査で承認可能な候補が残っていないため、現時点で推奨を提示できない。追加の検証または候補の再設計が必要。"
    if confidence == ConfidenceLabel.LOW and degraded_for_audit:
        return "実行比較の結果はあるが、選択候補に実行根拠や過学習懸念の警告が残っているため、現時点の信頼度は低い。追加検証で推奨が変わる可能性がある。"

    explanations = {
        ConfidenceLabel.LOW: "計画段階の評価のみに基づいており、バックテスト未実施。エビデンスのギャップがあるため、信頼度は低い。",
        ConfidenceLabel.MEDIUM: "計画段階の評価では妥当だが、バックテストによる実証は未完了。過去データでの検証後に信頼度が変わる可能性がある。",
        ConfidenceLabel.HIGH: "計画段階および実行段階の検証を通過。ただし、過去の実績は将来の成果を保証しない。",
    }
    return explanations[confidence]


def _execution_ranking_available(
    best: Candidate,
    comparison_result: ComparisonResult,
) -> bool:
    return comparison_result.execution_based_ranking.recommended_best == best.candidate_id


def _build_execution_ranking_items(
    best: Candidate,
    runner_up: Candidate | None,
    comparison_result: ComparisonResult,
) -> list[RankingLogicItem]:
    runner_up_name = runner_up.name if runner_up else "該当なし"
    rationale = comparison_result.execution_based_ranking.ranking_rationale
    if not rationale:
        return [
            RankingLogicItem(
                comparison_axis="実行比較",
                best_assessment=f"{best.name}: 実行比較で推奨",
                runner_up_assessment=f"{runner_up_name}: 実行比較で次点" if runner_up else "該当なし",
                verdict="監査通過候補の中では実行比較を優先して順位づけしました。",
            )
        ]

    items: list[RankingLogicItem] = []
    for reason in rationale[:2]:
        best_text = f"{best.name}: {'優位' if reason.winner == best.candidate_id else '劣後'}"
        runner_text = (
            f"{runner_up_name}: {'優位' if runner_up and reason.winner == runner_up.candidate_id else '劣後'}"
            if runner_up else "該当なし"
        )
        items.append(
            RankingLogicItem(
                comparison_axis=f"実行比較/{reason.comparison_axis}",
                best_assessment=best_text,
                runner_up_assessment=runner_text,
                verdict=f"{reason.winner} が {reason.margin} 差で優位",
            )
        )
    return items


def _build_next_steps(
    spec: ResearchSpec,
    audits: list[Audit] | None = None,
) -> list[NextValidationStep]:
    """Build next validation steps."""
    if audits and all(audit.audit_status == AuditStatus.REJECTED for audit in audits):
        return [
            NextValidationStep(
                step_id="NVS-01",
                who="system",
                what_data="不足している必須エビデンス",
                what_test="棄却理由を解消したうえで再監査",
                threshold="少なくとも1候補が監査で rejected 以外になること",
                priority=NextValidationPriority.CRITICAL,
            )
        ]

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
