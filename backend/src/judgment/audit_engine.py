"""Minimal deterministic Audit Engine for v1 candidate judgment."""

from __future__ import annotations

import re

from src.domain.models import (
    Availability,
    Audit,
    AuditCategory,
    AuditIssue,
    AuditStatus,
    Candidate,
    ComparisonResult,
    EvidenceItem,
    EvidencePlan,
    GapSeverity,
    ImplementationComplexity,
    MetaAudit,
    MinimumEvidenceStandard,
    PlanCompleteness,
    PointInTimeStatus,
    QualityLossEstimate,
    RequirementLevel,
    ResearchSpec,
    Severity,
    TestResult,
    ValidationBurden,
    ValidationPlan,
)

_SPLIT_PATTERN = re.compile(
    r"[\s,./:;()\[\]{}<>「」『』【】（）・。]+|"
    r"(?:が|を|に|で|と|は|へ|から|まで|より|する|される|できる|ある|ない)"
)
_GENERIC_KEYWORDS = {
    "",
    "candidate",
    "data",
    "plan",
    "strategy",
    "test",
    "候補",
    "前提",
    "条件",
    "戦略",
    "検証",
    "必要",
    "可能",
    "成立",
    "有効",
}
_IDEALIZED_EXECUTION_KEYWORDS = (
    "zero slippage",
    "instant fill",
    "perfect execution",
    "unlimited liquidity",
    "ゼロスリッページ",
    "即時約定",
    "完全約定",
    "理想的な執行",
    "無制限の流動性",
)
_STRONG_LEAKAGE_KEYWORDS = (
    "future",
    "future information",
    "lookahead",
    "look-ahead",
    "survivorship",
    "leakage",
    "将来",
    "未来情報",
    "先読み",
    "後知恵",
    "リーク",
)
_WEAK_TEMPORAL_KEYWORDS = (
    "timing",
    "lag",
    "pit",
    "point in time",
    "temporal",
    "時点",
    "タイミング",
    "遅延",
)
_REALISM_BLOCKER_KEYWORDS = (
    "live trading",
    "real money",
    "broker",
    "broker api",
    "order routing",
    "real-time",
    "realtime",
    "intraday",
    "minute",
    "tick",
    "low latency",
    "streaming",
    "actual order",
    "live execution",
    "実注文",
    "発注",
    "約定",
    "ライブ取引",
    "リアルタイム",
    "分次",
    "ティック",
    "秒次",
    "低遅延",
    "ブローカー",
)
_REALISM_WARNING_KEYWORDS = (
    "manual",
    "discretionary",
    "continuous monitoring",
    "24/7",
    "human-in-the-loop",
    "hand-label",
    "custom vendor feed",
    "手動",
    "裁量",
    "常時監視",
    "24時間監視",
    "随時対応",
    "人手",
    "複数ベンダー",
)
_PROXY_KEYWORDS = ("synthetic", "fallback", "proxy", "代替", "代理", "合成")


def audit_candidates(
    research_spec: ResearchSpec,
    candidates: list[Candidate],
    evidence_plans: list[EvidencePlan],
    validation_plans: list[ValidationPlan],
    test_results: dict[str, TestResult] | None = None,
    statistical_tests: dict[str, list[TestResult]] | None = None,
    comparison_result: ComparisonResult | None = None,
) -> list[Audit]:
    """Audit every candidate using the minimum Round 4.1 rule set."""
    evidence_map = {plan.candidate_id: plan for plan in evidence_plans}
    validation_map = {plan.candidate_id: plan for plan in validation_plans}
    test_results = test_results or {}
    statistical_tests = statistical_tests or {}

    return [
        audit_candidate(
            candidate,
            evidence_map.get(candidate.candidate_id),
            validation_map.get(candidate.candidate_id),
            test_results.get(candidate.candidate_id),
            statistical_tests.get(candidate.candidate_id),
            comparison_result,
            research_spec=research_spec,
        )
        for candidate in candidates
    ]


