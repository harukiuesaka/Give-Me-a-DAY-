"""
Module 2: DomainFramer

Transform UserIntent into DomainFrame:
- Classify strategy archetype
- Reframe goal as testable research problem
- Decompose into falsifiable claims
- Identify regime dependencies and comparable approaches

Uses LLM when available; falls back to template-based classification.
"""

import logging

from src.domain.models import (
    Archetype,
    ClaimLayer,
    ComparableApproach,
    DomainFrame,
    TestableClaim,
    UserIntent,
)
from src.llm.client import LLMClient, LLMUnavailableError
from src.llm.fallbacks import fallback_domain_frame
from src.llm.prompts import DOMAIN_FRAMING_SYSTEM, DOMAIN_FRAMING_USER

logger = logging.getLogger(__name__)


def frame(user_intent: UserIntent) -> DomainFrame:
    """
    Convert UserIntent into DomainFrame.

    Attempts LLM-based framing first. Falls back to template-based
    framing if the LLM is unavailable or returns invalid output.
    """
    client = LLMClient()

    if not client.available:
        logger.info("LLM unavailable — using fallback domain framing")
        return fallback_domain_frame(user_intent)

    try:
        return _llm_frame(client, user_intent)
    except (LLMUnavailableError, Exception) as e:
        logger.warning(f"LLM domain framing failed: {e} — using fallback")
        return fallback_domain_frame(user_intent)


def _llm_frame(client: LLMClient, intent: UserIntent) -> DomainFrame:
    """Use LLM to generate DomainFrame."""
    prompt = DOMAIN_FRAMING_USER.format(
        raw_goal=intent.raw_goal,
        goal_summary=intent.user_goal_summary,
        success_definition=intent.success_definition,
        risk_preference=intent.risk_preference.value,
        must_not_do=", ".join(intent.must_not_do) if intent.must_not_do else "なし",
    )

    data = client.call_json(DOMAIN_FRAMING_SYSTEM, prompt)

    # Parse archetype
    archetype_str = data.get("archetype", "UNCLASSIFIED")
    try:
        archetype = Archetype(archetype_str)
    except ValueError:
        archetype = Archetype.UNCLASSIFIED

    # Parse testable claims
    raw_claims = data.get("testable_claims", [])
    claims = _parse_claims(raw_claims)

    # Ensure minimum: 1 per layer
    claims = _ensure_minimum_claims(claims)

    # Parse regime dependencies (minimum 2)
    regimes = data.get("regime_dependencies", [])
    if len(regimes) < 2:
        regimes = ["市場トレンドの方向性（上昇/下降/横ばい）", "ボラティリティ環境（高/低）"]

    # Parse comparable approaches
    raw_comparables = data.get("comparable_known_approaches", [])
    comparables = [
        ComparableApproach(
            name=c.get("name", "不明"),
            relevance=c.get("relevance", ""),
            known_outcome=c.get("known_outcome", "不明"),
        )
        for c in raw_comparables
        if isinstance(c, dict) and c.get("name")
    ]

    return DomainFrame(
        run_id=intent.run_id,
        archetype=archetype,
        reframed_problem=data.get("reframed_problem", f"{intent.user_goal_summary}の検証可能性"),
        core_hypothesis=data.get("core_hypothesis", f"{intent.user_goal_summary}が有意なリターンを生む"),
        testable_claims=claims,
        critical_assumptions=data.get("critical_assumptions", [
            "過去のパターンが将来にある程度持続する",
            "使用するデータが十分な品質を持つ",
        ]),
        regime_dependencies=regimes,
        comparable_known_approaches=comparables,
    )


def _parse_claims(raw_claims: list) -> list[TestableClaim]:
    """Parse raw claim dicts into TestableClaim objects."""
    claims = []
    for i, c in enumerate(raw_claims):
        if not isinstance(c, dict):
            continue
        try:
            layer = ClaimLayer(c.get("layer", "core"))
        except ValueError:
            layer = ClaimLayer.CORE

        claim_text = c.get("claim", "")
        falsification = c.get("falsification_condition", "")
        if not claim_text or not falsification:
            continue

        claims.append(TestableClaim(
            claim_id=c.get("claim_id", f"TC-{i+1:02d}"),
            layer=layer,
            claim=claim_text,
            falsification_condition=falsification,
        ))
    return claims


def _ensure_minimum_claims(claims: list[TestableClaim]) -> list[TestableClaim]:
    """Ensure at least 1 claim per layer (premise, core, practical)."""
    layers_present = {c.layer for c in claims}

    defaults = {
        ClaimLayer.PREMISE: TestableClaim(
            claim_id="TC-D01",
            layer=ClaimLayer.PREMISE,
            claim="この戦略の前提となる市場特性が存在する",
            falsification_condition="前提となる市場特性が統計的に確認できない",
        ),
        ClaimLayer.CORE: TestableClaim(
            claim_id="TC-D02",
            layer=ClaimLayer.CORE,
            claim="この戦略がベンチマークを上回るリスク調整後リターンを生む",
            falsification_condition="バックテスト期間でリスク調整後リターンがベンチマーク以下",
        ),
        ClaimLayer.PRACTICAL: TestableClaim(
            claim_id="TC-D03",
            layer=ClaimLayer.PRACTICAL,
            claim="取引コストとリスク管理を考慮した実装が可能である",
            falsification_condition="取引コスト込みのネットリターンが負",
        ),
    }

    for layer, default_claim in defaults.items():
        if layer not in layers_present:
            claims.append(default_claim)

    return claims
