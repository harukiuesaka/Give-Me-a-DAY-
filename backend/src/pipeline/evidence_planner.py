"""
Module 5: EvidencePlanner

For each candidate, identify required evidence items, assess availability,
detect biases, evaluate proxy options, and produce an EvidencePlan.

Uses LLM for gap analysis when available; falls back to archetype-based templates.
"""

import logging

from src.domain.models import (
    Availability,
    Candidate,
    CoverageMetrics,
    CriticalGap,
    EvidenceCategory,
    EvidenceItem,
    EvidencePlan,
    GapSeverity,
    PointInTimeStatus,
    ProxyOption,
    QualityLossEstimate,
    RequirementLevel,
    ResearchSpec,
)
from src.llm.client import LLMClient, LLMUnavailableError
from src.llm.prompts import EVIDENCE_PLANNING_SYSTEM, EVIDENCE_PLANNING_USER

logger = logging.getLogger(__name__)


def plan(research_spec: ResearchSpec, candidate: Candidate) -> EvidencePlan:
    """
    Plan evidence for a candidate.

    Produces EvidencePlan with:
    - evidence_items (required / optional / proxy_acceptable)
    - critical_gaps
    - gap_severity
    - coverage_metrics
    """
    client = LLMClient()

    if not client.available:
        logger.info("LLM unavailable — using fallback evidence planning")
        return _fallback_plan(research_spec, candidate)

    try:
        return _llm_plan(client, research_spec, candidate)
    except (LLMUnavailableError, Exception) as e:
        logger.warning(f"LLM evidence planning failed: {e} — using fallback")
        return _fallback_plan(research_spec, candidate)


def _llm_plan(
    client: LLMClient, spec: ResearchSpec, candidate: Candidate
) -> EvidencePlan:
    """Use LLM to generate evidence plan."""
    prompt = EVIDENCE_PLANNING_USER.format(
        candidate_name=candidate.name,
        archetype=spec.problem_frame,
        required_inputs=", ".join(candidate.required_inputs),
        architecture_outline=", ".join(candidate.architecture_outline),
    )

    data = client.call_json(EVIDENCE_PLANNING_SYSTEM, prompt)

    raw_items = data.get("evidence_items", [])
    items = _parse_evidence_items(raw_items, candidate.candidate_id)

    raw_gaps = data.get("critical_gaps", [])
    gaps = _parse_critical_gaps(raw_gaps)

    # Ensure price data is present
    items = _ensure_price_data(items, candidate.candidate_id)

    # Apply LKG-07 rule
    _apply_leakage_rules(items)

    # Compute metrics
    coverage = _compute_coverage(items)
    gap_severity = _compute_gap_severity(items, gaps)

    return EvidencePlan(
        evidence_plan_id=f"{spec.run_id}-EP-{candidate.candidate_id}",
        candidate_id=candidate.candidate_id,
        evidence_items=items,
        critical_gaps=gaps,
        gap_severity=gap_severity,
        coverage_metrics=coverage,
    )


