"""
LLM client wrapper — stub.

TODO: Round 2 — Anthropic API client with fallback templates.
"""


class LLMClient:
    """Wrapper for Anthropic Claude API. TODO: Round 2."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.available = bool(api_key)

    def summarize_goal(self, goal_text: str) -> str:
        """Summarize a user goal. TODO: Round 2 — LLM call."""
        # Fallback: truncate
        return goal_text[:200]

    def classify_domain(self, goal_text: str) -> str:
        """Classify domain of a goal. TODO: Round 2 — LLM call."""
        raise NotImplementedError("LLM domain classification is a Round 2 target.")