def audit_candidate(
    candidate: Candidate,
    evidence_plan: EvidencePlan | None,
    validation_plan: ValidationPlan | None,
    test_result: TestResult | None = None,
    statistical_tests: list[TestResult] | None = None,
    comparison_result: ComparisonResult | None = None,
    research_spec: ResearchSpec | None = None,
) -> Audit:
    """Audit a single candidate."""
    issues: list[AuditIssue] = []

    issues.extend(_evidence_gap_issues(candidate, evidence_plan, validation_plan))
    issues.extend(_leakage_risk_issues(candidate, evidence_plan, test_result))
    issues.extend(_assumption_issues(candidate, evidence_plan, validation_plan, research_spec))
    issues.extend(_overfitting_risk_issues(candidate, test_result, statistical_tests or []))
    issues.extend(_execution_rejection_issues(candidate, comparison_result))
    issues.extend(_execution_evidence_issues(candidate, test_result, comparison_result))
    issues.extend(_realism_issues(candidate))
    issues.extend(_complexity_issues(candidate))

    audit_status = _derive_audit_status(issues)
    rejection_reason = _build_rejection_reason(candidate, issues)
    surviving_assumptions = _build_surviving_assumptions(candidate, audit_status, issues)
    residual_risks = _build_residual_risks(candidate, issues)

    return Audit(
        candidate_id=candidate.candidate_id,
        audit_status=audit_status,
        issues=issues,
        rejection_reason=rejection_reason,
        surviving_assumptions=surviving_assumptions,
        residual_risks=residual_risks,
        meta_audit=_build_meta_audit(issues),
    )


def _evidence_gap_issues(
    candidate: Candidate,
    evidence_plan: EvidencePlan | None,
    validation_plan: ValidationPlan | None,
) -> list[AuditIssue]:
    if evidence_plan is None:
        return [
            _issue(
                candidate,
                "evd-missing",
                Severity.HIGH,
                AuditCategory.EVIDENCE_GAP,
                "エビデンス計画が不足している",
                "この候補に対応するエビデンス計画が見つからないため、監査は計画の完全性を確認できません。",
            )
        ]

    coverage = evidence_plan.coverage_metrics
    issues: list[AuditIssue] = []

    if evidence_plan.gap_severity == GapSeverity.BLOCKING:
        issues.append(
            _issue(
                candidate,
                "evd-blocking",
                Severity.CRITICAL,
                AuditCategory.EVIDENCE_GAP,
                "必須エビデンスにブロッキングギャップがある",
                "必須エビデンスが不足しており、v1の投資検証として承認前に成立しません。",
                disqualifying=True,
                mitigation="不足している必須データを満たす別候補に切り替えるか、再設計して再検証します。",
                affected_evidence_items=[gap.gap_id for gap in evidence_plan.critical_gaps],
            )
        )
        return issues

    incomplete_coverage = (
        coverage.required_total > 0
        and coverage.required_available < coverage.required_total
    )
    incomplete_validation = (
        validation_plan is not None
        and validation_plan.plan_completeness != PlanCompleteness.COMPLETE
    )

    if evidence_plan.gap_severity == GapSeverity.MANAGEABLE or incomplete_coverage or incomplete_validation:
        issues.append(
            _issue(
                candidate,
                "evd-manageable",
                Severity.HIGH if incomplete_validation else Severity.MEDIUM,
                AuditCategory.EVIDENCE_GAP,
                "検証カバレッジが十分ではない",
                "必要データまたは検証計画に残存ギャップがあり、この候補は警告付きでのみ扱えます。",
                mitigation="不足データの補完またはテスト計画の拡張後に再監査します。",
                affected_evidence_items=[item.item_id for item in evidence_plan.evidence_items],
            )
        )

    return issues