def _fallback_plan(spec: ResearchSpec, candidate: Candidate) -> EvidencePlan:
    """Template-based evidence planning without LLM."""
    cid = candidate.candidate_id
    items: list[EvidenceItem] = []

    # Always required: price data
    items.append(EvidenceItem(
        item_id=f"{cid}-EI-001",
        category=EvidenceCategory.PRICE,
        description="日次株価データ（OHLCV）",
        requirement_level=RequirementLevel.REQUIRED,
        availability=Availability.AVAILABLE,
        quality_concerns=["生存者バイアスの可能性", "株式分割・配当調整の正確性"],
        known_biases=["PRC-B01"],
        point_in_time_status=PointInTimeStatus.PARTIAL,
        reporting_lag_days=0,
        leakage_risk_patterns=[],
    ))

    # Metadata
    items.append(EvidenceItem(
        item_id=f"{cid}-EI-002",
        category=EvidenceCategory.METADATA,
        description="銘柄ユニバース構成データ（上場/廃止日、セクター分類）",
        requirement_level=RequirementLevel.REQUIRED,
        availability=Availability.AVAILABLE,
        quality_concerns=["過去のユニバース再構成の正確性"],
        known_biases=["MTA-B01"],
        point_in_time_status=PointInTimeStatus.PARTIAL,
        reporting_lag_days=None,
        leakage_risk_patterns=[],
    ))

    # Add archetype-specific evidence
    for inp in candidate.required_inputs:
        inp_lower = inp.lower()
        if "株価" in inp_lower or "ohlcv" in inp_lower or "price" in inp_lower:
            continue  # Already covered
        if "ユニバース" in inp_lower or "構成" in inp_lower:
            continue

        category = _infer_category(inp_lower)
        items.append(EvidenceItem(
            item_id=f"{cid}-EI-{len(items)+1:03d}",
            category=category,
            description=inp,
            requirement_level=RequirementLevel.REQUIRED,
            availability=Availability.OBTAINABLE_WITH_EFFORT,
            quality_concerns=["データの網羅性と正確性の確認が必要"],
            known_biases=[],
            point_in_time_status=PointInTimeStatus.NONE,
            reporting_lag_days=None,
            leakage_risk_patterns=[],
        ))

    # Apply LKG-07 rule
    _apply_leakage_rules(items)

    # Compute coverage
    coverage = _compute_coverage(items)

    # Identify gaps
    gaps: list[CriticalGap] = []
    unavailable = [it for it in items if it.availability == Availability.UNAVAILABLE]
    for ua in unavailable:
        gaps.append(CriticalGap(
            gap_id=f"GAP-{len(gaps)+1:03d}",
            description=f"データ入手不可: {ua.description}",
            affected_evidence_items=[ua.item_id],
            severity=GapSeverity.MANAGEABLE if ua.requirement_level != RequirementLevel.REQUIRED
            else GapSeverity.BLOCKING,
            impact_on_recommendation="このデータなしでは候補の完全な検証が困難",
            mitigation_option="代替データソースの検討",
        ))

    gap_severity = _compute_gap_severity(items, gaps)

    return EvidencePlan(
        evidence_plan_id=f"{spec.run_id}-EP-{cid}",
        candidate_id=cid,
        evidence_items=items,
        critical_gaps=gaps,
        gap_severity=gap_severity,
        coverage_metrics=coverage,
    )


def _infer_category(text: str) -> EvidenceCategory:
    """Infer evidence category from description text."""
    if any(k in text for k in ["マクロ", "gdp", "cpi", "金利", "macro"]):
        return EvidenceCategory.MACRO
    if any(k in text for k in ["財務", "pbr", "roe", "eps", "fundamental"]):
        return EvidenceCategory.FUNDAMENTAL
    if any(k in text for k in ["センチメント", "ニュース", "sentiment"]):
        return EvidenceCategory.SENTIMENT
    if any(k in text for k in ["オルタナティブ", "sns", "衛星", "alternative"]):
        return EvidenceCategory.ALTERNATIVE
    if any(k in text for k in ["フロー", "出来高", "flow"]):
        return EvidenceCategory.FLOW
    return EvidenceCategory.METADATA


def _parse_evidence_items(raw_items: list, candidate_id: str) -> list[EvidenceItem]:
    """Parse LLM-generated evidence items."""
    items = []
    for i, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        try:
            category = EvidenceCategory(raw.get("category", "metadata"))
        except ValueError:
            category = EvidenceCategory.METADATA
        try:
            req_level = RequirementLevel(raw.get("requirement_level", "required"))
        except ValueError:
            req_level = RequirementLevel.REQUIRED
        try:
            avail = Availability(raw.get("availability", "obtainable_with_effort"))
        except ValueError:
            avail = Availability.OBTAINABLE_WITH_EFFORT
        try:
            pit = PointInTimeStatus(raw.get("point_in_time_status", "none"))
        except ValueError:
            pit = PointInTimeStatus.NONE

        items.append(EvidenceItem(
            item_id=raw.get("item_id", f"{candidate_id}-EI-{i+1:03d}"),
            category=category,
            description=raw.get("description", ""),
            requirement_level=req_level,
            availability=avail,
            quality_concerns=raw.get("quality_concerns", ["品質未評価"]),
            known_biases=raw.get("known_biases", []),
            point_in_time_status=pit,
            reporting_lag_days=raw.get("reporting_lag_days"),
            leakage_risk_patterns=raw.get("leakage_risk_patterns", []),
        ))
    return items


