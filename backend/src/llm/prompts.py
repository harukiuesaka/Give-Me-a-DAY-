"""
LLM prompt templates — stub.

TODO: Round 2 — All prompt templates for Claude API calls.
"""

# Placeholder prompt templates.
# Each will be a structured prompt for a specific pipeline step.

GOAL_SUMMARIZATION_PROMPT = """
以下のユーザーの投資目標を2文以内で要約してください。

目標: {goal_text}

要約:
"""

DOMAIN_CLASSIFICATION_PROMPT = """
以下のテキストが投資研究に関するものかどうかを判定してください。
"investment_research" または "out_of_scope" で回答してください。

テキスト: {goal_text}

判定:
"""