def _assumption_issues(
    candidate: Candidate,
    evidence_plan: EvidencePlan | None,
    validation_plan: ValidationPlan | None,
    research_spec: ResearchSpec | None,
) -> list[AuditIssue]:
    if not candidate.core_assumptions:
        return []

    validation_text = _join_validation_text(validation_plan)
    evidence_items = evidence_plan.evidence_items if evidence_plan else []
    unsupported = []
    weak_evidence: list[tuple] = []
    conflicting = []
    idealized = []

    for assumption in candidate.core_assumptions:
        keywords = _extract_keywords(assumption.statement)
        supporting_items = _matching_evidence_items(evidence_items, assumption.statement, keywords)
        validation_covered = _text_covers_statement(validation_text, assumption.statement, keywords)

        if not validation_covered:
            unsupported.append(assumption)

        if supporting_items and all(_is_weak_evidence_item(item) for item in supporting_items):
            weak_evidence.append((assumption, supporting_items))

        if research_spec:
            assumption_text = assumption.statement.lower()
            assumption_keywords = _extract_keywords(assumption_text)
            for forbidden in research_spec.constraints.forbidden_behaviors:
                if not forbidden:
                    continue
                forbidden_lower = forbidden.lower()
                forbidden_keywords = _extract_keywords(forbidden_lower)
                if forbidden_lower in assumption_text or any(
                    keyword in assumption_text for keyword in forbidden_keywords
                ) or any(
                    keyword in forbidden_lower for keyword in assumption_keywords
                ):
                    conflicting.append(assumption)
                    break

        if _matches_any_phrase(assumption.statement, _IDEALIZED_EXECUTION_KEYWORDS):
            idealized.append(assumption)

    issues: list[AuditIssue] = []

    if conflicting:
        issues.append(
            _issue(
                candidate,
                "asm-conflict",
                Severity.CRITICAL,
                AuditCategory.ASSUMPTION,
                "中核前提が明示制約と衝突している",
                (
                    f"前提 {_summarize_assumptions(conflicting)} が、ユーザーまたは仕様で禁止された条件に依存しています。"
                    "この候補は承認前提を満たしません。"
                ),
                mitigation="制約に抵触しない前提へ置き換えるか、別候補を採用します。",
                disqualifying=True,
                affected_assumptions=[assumption.assumption_id for assumption in conflicting],
            )
        )

    if unsupported:
        strong_evidence_bar = (
            research_spec is not None
            and research_spec.validation_requirements.minimum_evidence_standard
            == MinimumEvidenceStandard.STRONG
        )
        issues.append(
            _issue(
                candidate,
                "asm-coverage",
                Severity.HIGH if len(unsupported) >= 2 or strong_evidence_bar else Severity.MEDIUM,
                AuditCategory.ASSUMPTION,
                "中核前提の検証カバレッジが不足している",
                (
                    f"前提 {_summarize_assumptions(unsupported)} が検証計画の失敗条件や手順に十分反映されていません。"
                    "前提を検証できない候補は見かけ上まとまっていても推奨品質が弱くなります。"
                ),
                mitigation="未検証の前提を直接反証できるテストまたは検証条件を追加します。",
                disqualifying=len(unsupported) >= 3,
                affected_assumptions=[assumption.assumption_id for assumption in unsupported],
            )
        )

    if weak_evidence:
        issues.append(
            _issue(
                candidate,
                "asm-weak-evidence",
                Severity.HIGH if len(weak_evidence) >= 2 else Severity.MEDIUM,
                AuditCategory.ASSUMPTION,
                "中核前提を支えるエビデンスが弱い",
                (
                    f"前提 {_summarize_assumptions([assumption for assumption, _ in weak_evidence])} は、"
                    "取得難度・時点整合性・代理品質に難のあるエビデンスへ強く依存しています。"
                ),
                mitigation="対象前提を支える必須データを改善し、弱い代理エビデンスへの依存を下げます。",
                affected_evidence_items=[
                    item.item_id
                    for _, items in weak_evidence
                    for item in items
                ],
                affected_assumptions=[
                    assumption.assumption_id
                    for assumption, _ in weak_evidence
                ],
            )
        )

    if idealized:
        issues.append(
            _issue(
                candidate,
                "asm-idealized-execution",
                Severity.MEDIUM,
                AuditCategory.ASSUMPTION,
                "理想化された執行条件に依存している",
                (
                    f"前提 {_summarize_assumptions(idealized)} は、"
                    "スリッページ無視や完全約定のような理想条件を暗黙に置いています。"
                ),
                mitigation="Paper Runで再現可能な日次・T+1前提へ置き換えます。",
                affected_assumptions=[assumption.assumption_id for assumption in idealized],
            )
        )

    return issues


