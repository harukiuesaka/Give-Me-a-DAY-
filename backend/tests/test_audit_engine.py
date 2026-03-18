"""Focused tests for the Round 4 Audit Engine."""

from src.domain.models import (
    AuditCategory,
    AuditStatus,
    Availability,
    Candidate,
    CandidateAssumption,
    CandidateMetricValue,
    CandidateType,
    ComparisonMatrixData,
    ComparisonMetric,
    ComparisonResult,
    Constraints,
    CoverageMetrics,
    EvidenceCategory,
    EvidenceItem,
    EvidencePlan,
    ExecutionBasedRanking,
    ExecutionBasedRejection,
    ExecutionStatus,
    GapSeverity,
    ImplementationComplexity,
    MetricResult,
    MinimumEvidenceStandard,
    PointInTimeStatus,
    ProxyOption,
    QualityLossEstimate,
    RequirementLevel,
    ResearchSpec,
    StatisticalSignificance,
    TestResult,
    TestResultOutcome,
    TestSequenceItem,
    TestType,
    ValidationBurden,
    ValidationPlan,
    ValidationRequirements,
)
from src.judgment.audit_engine import audit_candidate


def _make_spec(
    *,
    forbidden_behaviors: list[str] | None = None,
    minimum_evidence_standard: MinimumEvidenceStandard = MinimumEvidenceStandard.MODERATE,
) -> ResearchSpec:
    return ResearchSpec(
        spec_id="run_audit_test-RS",
        run_id="run_audit_test",
        primary_objective="監査テスト",
        problem_frame="投資戦略監査",
        constraints=Constraints(forbidden_behaviors=forbidden_behaviors or []),
        validation_requirements=ValidationRequirements(
            must_test=["バックテスト"],
            minimum_evidence_standard=minimum_evidence_standard,
        ),
    )


def _make_candidate(
    cid: str = "C01",
    *,
    assumptions: list[str] | None = None,
    architecture_outline: list[str] | None = None,
    required_inputs: list[str] | None = None,
    burden: ValidationBurden = ValidationBurden.MEDIUM,
    complexity: ImplementationComplexity = ImplementationComplexity.MEDIUM,
) -> Candidate:
    assumptions = assumptions or ["モメンタムが継続する"]
    return Candidate(
        candidate_id=cid,
        name=f"Candidate {cid}",
        candidate_type=CandidateType.BASELINE,
        summary="テスト候補",
        architecture_outline=architecture_outline or ["シンプルな候補"],
        core_assumptions=[
            CandidateAssumption(
                assumption_id=f"{cid}-A{i + 1}",
                statement=statement,
                failure_impact="前提が崩れると優位性が消える",
            )
            for i, statement in enumerate(assumptions)
        ],
        required_inputs=required_inputs or ["日次株価データ(OHLCV)", "銘柄ユニバース構成情報"],
        validation_burden=burden,
        implementation_complexity=complexity,
        known_risks=["市場環境の急変", "データ品質の劣化"],
    )


def _make_price_evidence_item(cid: str = "C01") -> EvidenceItem:
    return EvidenceItem(
        item_id=f"{cid}-EI-001",
        category=EvidenceCategory.PRICE,
        description="日次株価データ（OHLCV）",
        requirement_level=RequirementLevel.REQUIRED,
        availability=Availability.AVAILABLE,
        quality_concerns=[],
        known_biases=[],
        point_in_time_status=PointInTimeStatus.PARTIAL,
        reporting_lag_days=0,
    )


def _make_evidence_plan(
    cid: str = "C01",
    *,
    gap_severity: GapSeverity = GapSeverity.NONE,
    required_total: int = 4,
    required_available: int = 4,
    evidence_items: list[EvidenceItem] | None = None,
) -> EvidencePlan:
    return EvidencePlan(
        evidence_plan_id=f"{cid}-EP",
        candidate_id=cid,
        gap_severity=gap_severity,
        evidence_items=evidence_items or [_make_price_evidence_item(cid)],
        coverage_metrics=CoverageMetrics(
            required_total=required_total,
            required_available=required_available,
            coverage_percentage=(required_available / required_total) * 100 if required_total else 100.0,
        ),
    )


