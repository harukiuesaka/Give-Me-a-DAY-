"""
Presentation Builder — convert internal Recommendation into user-facing output.

Produces:
- CandidateCard (exactly 2, or 1, or 0)
- PresentationContext
- Markdown export

The user sees ONLY these objects. Internal pipeline state is hidden.
"""

import logging
from datetime import datetime

from src.domain.models import (
    Candidate,
    CandidateCard,
    CandidateLabel,
    ConfidenceLabel,
    MaxLoss,
    PresentationContext,
    Recommendation,
    ReturnBand,
)

logger = logging.getLogger(__name__)

# Return band estimates by candidate type (planning-stage heuristic)
# Without backtest data, these are archetype-typical ranges with disclaimers
_RETURN_ESTIMATES = {
    "baseline": {"low": 4.0, "high": 11.0, "loss_low": -18.0, "loss_high": -27.0},
    "conservative": {"low": 3.0, "high": 8.0, "loss_low": -12.0, "loss_high": -20.0},
    "exploratory": {"low": 2.0, "high": 15.0, "loss_low": -20.0, "loss_high": -35.0},
    "hybrid": {"low": 3.0, "high": 12.0, "loss_low": -15.0, "loss_high": -28.0},
}

_RETURN_DISCLAIMER = "計画段階の概算値です。バックテスト未実施のため、実際の期待リターンは異なる可能性があります。過去の実績は将来の成果を保証しません。"


def build_presentation(
    recommendation: Recommendation,
    candidates: list[Candidate],
) -> tuple[list[CandidateCard], PresentationContext]:
    """
    Build user-facing presentation from Recommendation + Candidates.

    Returns:
    - list of CandidateCards (exactly 2, 1, or 0)
    - PresentationContext
    """
    candidate_map = {c.candidate_id: c for c in candidates}

    cards: list[CandidateCard] = []

    # Primary card
    if recommendation.best_candidate_id:
        best = candidate_map.get(recommendation.best_candidate_id)
        if best:
            cards.append(_build_card(best, CandidateLabel.PRIMARY, recommendation))

    # Alternative card
    if recommendation.runner_up_candidate_id:
        runner_up = candidate_map.get(recommendation.runner_up_candidate_id)
        if runner_up:
            cards.append(_build_card(runner_up, CandidateLabel.ALTERNATIVE, recommendation))

    # Presentation context
    context = _build_context(recommendation, candidates, cards)

    return cards, context


def _build_card(
    candidate: Candidate,
    label: CandidateLabel,
    recommendation: Recommendation,
) -> CandidateCard:
    """Build a single CandidateCard."""
    ct = candidate.candidate_type.value
    estimates = _RETURN_ESTIMATES.get(ct, _RETURN_ESTIMATES["baseline"])

    # Key risks: 2-3 items from known_risks
    key_risks = candidate.known_risks[:3]
    if len(key_risks) < 2:
        key_risks.append("市場環境の変化によるパフォーマンス悪化")
    key_risks = key_risks[:3]

    return CandidateCard(
        candidate_id=candidate.candidate_id,
        label=label,
        display_name=candidate.name,
        summary=candidate.summary,
        strategy_approach=candidate.architecture_outline[0] if candidate.architecture_outline else candidate.summary[:50],
        expected_return_band=ReturnBand(
            low_pct=estimates["low"],
            high_pct=estimates["high"],
            basis="計画段階の概算（バックテスト未実施）",
            disclaimer=_RETURN_DISCLAIMER,
        ),
        estimated_max_loss=MaxLoss(
            low_pct=estimates["loss_low"],
            high_pct=estimates["loss_high"],
            basis="同アーキタイプの過去事例に基づく概算",
        ),
        confidence_level=recommendation.confidence_label,
        confidence_reason=recommendation.confidence_explanation,
        key_risks=key_risks,
        stop_conditions_headline="損失が-20%に達した場合、自動的に停止します。3ヶ月連続でベンチマークを下回った場合も停止します。",
    )


def _build_context(
    recommendation: Recommendation,
    candidates: list[Candidate],
    cards: list[CandidateCard],
) -> PresentationContext:
    """Build PresentationContext."""
    total = len(candidates)
    rejected = len(recommendation.rejected_candidate_ids)
    presented = len(cards)

    rejection_headline = None
    if rejected > 0:
        rejection_headline = f"{rejected}方向を棄却。主な理由: 計画段階の評価で相対的に劣位"

    return PresentationContext(
        run_id=recommendation.run_id,
        created_at=datetime.utcnow(),
        validation_summary=f"{total}方向を検討、{rejected}方向を棄却、検証計画を策定済み",
        recommendation_expiry="3ヶ月後に自動で再評価します",
        rejection_headline=rejection_headline,
        caveats=[
            "計画段階の評価であり、バックテスト未実施です",
            "無料データを使用する予定のため、精度に限界があります",
            "過去の実績は将来の成果を保証しません",
        ],
        candidates_evaluated=total,
        candidates_rejected=rejected,
        candidates_presented=presented,
    )


def build_markdown_export(
    cards: list[CandidateCard],
    context: PresentationContext,
    raw_goal: str,
) -> str:
    """Build markdown export per v1_output_spec.md."""
    lines = [
        "# Give Me a DAY — 検証結果",
        "",
        f"**ゴール**: {raw_goal}",
        f"**検証日**: {context.created_at.strftime('%Y-%m-%d')}",
        f"**信頼度**: {_confidence_ja(cards[0].confidence_level) if cards else '該当なし'}",
        "",
    ]

    for card in cards:
        is_primary = card.label == CandidateLabel.PRIMARY
        icon = "⭐ 推奨" if is_primary else "🔄 代替"
        section = "おすすめの方向" if is_primary else "代替の方向"

        lines.extend([
            f"## {section}",
            "",
            f"**{card.display_name}** {icon}",
            "",
            card.summary,
            "",
            f"期待リターン: 年率 {card.expected_return_band.low_pct}〜{card.expected_return_band.high_pct}%（{card.expected_return_band.basis}）",
            f"想定最大損失: {card.estimated_max_loss.low_pct}〜{card.estimated_max_loss.high_pct}%",
            card.expected_return_band.disclaimer,
            "",
            "### 主なリスク",
            "",
        ])
        for risk in card.key_risks:
            lines.append(f"- {risk}")
        lines.extend([
            "",
            "### 停止条件",
            "",
            card.stop_conditions_headline,
            "",
            "---",
            "",
        ])

    lines.extend([
        "## 検証の概要",
        "",
        context.validation_summary,
    ])
    if context.rejection_headline:
        lines.append(context.rejection_headline)
    lines.extend([
        "",
        "## 注意事項",
        "",
    ])
    for caveat in context.caveats:
        lines.append(f"- {caveat}")
    lines.extend([
        "",
        "## 有効期限",
        "",
        context.recommendation_expiry,
        "",
        "---",
        "*Give Me a DAY v1 により生成*",
    ])

    return "\n".join(lines)


def _confidence_ja(level: ConfidenceLabel) -> str:
    return {"low": "低", "medium": "中", "high": "高"}[level.value]
