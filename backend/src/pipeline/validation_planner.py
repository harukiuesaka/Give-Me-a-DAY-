"""
Module 6: ValidationPlanner

For each candidate, define the test sequence, metrics, pass/fail thresholds,
and comparison framework.

Every test MUST have >= 1 failure_conditions.
A test that cannot fail is not a test.
"""

import logging

from src.domain.models import (
    Candidate,
    ComparisonMatrix,
    EstimatedEffort,
    EvidencePlan,
    GapSeverity,
    PlanCompleteness,
    ResearchSpec,
    TestSequenceItem,
    TestType,
    ValidationBurden,
    ValidationPlan,
)
from src.llm.client import LLMClient, LLMUnavailableError
from src.llm.prompts import VALIDATION_PLANNING_SYSTEM, VALIDATION_PLANNING_USER

logger = logging.getLogger(__name__)


def plan(
    research_spec: ResearchSpec,
    candidate: Candidate,
    evidence_plan: EvidencePlan,
) -> ValidationPlan:
    """
    Plan validation for a candidate.

    Ensures:
    - Every test has >= 1 failure_conditions
    - Mandatory tests: backtest, OOS, walk_forward, regime_split
    - Optional: sensitivity (if validation_burden >= medium)
    """
    client = LLMClient()

    if not client.available:
        logger.info("LLM unavailable — using fallback validation planning")
        return _fallback_plan(research_spec, candidate, evidence_plan)

    try:
        return _llm_plan(client, research_spec, candidate, evidence_plan)
    except (LLMUnavailableError, Exception) as e:
        logger.warning(f"LLM validation planning failed: {e} — using fallback")
        return _fallback_plan(research_spec, candidate, evidence_plan)


def _llm_plan(
    client: LLMClient,
    spec: ResearchSpec,
    candidate: Candidate,
    evidence: EvidencePlan,
) -> ValidationPlan:
    """Use LLM to generate validation plan."""
    prompt = VALIDATION_PLANNING_USER.format(
        candidate_name=candidate.name,
        candidate_type=candidate.candidate_type.value,
        archetype=spec.problem_frame,
        coverage_percentage=evidence.coverage_metrics.coverage_percentage,
        gap_severity=evidence.gap_severity.value,
    )

    data = client.call_json(VALIDATION_PLANNING_SYSTEM, prompt)

    raw_tests = data.get("tests", [])
    tests = _parse_tests(raw_tests, candidate.candidate_id, evidence)

    # Ensure mandatory tests
    tests = _ensure_mandatory_tests(tests, candidate, evidence)

    # Validate: every test has failure_conditions
    _validate_failure_conditions(tests)

    # Set prerequisites
    _set_prerequisites(tests)

    # Determine completeness
    completeness = _determine_completeness(evidence)

    # Build comparison matrix
    matrix = _build_comparison_matrix(spec)

    return ValidationPlan(
        validation_plan_id=f"{spec.run_id}-VP-{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        test_sequence=tests,
        plan_completeness=completeness,
        comparison_matrix=matrix,
    )


def _fallback_plan(
    spec: ResearchSpec,
    candidate: Candidate,
    evidence: EvidencePlan,
) -> ValidationPlan:
    """Template-based validation planning without LLM."""
    cid = candidate.candidate_id
    tests: list[TestSequenceItem] = []

    # 1. Offline backtest (mandatory)
    tests.append(TestSequenceItem(
        test_id=f"{cid}-T01",
        test_type=TestType.OFFLINE_BACKTEST,
        purpose="過去データでの戦略パフォーマンスの検証",
        method_summary="過去5年分の日次データで戦略をバックテストし、リスク調整後リターンを算出",
        required_evidence_items=[
            it.item_id for it in evidence.evidence_items
            if it.requirement_level.value == "required"
        ][:3],
        failure_conditions=[
            "累積リターンがベンチマーク（市場インデックス）を下回る",
            "シャープレシオが0.5未満",
            "最大ドローダウンが-30%を超える",
        ],
        estimated_effort=EstimatedEffort.MEDIUM,
    ))

    # 2. Out-of-sample test (mandatory)
    tests.append(TestSequenceItem(
        test_id=f"{cid}-T02",
        test_type=TestType.OUT_OF_SAMPLE,
        purpose="過学習でないことの確認",
        method_summary="データを70/30に分割し、訓練期間外のデータでパフォーマンスを検証",
        execution_prerequisites=[f"{cid}-T01"],
        failure_conditions=[
            "アウトオブサンプル期間でのリターンがインサンプルの50%未満",
            "アウトオブサンプルのシャープレシオがインサンプルの40%未満",
        ],
        estimated_effort=EstimatedEffort.MEDIUM,
    ))

    # 3. Walk-forward test (mandatory)
    tests.append(TestSequenceItem(
        test_id=f"{cid}-T03",
        test_type=TestType.WALK_FORWARD,
        purpose="時間経過に伴う戦略の頑健性の検証",
        method_summary="1年窓のウォークフォワードテストで、逐次的にパフォーマンスを確認",
        execution_prerequisites=[f"{cid}-T01"],
        failure_conditions=[
            "ウォークフォワード各期間の50%以上で負のリターン",
            "直近の期間で著しいパフォーマンス悪化",
        ],
        estimated_effort=EstimatedEffort.HIGH,
    ))

    # 4. Regime split (mandatory)
    tests.append(TestSequenceItem(
        test_id=f"{cid}-T04",
        test_type=TestType.REGIME_SPLIT,
        purpose="市場環境別のパフォーマンス特性の把握",
        method_summary="上昇相場/下降相場/高ボラ/低ボラ別にパフォーマンスを分析",
        execution_prerequisites=[f"{cid}-T01"],
        failure_conditions=[
            "全レジームでベンチマークを下回る",
            "特定レジームでの損失が全体利益を上回る",
        ],
        estimated_effort=EstimatedEffort.MEDIUM,
    ))

    # 5. Sensitivity (conditional)
    if candidate.validation_burden != ValidationBurden.LOW:
        tests.append(TestSequenceItem(
            test_id=f"{cid}-T05",
            test_type=TestType.SENSITIVITY,
            purpose="パラメータ変更に対する頑健性の確認",
            method_summary="主要パラメータを±20%変動させ、結果の安定性を検証",
            execution_prerequisites=[f"{cid}-T01"],
            failure_conditions=[
                "パラメータの小さな変更でリターンの符号が変わる",
                "最適パラメータの近傍で性能が急激に劣化する",
            ],
            estimated_effort=EstimatedEffort.HIGH,
        ))

    completeness = _determine_completeness(evidence)
    matrix = _build_comparison_matrix(spec)

    return ValidationPlan(
        validation_plan_id=f"{spec.run_id}-VP-{cid}",
        candidate_id=cid,
        test_sequence=tests,
        plan_completeness=completeness,
        comparison_matrix=matrix,
    )


