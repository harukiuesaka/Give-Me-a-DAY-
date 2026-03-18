"""
Approval Controller — explicit approval gate.

No approval = no runtime.

Required confirmations:
- risks_reviewed = true
- stop_conditions_reviewed = true
- paper_run_understood = true (v1: no real money)

All three must be true. No shortcut.
"""

import logging
import uuid
from datetime import datetime

from src.domain.models import (
    Approval,
    PaperRunState,
    Recommendation,
    RuntimeConfig,
    UserConfirmations,
)

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Raised when approval requirements are not met."""
    pass


def validate_confirmations(confirmations: dict[str, bool]) -> UserConfirmations:
    """
    Validate that all required confirmations are true.

    Raises ApprovalError if any confirmation is missing or false.
    """
    required = ["risks_reviewed", "stop_conditions_reviewed", "paper_run_understood"]

    for key in required:
        if not confirmations.get(key, False):
            raise ApprovalError(
                f"確認項目 '{key}' が承認されていません。すべての確認が必要です。"
            )

    return UserConfirmations(
        risks_reviewed=True,
        stop_conditions_reviewed=True,
        paper_run_understood=True,
    )


def create_approval(
    run_id: str,
    candidate_id: str,
    confirmations: UserConfirmations,
    recommendation: Recommendation,
    virtual_capital: float | None = None,
) -> Approval:
    """
    Create an Approval object.

    The candidate_id must match either best_candidate_id or runner_up_candidate_id
    from the recommendation. Users can choose either of the 2 presented candidates.
    """
    # Validate candidate is one of the surfaced candidates
    valid_ids = set()
    if recommendation.best_candidate_id:
        valid_ids.add(recommendation.best_candidate_id)
    if recommendation.runner_up_candidate_id:
        valid_ids.add(recommendation.runner_up_candidate_id)

    if candidate_id not in valid_ids:
        raise ApprovalError(
            f"候補 '{candidate_id}' は推奨された候補ではありません。"
            f"承認可能な候補: {valid_ids}"
        )

    # Build runtime config
    config = RuntimeConfig()
    if virtual_capital is not None and virtual_capital > 0:
        config.initial_virtual_capital = virtual_capital

    return Approval(
        approval_id=f"{run_id}_AP_{uuid.uuid4().hex[:6]}",
        run_id=run_id,
        candidate_id=candidate_id,
        approved_at=datetime.utcnow(),
        user_confirmations=confirmations,
        runtime_config=config,
        re_approval_required=[
            "再評価により候補変更が推奨された場合",
            "停止条件に到達し運用が停止した後の再開",
            "実取引への移行（v1.5）",
        ],
    )


def create_reapproval(
    paper_run_state: PaperRunState,
    confirmations: UserConfirmations,
    candidate_id: str,
) -> Approval:
    """
    Create a new Approval object to resume an existing Paper Run.

    Re-approval is only valid for the same candidate already attached to the Paper Run.
    """
    if candidate_id != paper_run_state.candidate_id:
        raise ApprovalError(
            f"候補 '{candidate_id}' はこの Paper Run の候補ではありません。"
            f"再承認可能な候補: {paper_run_state.candidate_id}"
        )

    run_id = extract_run_id_from_approval_id(paper_run_state.approval_id)
    if not run_id:
        raise ApprovalError("元の承認情報から run_id を特定できません。")

    return Approval(
        approval_id=f"{run_id}_AP_{uuid.uuid4().hex[:6]}",
        run_id=run_id,
        candidate_id=paper_run_state.candidate_id,
        approved_at=datetime.utcnow(),
        user_confirmations=confirmations,
        runtime_config=RuntimeConfig(
            initial_virtual_capital=paper_run_state.current_snapshot.virtual_capital_initial,
        ),
        re_approval_required=[
            "再評価により候補変更が推奨された場合",
            "停止条件に到達し運用が停止した後の再開",
            "実取引への移行（v1.5）",
        ],
    )


def create_changed_candidate_reapproval(
    paper_run_state: PaperRunState,
    confirmations: UserConfirmations,
    candidate_id: str,
) -> Approval:
    """
    Create a new Approval object for a re-evaluating Paper Run that will switch candidates.

    The candidate must differ from the currently running candidate.
    """
    if candidate_id == paper_run_state.candidate_id:
        raise ApprovalError(
            "候補変更の再承認では、現在と異なる候補を指定する必要があります。"
        )

    run_id = extract_run_id_from_approval_id(paper_run_state.approval_id)
    if not run_id:
        raise ApprovalError("元の承認情報から run_id を特定できません。")

    return Approval(
        approval_id=f"{run_id}_AP_{uuid.uuid4().hex[:6]}",
        run_id=run_id,
        candidate_id=candidate_id,
        approved_at=datetime.utcnow(),
        user_confirmations=confirmations,
        runtime_config=RuntimeConfig(
            initial_virtual_capital=paper_run_state.current_snapshot.virtual_capital_initial,
        ),
        re_approval_required=[
            "再評価により候補変更が推奨された場合",
            "停止条件に到達し運用が停止した後の再開",
            "実取引への移行（v1.5）",
        ],
    )


def extract_run_id_from_approval_id(approval_id: str) -> str | None:
    if "_AP_" not in approval_id:
        return None
    return approval_id.rsplit("_AP_", 1)[0]