def _execution_rejection_issues(
    candidate: Candidate,
    comparison_result: ComparisonResult | None,
) -> list[AuditIssue]:
    if comparison_result is None:
        return []

    issues: list[AuditIssue] = []
    for rejection in comparison_result.execution_based_rejections:
        if rejection.candidate_id != candidate.candidate_id:
            continue
        issues.append(
            _issue(
                candidate,
                "exec-reject",
                Severity.HIGH,
                AuditCategory.REALISM,
                "実行検証で不合格基準に抵触した",
                f"比較結果でこの候補は棄却対象と判定されました。理由: {rejection.reason}",
                disqualifying=True,
                mitigation="実行結果で崩れた前提を見直し、別の候補として再生成します。",
            )
        )
    return issues


def _overfitting_risk_issues(
    candidate: Candidate,
    test_result: TestResult | None,
    statistical_tests: list[TestResult],
) -> list[AuditIssue]:
    if test_result is None:
        return []

    oos_test = _find_stat_test(statistical_tests, "oos_is_sharpe_ratio")
    significance_tests = [
        stat_test
        for stat_test in statistical_tests
        if any(metric.statistical_significance is not None for metric in stat_test.metrics_results)
    ]

    issues: list[AuditIssue] = []
    missing_artifacts: list[str] = []

    if oos_test is None:
        missing_artifacts.append("OOS比較")
    if not significance_tests:
        missing_artifacts.append("有意性検定")

    if missing_artifacts:
        issues.append(
            _issue(
                candidate,
                "ovf-thin",
                Severity.MEDIUM,
                AuditCategory.OVERFITTING_RISK,
                "過学習リスクを判断する証拠が薄い",
                (
                    f"{'・'.join(missing_artifacts)} の結果が不足しており、"
                    "見かけ上の適合と汎化性能の差を十分に確認できません。"
                ),
                mitigation="OOS比較と有意性検定を揃えたうえで再監査します。",
            )
        )
        return issues

    if oos_test.execution_status.value != "completed" or not oos_test.metrics_results:
        issues.append(
            _issue(
                candidate,
                "ovf-oos-thin",
                Severity.MEDIUM,
                AuditCategory.OVERFITTING_RISK,
                "OOS証拠が薄く過学習リスクを強く判断できない",
                "アウトオブサンプル比較が部分的または不十分で、過学習の有無を強く結論づけられません。",
                mitigation="十分なサンプル長でOOS比較を再実行します。",
            )
        )
        return issues

    in_sample_sharpe = _metric_value(oos_test, "in_sample_sharpe")
    out_of_sample_sharpe = _metric_value(oos_test, "out_of_sample_sharpe")
    ratio = _metric_value(oos_test, "oos_is_sharpe_ratio")

    if in_sample_sharpe is None or out_of_sample_sharpe is None or ratio is None:
        issues.append(
            _issue(
                candidate,
                "ovf-oos-missing-metrics",
                Severity.MEDIUM,
                AuditCategory.OVERFITTING_RISK,
                "OOS比較の指標が不足している",
                "インサンプルとアウトオブサンプルの比較指標が揃っておらず、過学習リスクの強い判断ができません。",
                mitigation="OOS比較指標を揃えて再実行します。",
            )
        )
        return issues

    if in_sample_sharpe >= 0.75 and (out_of_sample_sharpe <= 0 or ratio < 0.35):
        issues.append(
            _issue(
                candidate,
                "ovf-collapse",
                Severity.CRITICAL,
                AuditCategory.OVERFITTING_RISK,
                "OOSで性能が崩れており過学習リスクが高い",
                (
                    f"インサンプルのSharpe {in_sample_sharpe:.2f} に対して、"
                    f"アウトオブサンプルのSharpe {out_of_sample_sharpe:.2f}、"
                    f"OOS/IS比 {ratio:.2f} と大きく崩れており、"
                    "見かけ上の適合が外部期間へ持ち越されていません。"
                ),
                mitigation="特徴量やルールの自由度を下げ、OOSで再検証します。",
                disqualifying=True,
            )
        )
    elif in_sample_sharpe > 0 and (
        oos_test.overall_result.value in {"mixed", "fail"}
        or ratio < 0.5
        or out_of_sample_sharpe <= 0
    ):
        issues.append(
            _issue(
                candidate,
                "ovf-warning",
                Severity.HIGH if ratio < 0.35 else Severity.MEDIUM,
                AuditCategory.OVERFITTING_RISK,
                "OOSで性能低下が見られ過学習懸念が残る",
                (
                    f"インサンプルのSharpe {in_sample_sharpe:.2f} に対して、"
                    f"アウトオブサンプルのSharpe {out_of_sample_sharpe:.2f}、"
                    f"OOS/IS比 {ratio:.2f} で、汎化性能に注意が必要です。"
                ),
                mitigation="OOS期間を増やすか、複雑性を下げた候補と比較します。",
            )
        )

    weak_significance = [
        stat_test
        for stat_test in significance_tests
        if stat_test.execution_status.value != "completed"
        or stat_test.overall_result.value in {"mixed", "inconclusive"}
        or any(p_value >= 0.05 for p_value in _significance_pvalues(stat_test))
    ]
    if weak_significance:
        issues.append(
            _issue(
                candidate,
                "ovf-significance",
                Severity.MEDIUM,
                AuditCategory.OVERFITTING_RISK,
                "統計的有意性が弱く過学習懸念を十分に払拭できない",
                (
                    f"{len(weak_significance)}件の有意性検定が弱いまたは不確定で、"
                    "見かけ上の成績が偶然でないと断言できません。"
                ),
                mitigation="サンプルを増やし、OOS結果と合わせて再評価します。",
            )
        )

    return issues


