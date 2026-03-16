"""
Module 1: GoalIntake

Accept user's natural-language investment goal and produce a valid UserIntent.
Follows technical_design.md Module 1 specification.

Round 1: Minimal implementation using template-based processing (no LLM).
"""

from datetime import datetime

from src.api.schemas import CreateRunRequest
from src.domain.models import (
    RiskPreference,
    TimeHorizonPreference,
    UserIntent,
)


# Domain keywords for basic investment domain classification
_INVESTMENT_KEYWORDS = [
    "株", "投資", "戦略", "モメンタム", "ファクター", "リターン",
    "ポートフォリオ", "リスク", "バリュー", "market", "stock",
    "investment", "strategy", "factor", "momentum", "equity",
    "trading", "hedge", "alpha", "backtest", "quant",
    "日経", "TOPIX", "S&P", "配当", "運用", "資産",
]


class DomainOutOfScopeError(Exception):
    """Raised when the user goal is not investment research."""
    pass


def classify_domain(goal_text: str) -> str:
    """
    Check if the goal is investment-related.
    v1: keyword-based classification.
    TODO: Round 2 — LLM-based classification.
    """
    text_lower = goal_text.lower()
    for keyword in _INVESTMENT_KEYWORDS:
        if keyword.lower() in text_lower:
            return "investment_research"
    raise DomainOutOfScopeError(
        f"Goal does not appear to be investment research: '{goal_text[:100]}...'"
    )


def process_goal_intake(run_id: str, request: CreateRunRequest) -> UserIntent:
    """
    Process raw user input into a valid UserIntent.

    Round 1: Template-based processing without LLM.
    TODO: Round 2 — Add LLM-based goal summarization.
    """
    # 1. Domain check
    domain = classify_domain(request.goal)

    # 2. Summarize goal (template-based for Round 1)
    user_goal_summary = request.goal[:200]  # TODO: LLM summarization

    # 3. Parse risk preference
    risk_map = {
        "very_low": RiskPreference.VERY_LOW,
        "low": RiskPreference.LOW,
        "medium": RiskPreference.MEDIUM,
        "high": RiskPreference.HIGH,
    }
    risk_pref = risk_map.get(request.risk or "medium", RiskPreference.MEDIUM)

    # 4. Parse time horizon
    horizon_map = {
        "fast": TimeHorizonPreference.FAST,
        "one_day": TimeHorizonPreference.ONE_DAY,
        "one_week": TimeHorizonPreference.ONE_WEEK,
        "one_month": TimeHorizonPreference.ONE_MONTH,
        "quality_over_speed": TimeHorizonPreference.QUALITY_OVER_SPEED,
    }
    time_horizon = horizon_map.get(
        request.time_horizon or "one_week", TimeHorizonPreference.ONE_WEEK
    )

    # 5. Build open uncertainties
    uncertainties: list[str] = []
    success_definition = request.success_criteria or ""
    if not success_definition:
        uncertainties.append("success criteria not provided — system will use domain defaults")
        success_definition = _default_success_definition(risk_pref)
    if request.risk is None:
        uncertainties.append("risk preference defaulted to medium")
    if request.time_horizon is None:
        uncertainties.append("time horizon defaulted to one_week")

    # 6. Build and validate UserIntent
    return UserIntent(
        run_id=run_id,
        created_at=datetime.utcnow(),
        raw_goal=request.goal,
        domain=domain,
        user_goal_summary=user_goal_summary,
        success_definition=success_definition,
        risk_preference=risk_pref,
        time_horizon_preference=time_horizon,
        must_not_do=request.exclusions,
        available_inputs=[],
        open_uncertainties=uncertainties,
    )


def _default_success_definition(risk: RiskPreference) -> str:
    """Generate default success definition based on risk preference."""
    defaults = {
        RiskPreference.VERY_LOW: "年率3-5%のリターンを低リスクで達成する",
        RiskPreference.LOW: "年率5-8%のリターンをベンチマーク以下のリスクで達成する",
        RiskPreference.MEDIUM: "年率8-12%のリターンをベンチマーク程度のリスクで達成する",
        RiskPreference.HIGH: "年率12%以上のリターンを高リスク許容で追求する",
    }
    return defaults.get(risk, defaults[RiskPreference.MEDIUM])