def _make_validation_plan(
    cid: str = "C01",
    *,
    tests: list[TestSequenceItem] | None = None,
) -> ValidationPlan:
    return ValidationPlan(
        validation_plan_id=f"{cid}-VP",
        candidate_id=cid,
        test_sequence=tests or [
            TestSequenceItem(
                test_id=f"{cid}-T01",
                test_type=TestType.OFFLINE_BACKTEST,
                purpose="バックテスト",
                method_summary="過去リターンを比較する",
                failure_conditions=["シャープレシオが0未満"],
            )
        ],
    )


def _make_test_result(
    cid: str = "C01",
    *,
    overall_result: TestResultOutcome = TestResultOutcome.PASS,
    data_quality_flags: list[str] | None = None,
) -> TestResult:
    return TestResult(
        test_result_id=f"{cid}-TR",
        test_id=f"{cid}-BT",
        candidate_id=cid,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=[
            MetricResult(
                metric_name="annualized_return",
                actual_value=0.12,
                pass_threshold=">0",
                fail_threshold="<=0",
                result=TestResultOutcome.PASS,
            )
        ],
        overall_result=overall_result,
        data_quality_flags=data_quality_flags or [],
        pit_compliance="partial",
    )


def _make_comparison_result(rejected_candidate_id: str = "C01") -> ComparisonResult:
    return ComparisonResult(
        comparison_id="cmp_001",
        run_id="run_audit_test",
        comparison_matrix=ComparisonMatrixData(
            candidates=["C01", "C02"],
            baseline_candidate_id="C01",
            metrics=[
                ComparisonMetric(
                    metric_name="annualized_return",
                    values={
                        "C01": CandidateMetricValue(value=0.12, vs_baseline=0.0, rank=1),
                        "C02": CandidateMetricValue(value=0.08, vs_baseline=-0.04, rank=2),
                    },
                )
            ],
        ),
        execution_based_rejections=[
            ExecutionBasedRejection(
                candidate_id=rejected_candidate_id,
                reason="annualized_return が不合格閾値を下回った",
                disqualifying_test_results=["bt_C01"],
            )
        ],
        execution_based_ranking=ExecutionBasedRanking(recommended_best="C02"),
    )


