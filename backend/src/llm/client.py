"""
LLM client wrapper for Claude API.

Provides structured calls for each pipeline module with:
- Timeout and exception handling
- Automatic fallback when API key is empty or call fails
- Deterministic-leaning settings (low temperature)
"""

import json
import logging
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency when API key is not set
_anthropic_client = None


def _get_client():
    """Lazy-init Anthropic client."""
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return _anthropic_client
    except Exception as e:
        logger.warning(f"Failed to initialize Anthropic client: {e}")
        return None


class LLMClient:
    """Wrapper for Claude API calls used in the planning pipeline."""

    def __init__(self):
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 4096
        self.temperature = 0.3  # Deterministic-leaning

    @property
    def available(self) -> bool:
        return _get_client() is not None

    def call(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a Claude API call. Returns the text response.
        Raises LLMUnavailableError if the API is not available or fails.
        """
        client = _get_client()
        if client is None:
            raise LLMUnavailableError("Anthropic API key not set or client init failed")

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            raise LLMUnavailableError(f"LLM call failed: {e}") from e

    def call_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """
        Make a Claude API call expecting JSON output.
        Parses the response as JSON, with fallback extraction from markdown code blocks.
        """
        raw = self.call(system_prompt, user_prompt)
        return _extract_json(raw)


class LLMUnavailableError(Exception):
    """Raised when the LLM cannot be reached or returns an error."""
    pass


def _extract_json(text: str) -> dict[str, Any]:
    """Extract JSON from LLM response, handling markdown code blocks."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    # Try extracting from ``` ... ``` block
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        candidate = text[start:end].strip()
        return json.loads(candidate)

    # Try finding first { ... } or [ ... ]
    for open_char, close_char in [("{", "}"), ("[", "]")]:
        if open_char in text:
            start = text.index(open_char)
            # Find matching close from the end
            end = text.rindex(close_char) + 1
            return json.loads(text[start:end])

    raise json.JSONDecodeError("No JSON found in LLM response", text, 0)