def _execution_evidence_issues(
    candidate: Candidate,
    test_result: TestResult | None,
    comparison_result: ComparisonResult | None,
) -> list[AuditIssue]:
    if comparison_result is None or test_result is None:
        return [
            _issue(
                candidate,
                "exec-missing",
                Severity.MEDIUM,
                AuditCategory.RECOMMENDATION_RISK,
                "実行エビデンスが未充足",
                "バックテストまたは候補比較の結果が不足しているため、この候補は計画段階の根拠に強く依存しています。",
                mitigation="実行レイヤーが利用可能な環境で再実行し、比較結果を補完します。",
            )
        ]

    if test_result.execution_status.value != "completed" or test_result.overall_result.value in {"mixed", "inconclusive"}:
        return [
            _issue(
                candidate,
                "exec-weak",
                Severity.MEDIUM,
                AuditCategory.RECOMMENDATION_RISK,
                "実行エビデンスが弱い",
                "実行結果が完了済みでも、結論が混合または不確定のため、承認判断の根拠としては弱い状態です。",
                mitigation="追加の実行検証または代替候補との比較を行います。",
            )
        ]

    return []


def _leakage_risk_issues(
    candidate: Candidate,
    evidence_plan: EvidencePlan | None,
    test_result: TestResult | None,
) -> list[AuditIssue]:
    if evidence_plan is None:
        return []

    required_items = [
        item for item in evidence_plan.evidence_items
        if item.requirement_level == RequirementLevel.REQUIRED
    ]
    strong_items = [item for item in required_items if _is_strong_leakage_item(item)]
    weak_items = [
        item for item in required_items
        if item not in strong_items and _is_weak_temporal_item(item)
    ]
    proxy_items = [item for item in required_items if _is_proxy_or_synthetic_like(item)]

    issues: list[AuditIssue] = []

    if strong_items:
        issues.append(
            _issue(
                candidate,
                "lkg-strong",
                Severity.CRITICAL,
                AuditCategory.LEAKAGE_RISK,
                "将来情報に依存する疑いが強い",
                (
                    f"必須エビデンス {_summarize_items(strong_items)} は時点整合性が欠けており、"
                    "将来時点の情報を参照している可能性が高い状態です。"
                ),
                mitigation="Point-in-timeで取得可能なデータへ差し替え、汚染された特徴量を除外します。",
                disqualifying=True,
                affected_evidence_items=[item.item_id for item in strong_items],
            )
        )

    if weak_items:
        issues.append(
            _issue(
                candidate,
                "lkg-weak",
                Severity.MEDIUM,
                AuditCategory.LEAKAGE_RISK,
                "時点整合性が弱いエビデンスが残っている",
                (
                    f"必須エビデンス {_summarize_items(weak_items)} は、"
                    "利用時点や報告遅延の扱いが曖昧で、時間方向の妥当性が十分に固まっていません。"
                ),
                mitigation="利用可能時点と報告ラグを明示し、PIT前提を監査可能にします。",
                affected_evidence_items=[item.item_id for item in weak_items],
            )
        )

    if proxy_items:
        issues.append(
            _issue(
                candidate,
                "lkg-proxy",
                Severity.MEDIUM,
                AuditCategory.LEAKAGE_RISK,
                "代理・代替エビデンスを本証拠として扱っている",
                (
                    f"必須エビデンス {_summarize_items(proxy_items)} は、"
                    "代理データや品質劣化を伴う代替ソースへの依存が残っています。"
                ),
                mitigation="代理ソースの品質劣化を明示し、本来の検証データで置き換えます。",
                affected_evidence_items=[item.item_id for item in proxy_items],
            )
        )

    if test_result is not None and _has_test_flag(test_result, _STRONG_LEAKAGE_KEYWORDS):
        issues.append(
            _issue(
                candidate,
                "lkg-test-flag",
                Severity.HIGH,
                AuditCategory.LEAKAGE_RISK,
                "実行結果が時系列汚染を示唆している",
                "テスト結果の品質フラグに将来情報・リーク関連のシグナルが含まれており、比較品質を信頼できません。",
                mitigation="該当テストの特徴量定義と時系列分割を見直して再実行します。",
                disqualifying=True,
            )
        )

    if test_result is not None and _has_test_flag(test_result, _PROXY_KEYWORDS):
        issues.append(
            _issue(
                candidate,
                "lkg-synthetic",
                Severity.MEDIUM,
                AuditCategory.LEAKAGE_RISK,
                "代替データの扱いに慎重さが必要",
                "テスト結果が合成・フォールバック系のデータ利用を示しており、本来の市場エビデンスと同等には扱えません。",
                mitigation="本番相当の市場データで再検証し、代替データは警告付きで扱います。",
            )
        )

    return issues


