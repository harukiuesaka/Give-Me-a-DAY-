"""
Pydantic models matching internal_schema.md (all 17 objects).

This is the single source of truth for data shapes in code.
Every object in internal_schema.md has a corresponding Pydantic model here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class RiskPreference(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TimeHorizonPreference(str, Enum):
    FAST = "fast"
    ONE_DAY = "one_day"
    ONE_WEEK = "one_week"
    ONE_MONTH = "one_month"
    QUALITY_OVER_SPEED = "quality_over_speed"


class Archetype(str, Enum):
    FACTOR = "FACTOR"
    STAT_ARB = "STAT_ARB"
    EVENT = "EVENT"
    MACRO = "MACRO"
    ML_SIGNAL = "ML_SIGNAL"
    ALT_DATA = "ALT_DATA"
    HYBRID = "HYBRID"
    UNCLASSIFIED = "UNCLASSIFIED"


class CandidateType(str, Enum):
    BASELINE = "baseline"
    CONSERVATIVE = "conservative"
    EXPLORATORY = "exploratory"
    HYBRID = "hybrid"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLabel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationBurden(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImplementationComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceCategory(str, Enum):
    PRICE = "price"
    FUNDAMENTAL = "fundamental"
    ALTERNATIVE = "alternative"
    MACRO = "macro"
    SENTIMENT = "sentiment"
    FLOW = "flow"
    METADATA = "metadata"


class RequirementLevel(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    PROXY_ACCEPTABLE = "proxy_acceptable"


class Availability(str, Enum):
    AVAILABLE = "available"
    OBTAINABLE_WITH_EFFORT = "obtainable_with_effort"
    UNAVAILABLE = "unavailable"


class Frequency(str, Enum):
    TICK = "tick"
    MINUTE = "minute"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class PointInTimeStatus(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class QualityLossEstimate(str, Enum):
    MINIMAL = "minimal"
    MEDIUM = "medium"
    SEVERE = "severe"


class GapSeverity(str, Enum):
    NONE = "none"
    MANAGEABLE = "manageable"
    BLOCKING = "blocking"


class TestType(str, Enum):
    OFFLINE_BACKTEST = "offline_backtest"
    WALK_FORWARD = "walk_forward"
    OUT_OF_SAMPLE = "out_of_sample"
    REGIME_SPLIT = "regime_split"
    STRESS_TEST = "stress_test"
    SENSITIVITY = "sensitivity"
    PAPER_RUN = "paper_run"
    MONTE_CARLO = "monte_carlo"


class PlanCompleteness(str, Enum):
    COMPLETE = "complete"
    PARTIAL_DUE_TO_EVIDENCE_GAPS = "partial_due_to_evidence_gaps"
    MINIMAL = "minimal"


class AuditStatus(str, Enum):
    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    REJECTED = "rejected"


class AuditCategory(str, Enum):
    ASSUMPTION = "assumption"
    EVIDENCE_GAP = "evidence_gap"
    LEAKAGE_RISK = "leakage_risk"
    OVERFITTING_RISK = "overfitting_risk"
    REALISM = "realism"
    REGIME_DEPENDENCY = "regime_dependency"
    COMPLEXITY = "complexity"
    OBSERVABILITY = "observability"
    COST_ASSUMPTION = "cost_assumption"
    RECOMMENDATION_RISK = "recommendation_risk"


class CandidateLabel(str, Enum):
    PRIMARY = "primary"
    ALTERNATIVE = "alternative"


class PaperRunStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    HALTED = "halted"
    RE_EVALUATING = "re_evaluating"


class RunStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class AssumptionCategory(str, Enum):
    MARKET_EFFICIENCY = "market_efficiency"
    STATIONARITY = "stationarity"
    LIQUIDITY = "liquidity"
    DATA_QUALITY = "data_quality"
    CAUSAL = "causal"
    COST = "cost"
    REGULATORY = "regulatory"


class AssumptionSource(str, Enum):
    USER_STATED = "user_stated"
    SYSTEM_INFERRED = "system_inferred"
    DOMAIN_DEFAULT = "domain_default"


class MinimumEvidenceStandard(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class ExpiryType(str, Enum):
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    EVIDENCE_BASED = "evidence_based"


class AcquisitionStatus(str, Enum):
    ACQUIRED = "acquired"
    PARTIALLY_ACQUIRED = "partially_acquired"
    FAILED = "failed"


class QualityCheckType(str, Enum):
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    TEMPORAL = "temporal"
    SURVIVORSHIP = "survivorship"
    PIT = "pit"


class QualityIssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class TestResultOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    MIXED = "mixed"
    INCONCLUSIVE = "inconclusive"


class ReEvaluationTrigger(str, Enum):
    QUARTERLY_SCHEDULE = "quarterly_schedule"
    STOP_CONDITION_HIT = "stop_condition_hit"
    MARKET_REGIME_CHANGE = "market_regime_change"
    USER_REQUESTED = "user_requested"


class ReEvaluationOutcome(str, Enum):
    CONTINUE = "continue"
    CHANGE_CANDIDATE = "change_candidate"
    STOP_ALL = "stop_all"


class NextValidationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"


class ComparisonTarget(str, Enum):
    NULL = "null"
    BASELINE_CANDIDATE = "baseline_candidate"
    BENCHMARK = "benchmark"
    ABSOLUTE_VALUE = "absolute_value"


class EstimatedEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimLayer(str, Enum):
    PREMISE = "premise"
    CORE = "core"
    PRACTICAL = "practical"


class DisqualifyingAppliesTo(str, Enum):
    ALL_CANDIDATES = "all_candidates"
    SPECIFIC_CANDIDATE_TYPES = "specific_candidate_types"


class Currency(str, Enum):
    JPY = "JPY"
    USD = "USD"


# ============================================================
# §1. UserIntent
# ============================================================

class UserIntent(BaseModel):
    run_id: str
    created_at: datetime
    raw_goal: str
    domain: str = "investment_research"
    user_goal_summary: str
    success_definition: str
    risk_preference: RiskPreference
    time_horizon_preference: TimeHorizonPreference
    must_not_do: list[str] = Field(default_factory=list)
    available_inputs: list[str] = Field(default_factory=list)
    open_uncertainties: list[str] = Field(default_factory=list)
    # Companion AI tracing — optional, never read by pipeline logic
    companion_context: Optional[dict] = None


# ============================================================
# §2. DomainFrame
# ============================================================

class TestableClaim(BaseModel):
    claim_id: str
    layer: ClaimLayer
    claim: str
    falsification_condition: str


class ComparableApproach(BaseModel):
    name: str
    relevance: str
    known_outcome: str


class DomainFrame(BaseModel):
    run_id: str
    archetype: Archetype
    reframed_problem: str
    core_hypothesis: str
    testable_claims: list[TestableClaim] = Field(min_length=1)
    critical_assumptions: list[str] = Field(default_factory=list)
    regime_dependencies: list[str] = Field(min_length=1)
    comparable_known_approaches: list[ComparableApproach] = Field(default_factory=list)


# ============================================================
# §3. ResearchSpec
# ============================================================

class AssumptionItem(BaseModel):
    assumption_id: str
    statement: str
    category: AssumptionCategory
    falsification_condition: str
    source: AssumptionSource


class Constraints(BaseModel):
    time: str = ""
    budget: str = ""
    tooling: list[str] = Field(default_factory=list)
    forbidden_behaviors: list[str] = Field(default_factory=list)


class EvidenceRequirements(BaseModel):
    required_data: list[str] = Field(default_factory=list)
    optional_data: list[str] = Field(default_factory=list)
    proxy_data_allowed: bool = True
    evidence_gaps: list[str] = Field(default_factory=list)


class DisqualifyingFailure(BaseModel):
    failure_id: str
    description: str
    metric: str
    threshold: str
    applies_to: DisqualifyingAppliesTo


class ValidationRequirements(BaseModel):
    must_test: list[str] = Field(default_factory=list)
    must_compare: list[str] = Field(default_factory=list)
    disqualifying_failures: list[DisqualifyingFailure] = Field(default_factory=list)
    minimum_evidence_standard: MinimumEvidenceStandard = MinimumEvidenceStandard.MODERATE


class RecommendationRequirements(BaseModel):
    must_return_runner_up: bool = True
    must_return_rejections: bool = True
    must_surface_unknowns: bool = True
    allow_no_valid_candidate: bool = True


class ResearchSpec(BaseModel):
    spec_id: str
    run_id: str
    primary_objective: str
    secondary_objectives: list[str] = Field(default_factory=list)
    problem_frame: str
    assumption_space: list[AssumptionItem] = Field(default_factory=list, max_length=15)
    constraints: Constraints = Field(default_factory=Constraints)
    evidence_requirements: EvidenceRequirements = Field(default_factory=EvidenceRequirements)
    validation_requirements: ValidationRequirements = Field(default_factory=ValidationRequirements)
    recommendation_requirements: RecommendationRequirements = Field(
        default_factory=RecommendationRequirements
    )


# ============================================================
# §4. Candidate
# ============================================================

class CandidateAssumption(BaseModel):
    assumption_id: str
    statement: str
    failure_impact: str


class Candidate(BaseModel):
    candidate_id: str
    name: str
    candidate_type: CandidateType
    summary: str
    architecture_outline: list[str] = Field(default_factory=list)
    core_assumptions: list[CandidateAssumption] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    validation_burden: ValidationBurden = ValidationBurden.MEDIUM
    implementation_complexity: ImplementationComplexity = ImplementationComplexity.MEDIUM
    expected_strengths: list[str] = Field(default_factory=list)
    expected_weaknesses: list[str] = Field(default_factory=list)
    known_risks: list[str] = Field(min_length=1)


# ============================================================
# §5. EvidencePlan
# ============================================================

class TemporalCoverage(BaseModel):
    start: str  # ISO-8601
    end: str  # ISO-8601
    frequency: Frequency


class ProxyOption(BaseModel):
    description: str
    quality_loss_estimate: QualityLossEstimate
    permitted: bool = True
    prohibition_reason: Optional[str] = None


class EvidenceItem(BaseModel):
    item_id: str
    category: EvidenceCategory
    description: str
    requirement_level: RequirementLevel
    availability: Availability
    quality_concerns: list[str] = Field(default_factory=list)
    known_biases: list[str] = Field(default_factory=list)
    temporal_coverage: Optional[TemporalCoverage] = None
    point_in_time_status: PointInTimeStatus = PointInTimeStatus.NONE
    reporting_lag_days: Optional[int] = None
    proxy_option: Optional[ProxyOption] = None
    leakage_risk_patterns: list[str] = Field(default_factory=list)


class CriticalGap(BaseModel):
    gap_id: str
    description: str
    affected_evidence_items: list[str] = Field(default_factory=list)
    severity: GapSeverity
    impact_on_recommendation: str
    mitigation_option: Optional[str] = None


class CoverageMetrics(BaseModel):
    required_total: int = 0
    required_available: int = 0
    required_obtainable: int = 0
    required_unavailable: int = 0
    coverage_percentage: float = 0.0


class EvidencePlan(BaseModel):
    evidence_plan_id: str
    candidate_id: str
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    critical_gaps: list[CriticalGap] = Field(default_factory=list)
    gap_severity: GapSeverity = GapSeverity.NONE
    coverage_metrics: CoverageMetrics = Field(default_factory=CoverageMetrics)


# ============================================================
# §6. ValidationPlan
# ============================================================

class TestMetric(BaseModel):
    name: str
    calculation_method: str
    pass_threshold: str
    fail_threshold: str
    comparison_target: Optional[ComparisonTarget] = None


class TimeWindow(BaseModel):
    label: str
    start: str  # ISO-8601
    end: str  # ISO-8601
    selection_rationale: str


class TestSequenceItem(BaseModel):
    test_id: str
    test_type: TestType
    purpose: str
    method_summary: str
    required_evidence_items: list[str] = Field(default_factory=list)
    metrics: list[TestMetric] = Field(default_factory=list)
    time_windows: list[TimeWindow] = Field(default_factory=list)
    failure_conditions: list[str] = Field(min_length=1)
    execution_prerequisites: list[str] = Field(default_factory=list)
    estimated_effort: EstimatedEffort = EstimatedEffort.MEDIUM


class ComparisonMatrix(BaseModel):
    candidates_compared: list[str] = Field(default_factory=list)
    comparison_metrics: list[str] = Field(default_factory=list)
    comparison_method: str = ""


class ValidationPlan(BaseModel):
    validation_plan_id: str
    candidate_id: str
    test_sequence: list[TestSequenceItem] = Field(default_factory=list)
    plan_completeness: PlanCompleteness = PlanCompleteness.COMPLETE
    comparison_matrix: ComparisonMatrix = Field(default_factory=ComparisonMatrix)


# ============================================================
# §7. Audit
# ============================================================

class AuditIssue(BaseModel):
    issue_id: str
    severity: Severity
    category: AuditCategory
    title: str
    explanation: str
    mitigation: Optional[str] = None
    disqualifying: bool = False
    affected_evidence_items: list[str] = Field(default_factory=list)
    affected_assumptions: list[str] = Field(default_factory=list)
    compound_pattern: Optional[str] = None


class MetaAudit(BaseModel):
    total_issues: int = 0
    issues_by_severity: dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0}
    )
    zero_issue_flag: bool = False
    compound_patterns_detected: list[str] = Field(default_factory=list)


class Audit(BaseModel):
    candidate_id: str
    audit_status: AuditStatus
    issues: list[AuditIssue] = Field(default_factory=list)
    rejection_reason: Optional[str] = None
    surviving_assumptions: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    meta_audit: MetaAudit = Field(default_factory=MetaAudit)


# ============================================================
# §8. Recommendation
# ============================================================

class RankingLogicItem(BaseModel):
    comparison_axis: str
    best_assessment: str
    runner_up_assessment: str
    verdict: str


class OpenUnknown(BaseModel):
    unknown_id: str
    description: str
    impact_if_resolved_positively: str
    impact_if_resolved_negatively: str
    resolution_method: str


class CriticalCondition(BaseModel):
    condition_id: str
    statement: str
    verification_method: str
    verification_timing: str
    source: str


class NextValidationStep(BaseModel):
    step_id: str
    who: str
    what_data: str
    what_test: str
    threshold: str
    priority: NextValidationPriority


class RecommendationExpiry(BaseModel):
    type: ExpiryType
    description: str
    expiry_date: Optional[str] = None  # ISO-8601
    expiry_trigger: Optional[str] = None


class Recommendation(BaseModel):
    run_id: str
    best_candidate_id: Optional[str] = None
    runner_up_candidate_id: Optional[str] = None
    rejected_candidate_ids: list[str] = Field(default_factory=list)
    ranking_logic: list[RankingLogicItem] = Field(min_length=3)
    open_unknowns: list[OpenUnknown] = Field(min_length=1)
    critical_conditions: list[CriticalCondition] = Field(min_length=1)
    confidence_label: ConfidenceLabel
    confidence_explanation: str
    next_validation_steps: list[NextValidationStep] = Field(default_factory=list)
    recommendation_expiry: RecommendationExpiry


# ============================================================
# §9. CandidateCard (derived, user-facing)
# ============================================================

class ReturnBand(BaseModel):
    low_pct: float
    high_pct: float
    basis: str
    disclaimer: str


class MaxLoss(BaseModel):
    low_pct: float
    high_pct: float
    basis: str


class CandidateCard(BaseModel):
    candidate_id: str
    label: CandidateLabel
    display_name: str
    summary: str
    strategy_approach: str
    expected_return_band: ReturnBand
    estimated_max_loss: MaxLoss
    confidence_level: ConfidenceLabel
    confidence_reason: str
    key_risks: list[str] = Field(min_length=2, max_length=3)
    stop_conditions_headline: str


# ============================================================
# §10. PresentationContext (derived, user-facing)
# ============================================================

class PresentationContext(BaseModel):
    run_id: str
    created_at: datetime
    validation_summary: str
    recommendation_expiry: str
    rejection_headline: Optional[str] = None
    caveats: list[str] = Field(default_factory=list)
    candidates_evaluated: int
    candidates_rejected: int
    candidates_presented: int


# ============================================================
# §11. Approval
# ============================================================

class UserConfirmations(BaseModel):
    risks_reviewed: bool = False
    stop_conditions_reviewed: bool = False
    paper_run_understood: bool = False


class CostModel(BaseModel):
    commission_bps: int = 10
    spread_bps: int = 10


class RuntimeConfig(BaseModel):
    initial_virtual_capital: float = 1_000_000
    currency: Currency = Currency.JPY
    rebalance_frequency: str = "monthly"
    cost_model: CostModel = Field(default_factory=CostModel)
    execution_timing: str = "T+1_open"


class StopConditionSC01(BaseModel):
    id: str = "SC-01"
    type: str = "max_drawdown"
    threshold: float = -0.20
    action: str = "halt_and_notify"


class StopConditionSC02(BaseModel):
    id: str = "SC-02"
    type: str = "consecutive_underperformance"
    months: int = 3
    benchmark: str = "market_index"
    action: str = "halt_and_notify"


class StopConditionSC03(BaseModel):
    id: str = "SC-03"
    type: str = "signal_anomaly"
    threshold_sigma: float = 3.0
    action: str = "pause_and_notify"


class StopConditionSC04(BaseModel):
    id: str = "SC-04"
    type: str = "data_quality_failure"
    consecutive_days: int = 3
    action: str = "pause_and_notify"


class ReEvaluationConfig(BaseModel):
    monthly_report: bool = True
    quarterly_full_re_evaluation: bool = True
    re_evaluation_triggers: list[str] = Field(default_factory=list)


class Approval(BaseModel):
    approval_id: str
    run_id: str
    candidate_id: str
    approved_at: datetime
    user_confirmations: UserConfirmations
    runtime_config: RuntimeConfig = Field(default_factory=RuntimeConfig)
    stop_conditions: list[
        StopConditionSC01 | StopConditionSC02 | StopConditionSC03 | StopConditionSC04
    ] = Field(default_factory=lambda: [
        StopConditionSC01(),
        StopConditionSC02(),
        StopConditionSC03(),
        StopConditionSC04(),
    ])
    re_evaluation: ReEvaluationConfig = Field(default_factory=ReEvaluationConfig)
    re_approval_required: list[str] = Field(default_factory=list)
    # Companion AI tracing — optional, never read by pipeline logic
    companion_context: Optional[dict] = None


# ============================================================
# §12. PaperRunState
# ============================================================

class CurrentSnapshot(BaseModel):
    day_count: int = 0
    virtual_capital_initial: float = 0.0
    virtual_capital_current: float = 0.0
    total_return_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    positions_count: int = 0
    last_rebalance: Optional[str] = None  # ISO-8601
    next_rebalance: Optional[str] = None  # ISO-8601


class NearestCondition(BaseModel):
    id: str
    current_value: float
    threshold: float
    distance_pct: float


class SafetyStatus(BaseModel):
    any_breached: bool = False
    nearest_condition: Optional[NearestCondition] = None


class PaperRunSchedule(BaseModel):
    next_monthly_report: Optional[str] = None  # ISO-8601
    next_quarterly_re_evaluation: Optional[str] = None  # ISO-8601


class PaperRunAttentionState(BaseModel):
    requires_attention: bool = False
    event_type: Optional[str] = None
    summary: Optional[str] = None
    source_event_id: Optional[str] = None
    source_event_type: Optional[str] = None
    updated_at: Optional[datetime] = None


class HaltEvent(BaseModel):
    halted_at: str  # ISO-8601
    condition_id: str
    resumed_at: Optional[str] = None  # ISO-8601
    re_approval_id: Optional[str] = None


class PaperRunState(BaseModel):
    paper_run_id: str
    approval_id: str
    candidate_id: str
    started_at: datetime
    status: PaperRunStatus = PaperRunStatus.RUNNING
    current_snapshot: CurrentSnapshot = Field(default_factory=CurrentSnapshot)
    safety_status: SafetyStatus = Field(default_factory=SafetyStatus)
    schedule: PaperRunSchedule = Field(default_factory=PaperRunSchedule)
    halt_history: list[HaltEvent] = Field(default_factory=list)


# ============================================================
# §13. MonthlyReport
# ============================================================

class ReportPeriod(BaseModel):
    start: str  # ISO-8601
    end: str  # ISO-8601


class ReportNumbers(BaseModel):
    monthly_return_pct: float = 0.0
    benchmark_return_pct: float = 0.0
    cumulative_return_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    positions_count: int = 0
    trades_this_month: int = 0


class MonthlyReport(BaseModel):
    report_id: str
    paper_run_id: str
    period: ReportPeriod
    summary: str
    numbers: ReportNumbers = Field(default_factory=ReportNumbers)
    safety_note: str = ""
    next: str = ""


# ============================================================
# §14. ReEvaluationResult
# ============================================================

class ReEvaluationResult(BaseModel):
    re_evaluation_id: str
    paper_run_id: str
    executed_at: datetime
    trigger: ReEvaluationTrigger
    outcome: ReEvaluationOutcome
    new_run_id: Optional[str] = None
    new_best_candidate_id: Optional[str] = None
    new_runner_up_candidate_id: Optional[str] = None
    explanation: str
    re_approval_required: bool = True


# ============================================================
# §15. DataQualityReport
# ============================================================

class QualityIssue(BaseModel):
    check_type: QualityCheckType
    severity: QualityIssueSeverity
    description: str
    affected_rows: int = 0
    affected_percentage: float = 0.0


class DateRange(BaseModel):
    start: str  # ISO-8601
    end: str  # ISO-8601


class DataQualityReport(BaseModel):
    evidence_item_id: str
    acquisition_status: AcquisitionStatus
    acquisition_timestamp: datetime
    data_source: str
    row_count: int = 0
    date_range_actual: Optional[DateRange] = None
    quality_issues: list[QualityIssue] = Field(default_factory=list)
    pit_status_verified: str = "not_applicable"
    usable_for_validation: bool = True


# ============================================================
# §16. TestResult
# ============================================================

class StatisticalSignificance(BaseModel):
    test_used: str
    p_value: Optional[float] = None
    confidence_interval: Optional[list[float]] = None


class MetricResult(BaseModel):
    metric_name: str
    actual_value: float
    pass_threshold: str
    fail_threshold: str
    result: TestResultOutcome
    statistical_significance: Optional[StatisticalSignificance] = None


class ReturnTimeseries(BaseModel):
    dates: list[str] = Field(default_factory=list)  # ISO-8601
    gross_returns: list[float] = Field(default_factory=list)
    net_returns: list[float] = Field(default_factory=list)
    benchmark_returns: list[float] = Field(default_factory=list)


class TestResult(BaseModel):
    test_result_id: str
    test_id: str
    candidate_id: str
    execution_status: ExecutionStatus
    metrics_results: list[MetricResult] = Field(default_factory=list)
    overall_result: TestResultOutcome
    return_timeseries: Optional[ReturnTimeseries] = None
    data_quality_flags: list[str] = Field(default_factory=list)
    pit_compliance: str = "none"


# ============================================================
# §17. ComparisonResult
# ============================================================

class CandidateMetricValue(BaseModel):
    value: float
    vs_baseline: float = 0.0
    is_significant: bool = False
    p_value: float = 1.0
    rank: int = 0


class ComparisonMetric(BaseModel):
    metric_name: str
    values: dict[str, CandidateMetricValue] = Field(default_factory=dict)


class ExecutionBasedRejection(BaseModel):
    candidate_id: str
    reason: str
    disqualifying_test_results: list[str] = Field(default_factory=list)


class RankingRationale(BaseModel):
    comparison_axis: str
    winner: str
    margin: str


class ExecutionBasedRanking(BaseModel):
    recommended_best: Optional[str] = None
    recommended_runner_up: Optional[str] = None
    ranking_rationale: list[RankingRationale] = Field(default_factory=list)


class ComparisonMatrixData(BaseModel):
    candidates: list[str] = Field(default_factory=list)
    baseline_candidate_id: str = ""
    metrics: list[ComparisonMetric] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    comparison_id: str
    run_id: str
    comparison_matrix: ComparisonMatrixData = Field(default_factory=ComparisonMatrixData)
    execution_based_rejections: list[ExecutionBasedRejection] = Field(default_factory=list)
    execution_based_ranking: ExecutionBasedRanking = Field(default_factory=ExecutionBasedRanking)


# ============================================================
# Audit Event (for audit trail)
# ============================================================

class AuditEvent(BaseModel):
    event_id: str
    timestamp: datetime
    run_id: str
    paper_run_id: Optional[str] = None
    event_type: str
    module: str
    details: dict = Field(default_factory=dict)


# ============================================================
# Run metadata (for persistence)
# ============================================================

class RunMeta(BaseModel):
    run_id: str
    created_at: datetime
    status: RunStatus = RunStatus.PENDING
    current_step: str = ""
    steps_completed: int = 0
    steps_total: int = 12
    estimated_remaining_seconds: Optional[int] = None
    error: Optional[str] = None