def _make_oos_test_result(
    cid: str = "C01",
    *,
    is_sharpe: float = 1.2,
    oos_sharpe: float = 0.8,
    ratio: float = 0.67,
    overall_result: TestResultOutcome = TestResultOutcome.PASS,
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> TestResult:
    return TestResult(
        test_result_id=f"{cid}-OOS-TR",
        test_id=f"oos_{cid}",
        candidate_id=cid,
        execution_status=execution_status,
        metrics_results=[
            MetricResult(
                metric_name="in_sample_sharpe",
                actual_value=is_sharpe,
                pass_threshold=">0",
                fail_threshold="<0",
                result=TestResultOutcome.PASS if is_sharpe > 0 else TestResultOutcome.FAIL,
            ),
            MetricResult(
                metric_name="out_of_sample_sharpe",
                actual_value=oos_sharpe,
                pass_threshold=">0",
                fail_threshold="<0",
                result=TestResultOutcome.PASS if oos_sharpe > 0 else TestResultOutcome.FAIL,
            ),
            MetricResult(
                metric_name="oos_is_sharpe_ratio",
                actual_value=ratio,
                pass_threshold=">=0.5",
                fail_threshold="<0.5",
                result=TestResultOutcome.PASS if ratio >= 0.5 else TestResultOutcome.FAIL,
            ),
        ],
        overall_result=overall_result,
        pit_compliance="partial",
    )


def _make_significance_test_result(
    cid: str = "C01",
    *,
    metric_name: str,
    p_value: float,
    overall_result: TestResultOutcome,
) -> TestResult:
    return TestResult(
        test_result_id=f"{cid}-{metric_name}-TR",
        test_id=f"{metric_name}_{cid}",
        candidate_id=cid,
        execution_status=ExecutionStatus.COMPLETED,
        metrics_results=[
            MetricResult(
                metric_name=metric_name,
                actual_value=1.0,
                pass_threshold="p<0.05",
                fail_threshold="p>=0.05",
                result=TestResultOutcome.PASS if p_value < 0.05 else TestResultOutcome.INCONCLUSIVE,
                statistical_significance=StatisticalSignificance(
                    test_used="test",
                    p_value=p_value,
                    confidence_interval=[0.1, 0.2],
                ),
            )
        ],
        overall_result=overall_result,
        pit_compliance="partial",
    )


class TestAuditEngine:
    def test_blocking_evidence_gap_rejects_candidate(self):
        audit = audit_candidate(
            _make_candidate(),
            _make_evidence_plan(gap_severity=GapSeverity.BLOCKING, required_available=1),
            _make_validation_plan(),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(issue.category == AuditCategory.EVIDENCE_GAP and issue.disqualifying for issue in audit.issues)
        assert audit.rejection_reason is not None

    def test_execution_based_rejection_becomes_disqualifying_issue(self):
        audit = audit_candidate(
            _make_candidate(),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(issue.category == AuditCategory.REALISM and issue.disqualifying for issue in audit.issues)

    def test_missing_execution_evidence_is_warning_not_rejection(self):
        audit = audit_candidate(
            _make_candidate(),
            _make_evidence_plan(),
            _make_validation_plan(),
            None,
            comparison_result=None,
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(issue.category == AuditCategory.RECOMMENDATION_RISK for issue in audit.issues)

    def test_complexity_warning_marks_candidate_with_warnings(self):
        audit = audit_candidate(
            _make_candidate(
                burden=ValidationBurden.HIGH,
                complexity=ImplementationComplexity.HIGH,
            ),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(issue.category == AuditCategory.COMPLEXITY for issue in audit.issues)

    def test_assumption_absent_from_validation_coverage_warns(self):
        audit = audit_candidate(
            _make_candidate(assumptions=["イベントドリフトが持続する"]),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(issue.category == AuditCategory.ASSUMPTION for issue in audit.issues)
        assert not any(issue.category == AuditCategory.ASSUMPTION and issue.disqualifying for issue in audit.issues)

    def test_assumption_conflicting_with_constraints_rejects(self):
        audit = audit_candidate(
            _make_candidate(assumptions=["空売りが可能である"]),
            _make_evidence_plan(),
            _make_validation_plan(
                tests=[
                    TestSequenceItem(
                        test_id="C01-T01",
                        test_type=TestType.OFFLINE_BACKTEST,
                        purpose="空売り前提のバックテスト",
                        method_summary="空売りを使う",
                        failure_conditions=["空売りが機能しない"],
                    )
                ]
            ),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(forbidden_behaviors=["空売り禁止"]),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(issue.category == AuditCategory.ASSUMPTION and issue.disqualifying for issue in audit.issues)

    def test_many_unsupported_core_assumptions_escalate_to_rejection(self):
        audit = audit_candidate(
            _make_candidate(
                assumptions=[
                    "季節性プレミアムが持続する",
                    "小型株需給優位が継続する",
                    "企業行動が事前に予測可能である",
                ]
            ),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(minimum_evidence_standard=MinimumEvidenceStandard.STRONG),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(issue.category == AuditCategory.ASSUMPTION and issue.disqualifying for issue in audit.issues)

    def test_obvious_future_information_dependency_rejects(self):
        evidence_items = [
            _make_price_evidence_item(),
            EvidenceItem(
                item_id="C01-EI-002",
                category=EvidenceCategory.FUNDAMENTAL,
                description="翌日開示を含む将来財務データ",
                requirement_level=RequirementLevel.REQUIRED,
                availability=Availability.AVAILABLE,
                quality_concerns=["future information risk"],
                known_biases=[],
                point_in_time_status=PointInTimeStatus.NONE,
                reporting_lag_days=None,
                leakage_risk_patterns=["LKG-07", "future_info"],
            ),
        ]

        audit = audit_candidate(
            _make_candidate(required_inputs=["日次株価データ", "翌日開示を含む将来財務データ"]),
            _make_evidence_plan(evidence_items=evidence_items),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(issue.category == AuditCategory.LEAKAGE_RISK and issue.disqualifying for issue in audit.issues)

    def test_weak_temporal_evidence_is_warning(self):
        evidence_items = [
            _make_price_evidence_item(),
            EvidenceItem(
                item_id="C01-EI-002",
                category=EvidenceCategory.FUNDAMENTAL,
                description="公開タイミングが曖昧な財務データ",
                requirement_level=RequirementLevel.REQUIRED,
                availability=Availability.AVAILABLE,
                quality_concerns=["timing unclear"],
                known_biases=[],
                point_in_time_status=PointInTimeStatus.PARTIAL,
                reporting_lag_days=None,
                leakage_risk_patterns=["timing_unclear"],
            ),
        ]

        audit = audit_candidate(
            _make_candidate(required_inputs=["日次株価データ", "財務データ"]),
            _make_evidence_plan(evidence_items=evidence_items),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(issue.category == AuditCategory.LEAKAGE_RISK for issue in audit.issues)
        assert not any(issue.category == AuditCategory.LEAKAGE_RISK and issue.disqualifying for issue in audit.issues)

    def test_proxy_or_synthetic_like_evidence_is_warning(self):
        evidence_items = [
            _make_price_evidence_item(),
            EvidenceItem(
                item_id="C01-EI-002",
                category=EvidenceCategory.ALTERNATIVE,
                description="synthetic sentiment proxy",
                requirement_level=RequirementLevel.REQUIRED,
                availability=Availability.AVAILABLE,
                quality_concerns=["proxy quality degraded"],
                known_biases=[],
                point_in_time_status=PointInTimeStatus.PARTIAL,
                reporting_lag_days=1,
                proxy_option=ProxyOption(
                    description="proxy sentiment fallback",
                    quality_loss_estimate=QualityLossEstimate.SEVERE,
                ),
            ),
        ]

        audit = audit_candidate(
            _make_candidate(required_inputs=["日次株価データ", "センチメント代理データ"]),
            _make_evidence_plan(evidence_items=evidence_items),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(issue.category == AuditCategory.LEAKAGE_RISK for issue in audit.issues)

    def test_candidate_requiring_live_trading_like_capabilities_is_rejected(self):
        audit = audit_candidate(
            _make_candidate(
                architecture_outline=["broker API で実注文を送信", "低遅延で発注"],
                required_inputs=["リアルタイム板情報"],
            ),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(issue.category == AuditCategory.REALISM and issue.disqualifying for issue in audit.issues)

    def test_operationally_fragile_candidate_gets_realism_warning(self):
        audit = audit_candidate(
            _make_candidate(
                architecture_outline=["手動ニュース判定", "常時監視でシグナル調整"],
                required_inputs=["日次株価データ"],
            ),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(
            issue.category == AuditCategory.REALISM and not issue.disqualifying
            for issue in audit.issues
        )

    def test_clear_oos_collapse_rejects_for_overfitting_risk(self):
        statistical_tests = [
            _make_oos_test_result(
                is_sharpe=1.4,
                oos_sharpe=-0.2,
                ratio=-0.14,
                overall_result=TestResultOutcome.FAIL,
            ),
            _make_significance_test_result(
                metric_name="mean_daily_return",
                p_value=0.01,
                overall_result=TestResultOutcome.PASS,
            ),
            _make_significance_test_result(
                metric_name="annualized_sharpe_ratio",
                p_value=0.02,
                overall_result=TestResultOutcome.PASS,
            ),
        ]

        audit = audit_candidate(
            _make_candidate(),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            statistical_tests=statistical_tests,
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.REJECTED
        assert any(
            issue.category == AuditCategory.OVERFITTING_RISK and issue.disqualifying
            for issue in audit.issues
        )

    def test_weak_significance_is_warning_not_rejection(self):
        statistical_tests = [
            _make_oos_test_result(
                is_sharpe=0.9,
                oos_sharpe=0.6,
                ratio=0.67,
                overall_result=TestResultOutcome.PASS,
            ),
            _make_significance_test_result(
                metric_name="mean_daily_return",
                p_value=0.08,
                overall_result=TestResultOutcome.INCONCLUSIVE,
            ),
            _make_significance_test_result(
                metric_name="annualized_sharpe_ratio",
                p_value=0.07,
                overall_result=TestResultOutcome.INCONCLUSIVE,
            ),
        ]

        audit = audit_candidate(
            _make_candidate(),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            statistical_tests=statistical_tests,
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(
            issue.category == AuditCategory.OVERFITTING_RISK and not issue.disqualifying
            for issue in audit.issues
        )

    def test_missing_statistical_artifacts_warns_for_thin_overfitting_evidence(self):
        audit = audit_candidate(
            _make_candidate(),
            _make_evidence_plan(),
            _make_validation_plan(),
            _make_test_result(),
            statistical_tests=[],
            comparison_result=_make_comparison_result(rejected_candidate_id="C99"),
            research_spec=_make_spec(),
        )

        assert audit.audit_status == AuditStatus.PASSED_WITH_WARNINGS
        assert any(
            issue.category == AuditCategory.OVERFITTING_RISK and not issue.disqualifying
            for issue in audit.issues
        )