def _realism_issues(candidate: Candidate) -> list[AuditIssue]:
    text = _candidate_operational_text(candidate)
    blocker_hits = _matched_phrases(text, _REALISM_BLOCKER_KEYWORDS)
    fragility_hits = _matched_phrases(text, _REALISM_WARNING_KEYWORDS)

    issues: list[AuditIssue] = []

    if blocker_hits:
        issues.append(
            _issue(
                candidate,
                "rlm-unsupported",
                Severity.CRITICAL,
                AuditCategory.REALISM,
                "v1で未対応の運用能力に依存している",
                (
                    f"候補の要件に {_format_hits(blocker_hits)} が含まれており、"
                    "Paper Run only・日次・承認後実行というv1境界の外に出ています。"
                ),
                mitigation="日次データ・Paper Run前提で再現可能な候補に置き換えます。",
                disqualifying=True,
            )
        )

    if fragility_hits:
        issues.append(
            _issue(
                candidate,
                "rlm-fragile",
                Severity.HIGH if len(fragility_hits) >= 2 else Severity.MEDIUM,
                AuditCategory.REALISM,
                "v1で運用するには監視・手作業依存が強い",
                (
                    f"候補の説明に {_format_hits(fragility_hits)} が含まれており、"
                    "現行v1のパッケージ化された運用よりも人手依存が強い構成です。"
                ),
                mitigation="監視頻度や手動判断を減らし、日次のPaper Runに収まる形へ縮退します。",
            )
        )

    return issues


def _complexity_issues(candidate: Candidate) -> list[AuditIssue]:
    if (
        candidate.validation_burden != ValidationBurden.HIGH
        and candidate.implementation_complexity != ImplementationComplexity.HIGH
    ):
        return []

    severity = (
        Severity.HIGH
        if candidate.validation_burden == ValidationBurden.HIGH
        and candidate.implementation_complexity == ImplementationComplexity.HIGH
        else Severity.MEDIUM
    )
    return [
        _issue(
            candidate,
            "complexity-warning",
            severity,
            AuditCategory.COMPLEXITY,
            "v1で扱うには運用負荷が高い",
            "この候補は検証負担または実装複雑性が高く、v1の投資特化スコープでは運用リスクが残ります。",
            mitigation="より単純な候補を優先し、この候補は警告付きで扱います。",
        )
    ]


