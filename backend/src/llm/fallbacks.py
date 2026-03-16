"""
Template-based fallbacks when LLM is unavailable — stub.

TODO: Round 2 — Implement fallback logic for each LLM call.
"""


def fallback_goal_summary(goal_text: str) -> str:
    """Fallback goal summarization without LLM."""
    return goal_text[:200]


def fallback_domain_classification(goal_text: str) -> str:
    """Fallback domain classification without LLM. TODO: Round 2."""
    return "investment_research"  # Conservative default