def _parse_critical_gaps(raw_gaps: list) -> list[CriticalGap]:
    """Parse LLM-generated critical gaps."""
    gaps = []
    for i, raw in enumerate(raw_gaps):
        if not isinstance(raw, dict):
            continue
        try:
            sev = GapSeverity(raw.get("severity", "manageable"))
        except ValueError:
            sev = GapSeverity.MANAGEABLE

        gaps.append(CriticalGap(
            gap_id=raw.get("gap_id", f"GAP-{i+1:03d}"),
            description=raw.get("description", ""),
            affected_evidence_items=raw.get("affected_evidence_items", []),
            severity=sev,
            impact_on_recommendation=raw.get("impact_on_recommendation", ""),
            mitigation_option=raw.get("mitigation_option"),
        ))
    return gaps


def _ensure_price_data(items: list[EvidenceItem], candidate_id: str) -> list[EvidenceItem]:
    """Ensure price data is present (all investment strategies need it)."""
    has_price = any(it.category == EvidenceCategory.PRICE for it in items)
    if not has_price:
        items.insert(0, EvidenceItem(
            item_id=f"{candidate_id}-EI-PRC",
            category=EvidenceCategory.PRICE,
            description="日次株価データ（OHLCV）",
            requirement_level=RequirementLevel.REQUIRED,
            availability=Availability.AVAILABLE,
            quality_concerns=["生存者バイアスの可能性"],
            known_biases=["PRC-B01"],
            point_in_time_status=PointInTimeStatus.PARTIAL,
        ))
    return items


def _apply_leakage_rules(items: list[EvidenceItem]) -> None:
    """Apply LKG-07: PIT status = none triggers leakage flag."""
    for item in items:
        if (
            item.point_in_time_status == PointInTimeStatus.NONE
            and item.category != EvidenceCategory.PRICE
            and "LKG-07" not in item.leakage_risk_patterns
        ):
            item.leakage_risk_patterns.append("LKG-07")


def _compute_coverage(items: list[EvidenceItem]) -> CoverageMetrics:
    """Compute evidence coverage metrics."""
    required = [it for it in items if it.requirement_level == RequirementLevel.REQUIRED]
    total = len(required)
    if total == 0:
        return CoverageMetrics(coverage_percentage=100.0)

    available = sum(1 for it in required if it.availability == Availability.AVAILABLE)
    obtainable = sum(1 for it in required if it.availability == Availability.OBTAINABLE_WITH_EFFORT)
    unavailable = sum(1 for it in required if it.availability == Availability.UNAVAILABLE)

    coverage_pct = ((available + obtainable * 0.5) / total) * 100 if total > 0 else 0.0

    return CoverageMetrics(
        required_total=total,
        required_available=available,
        required_obtainable=obtainable,
        required_unavailable=unavailable,
        coverage_percentage=round(coverage_pct, 1),
    )


def _compute_gap_severity(
    items: list[EvidenceItem], gaps: list[CriticalGap]
) -> GapSeverity:
    """Compute overall gap severity."""
    # Check for blocking gaps
    if any(g.severity == GapSeverity.BLOCKING for g in gaps):
        return GapSeverity.BLOCKING

    # Check for required unavailable items
    required_unavailable = sum(
        1 for it in items
        if it.requirement_level == RequirementLevel.REQUIRED
        and it.availability == Availability.UNAVAILABLE
    )
    if required_unavailable > 0:
        return GapSeverity.BLOCKING

    # Check for manageable gaps
    if gaps or any(
        it.availability == Availability.OBTAINABLE_WITH_EFFORT
        for it in items
        if it.requirement_level == RequirementLevel.REQUIRED
    ):
        return GapSeverity.MANAGEABLE

    return GapSeverity.NONE