def _derive_audit_status(issues: list[AuditIssue]) -> AuditStatus:
    if any(issue.disqualifying for issue in issues):
        return AuditStatus.REJECTED
    if issues:
        return AuditStatus.PASSED_WITH_WARNINGS
    return AuditStatus.PASSED


def _build_rejection_reason(candidate: Candidate, issues: list[AuditIssue]) -> str | None:
    disqualifying = [issue for issue in issues if issue.disqualifying]
    if not disqualifying:
        return None

    details = " ".join(issue.explanation for issue in disqualifying)
    return (
        f"{candidate.name} は棄却されました。{details} "
        "この問題は承認前に解消されておらず、v1の投資検証として採用できません。"
    )


def _build_surviving_assumptions(
    candidate: Candidate,
    status: AuditStatus,
    issues: list[AuditIssue],
) -> list[str]:
    if status == AuditStatus.REJECTED:
        return []

    invalidated = {
        assumption_id
        for issue in issues
        if issue.disqualifying and issue.category == AuditCategory.ASSUMPTION
        for assumption_id in issue.affected_assumptions
    }
    assumptions = [
        assumption.statement
        for assumption in candidate.core_assumptions
        if assumption.assumption_id not in invalidated
    ]
    return assumptions or [candidate.summary]


def _build_residual_risks(candidate: Candidate, issues: list[AuditIssue]) -> list[str]:
    values: list[str] = []
    for issue in issues:
        if issue.disqualifying:
            continue
        values.append(issue.title)
    values.extend(candidate.known_risks)

    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped[:3]


def _build_meta_audit(issues: list[AuditIssue]) -> MetaAudit:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in issues:
        counts[issue.severity.value] += 1
    return MetaAudit(
        total_issues=len(issues),
        issues_by_severity=counts,
        zero_issue_flag=len(issues) == 0,
        compound_patterns_detected=[],
    )


def _issue(
    candidate: Candidate,
    suffix: str,
    severity: Severity,
    category: AuditCategory,
    title: str,
    explanation: str,
    *,
    mitigation: str | None = None,
    disqualifying: bool = False,
    affected_evidence_items: list[str] | None = None,
    affected_assumptions: list[str] | None = None,
) -> AuditIssue:
    return AuditIssue(
        issue_id=f"{candidate.candidate_id}-{suffix}",
        severity=severity,
        category=category,
        title=title,
        explanation=explanation,
        mitigation=mitigation,
        disqualifying=disqualifying,
        affected_evidence_items=affected_evidence_items or [],
        affected_assumptions=affected_assumptions or [],
        compound_pattern=None,
    )


def _join_validation_text(validation_plan: ValidationPlan | None) -> str:
    if validation_plan is None:
        return ""

    fragments: list[str] = []
    for test in validation_plan.test_sequence:
        fragments.extend([test.purpose, test.method_summary, *test.failure_conditions])
    return " ".join(fragment.lower() for fragment in fragments if fragment)


def _extract_keywords(text: str) -> list[str]:
    values: list[str] = []
    for raw in _SPLIT_PATTERN.split(text.lower()):
        token = raw.strip()
        if len(token) < 2 or token in _GENERIC_KEYWORDS:
            continue
        if token not in values:
            values.append(token)
    return values


def _text_covers_statement(text: str, statement: str, keywords: list[str]) -> bool:
    statement_lower = statement.lower()
    if statement_lower and statement_lower in text:
        return True
    return any(keyword in text for keyword in keywords)