def _parse_tests(
    raw_tests: list, candidate_id: str, evidence: EvidencePlan
) -> list[TestSequenceItem]:
    """Parse LLM-generated test items."""
    tests = []
    for i, raw in enumerate(raw_tests):
        if not isinstance(raw, dict):
            continue
        try:
            test_type = TestType(raw.get("test_type", "offline_backtest"))
        except ValueError:
            test_type = TestType.OFFLINE_BACKTEST
        try:
            effort = EstimatedEffort(raw.get("estimated_effort", "medium"))
        except ValueError:
            effort = EstimatedEffort.MEDIUM

        failure_conditions = raw.get("failure_conditions", [])
        if not failure_conditions:
            failure_conditions = ["テスト結果がベンチマークを下回る"]

        tests.append(TestSequenceItem(
            test_id=raw.get("test_id", f"{candidate_id}-T{i+1:02d}"),
            test_type=test_type,
            purpose=raw.get("purpose", ""),
            method_summary=raw.get("method_summary", ""),
            failure_conditions=failure_conditions,
            estimated_effort=effort,
        ))
    return tests


def _ensure_mandatory_tests(
    tests: list[TestSequenceItem],
    candidate: Candidate,
    evidence: EvidencePlan,
) -> list[TestSequenceItem]:
    """Ensure mandatory test types are present."""
    mandatory = {
        TestType.OFFLINE_BACKTEST,
        TestType.OUT_OF_SAMPLE,
        TestType.WALK_FORWARD,
        TestType.REGIME_SPLIT,
    }
    present = {t.test_type for t in tests}
    cid = candidate.candidate_id

    defaults = {
        TestType.OFFLINE_BACKTEST: ("バックテスト", ["シャープレシオが0.5未満"]),
        TestType.OUT_OF_SAMPLE: ("アウトオブサンプル検証", ["OOS期間のリターンがIS期間の50%未満"]),
        TestType.WALK_FORWARD: ("ウォークフォワード検証", ["各期間の50%以上で負のリターン"]),
        TestType.REGIME_SPLIT: ("レジーム別検証", ["全レジームでベンチマーク以下"]),
    }

    for tt in mandatory:
        if tt not in present:
            purpose, fc = defaults[tt]
            tests.append(TestSequenceItem(
                test_id=f"{cid}-T{len(tests)+1:02d}",
                test_type=tt,
                purpose=purpose,
                method_summary=f"{purpose}の標準手法",
                failure_conditions=fc,
                estimated_effort=EstimatedEffort.MEDIUM,
            ))

    return tests


def _validate_failure_conditions(tests: list[TestSequenceItem]) -> None:
    """Ensure every test has at least 1 failure condition."""
    for test in tests:
        if not test.failure_conditions:
            test.failure_conditions = [f"{test.test_type.value}の結果が基準を下回る"]


def _set_prerequisites(tests: list[TestSequenceItem]) -> None:
    """Set execution prerequisites: all tests require backtest first."""
    backtest_id = None
    for t in tests:
        if t.test_type == TestType.OFFLINE_BACKTEST:
            backtest_id = t.test_id
            break

    if backtest_id:
        for t in tests:
            if (
                t.test_type != TestType.OFFLINE_BACKTEST
                and not t.execution_prerequisites
            ):
                t.execution_prerequisites = [backtest_id]


def _determine_completeness(evidence: EvidencePlan) -> PlanCompleteness:
    """Determine plan completeness from evidence gaps."""
    if evidence.gap_severity == GapSeverity.BLOCKING:
        return PlanCompleteness.MINIMAL
    if evidence.gap_severity == GapSeverity.MANAGEABLE:
        return PlanCompleteness.PARTIAL_DUE_TO_EVIDENCE_GAPS
    return PlanCompleteness.COMPLETE


def _build_comparison_matrix(spec: ResearchSpec) -> ComparisonMatrix:
    """Build comparison matrix from spec."""
    return ComparisonMatrix(
        candidates_compared=spec.validation_requirements.must_compare,
        comparison_metrics=[
            "累積リターン",
            "シャープレシオ",
            "最大ドローダウン",
            "勝率",
            "リスク調整後リターン",
        ],
        comparison_method="各指標でランク付けし、総合スコアで比較",
    )