def _matching_evidence_items(
    evidence_items: list[EvidenceItem],
    statement: str,
    keywords: list[str],
) -> list[EvidenceItem]:
    statement_lower = statement.lower()
    matches: list[EvidenceItem] = []
    for item in evidence_items:
        blob = " ".join([
            item.description,
            *item.quality_concerns,
            *item.known_biases,
            *item.leakage_risk_patterns,
            item.proxy_option.description if item.proxy_option else "",
        ]).lower()
        if statement_lower and statement_lower in blob:
            matches.append(item)
            continue
        if any(keyword in blob for keyword in keywords):
            matches.append(item)
    return matches


def _is_weak_evidence_item(item: EvidenceItem) -> bool:
    if item.availability != Availability.AVAILABLE:
        return True
    if item.point_in_time_status != PointInTimeStatus.FULL and item.category.value not in {"price", "metadata"}:
        return True
    if item.proxy_option and item.proxy_option.quality_loss_estimate != QualityLossEstimate.MINIMAL:
        return True
    return False


def _is_strong_leakage_item(item: EvidenceItem) -> bool:
    blob = " ".join([
        item.description,
        *item.quality_concerns,
        *item.known_biases,
        *item.leakage_risk_patterns,
    ]).lower()
    if item.point_in_time_status == PointInTimeStatus.NONE:
        return True
    return any(keyword in blob for keyword in _STRONG_LEAKAGE_KEYWORDS)


def _is_weak_temporal_item(item: EvidenceItem) -> bool:
    blob = " ".join([
        item.description,
        *item.quality_concerns,
        *item.known_biases,
        *item.leakage_risk_patterns,
    ]).lower()
    if item.point_in_time_status == PointInTimeStatus.PARTIAL and item.category.value not in {"price", "metadata"}:
        return True
    if item.reporting_lag_days is None and item.category.value in {"fundamental", "macro", "sentiment", "alternative"}:
        return True
    return any(keyword in blob for keyword in _WEAK_TEMPORAL_KEYWORDS)


def _is_proxy_or_synthetic_like(item: EvidenceItem) -> bool:
    blob = " ".join([
        item.description,
        *item.quality_concerns,
        item.proxy_option.description if item.proxy_option else "",
    ]).lower()
    if item.proxy_option and item.proxy_option.quality_loss_estimate != QualityLossEstimate.MINIMAL:
        return True
    return any(keyword in blob for keyword in _PROXY_KEYWORDS)


def _has_test_flag(test_result: TestResult, keywords: tuple[str, ...]) -> bool:
    blob = " ".join(test_result.data_quality_flags).lower()
    return any(keyword in blob for keyword in keywords)


def _find_stat_test(statistical_tests: list[TestResult], metric_name: str) -> TestResult | None:
    for stat_test in statistical_tests:
        if any(metric.metric_name == metric_name for metric in stat_test.metrics_results):
            return stat_test
    return None


def _metric_value(test_result: TestResult, metric_name: str) -> float | None:
    for metric in test_result.metrics_results:
        if metric.metric_name == metric_name:
            return metric.actual_value
    return None


def _significance_pvalues(test_result: TestResult) -> list[float]:
    values: list[float] = []
    for metric in test_result.metrics_results:
        if metric.statistical_significance and metric.statistical_significance.p_value is not None:
            values.append(metric.statistical_significance.p_value)
    return values


def _candidate_operational_text(candidate: Candidate) -> str:
    return " ".join(
        [
            candidate.summary,
            *candidate.architecture_outline,
            *candidate.required_inputs,
            *candidate.expected_strengths,
            *candidate.expected_weaknesses,
            *candidate.known_risks,
            *(assumption.statement for assumption in candidate.core_assumptions),
        ]
    ).lower()


def _matches_any_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _matched_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]


def _summarize_assumptions(assumptions: list) -> str:
    statements = [assumption.statement for assumption in assumptions[:2]]
    if len(assumptions) > 2:
        statements.append(f"他{len(assumptions) - 2}件")
    return " / ".join(statements)


def _summarize_items(items: list[EvidenceItem]) -> str:
    descriptions = [item.description for item in items[:2]]
    if len(items) > 2:
        descriptions.append(f"他{len(items) - 2}件")
    return " / ".join(descriptions)


def _format_hits(hits: list[str]) -> str:
    unique = []
    for hit in hits:
        if hit not in unique:
            unique.append(hit)
    return " / ".join(unique[:3])
