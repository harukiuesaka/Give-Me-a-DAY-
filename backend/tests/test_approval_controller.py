"""Tests for ApprovalController module (Round 2.5)."""

import pytest
from datetime import datetime

from src.domain.models import (
    ConfidenceLabel,
    ExpiryType,
    OpenUnknown,
    CriticalCondition,
    PaperRunState,
    CurrentSnapshot,
    RankingLogicItem,
    Recommendation,
    RecommendationExpiry,
    PaperRunStatus,
    UserConfirmations,
)
from src.pipeline.approval_controller import (
    ApprovalError,
    create_approval,
    create_changed_candidate_reapproval,
    create_reapproval,
    validate_confirmations,
)


def _make_recommendation(best_id: str = "C01", runner_up_id: str = "C02") -> Recommendation:
    return Recommendation(
        run_id="run_ap_test",
        best_candidate_id=best_id,
        runner_up_candidate_id=runner_up_id,
        rejected_candidate_ids=["C03"],
        ranking_logic=[
            RankingLogicItem(
                comparison_axis="axis1",
                best_assessment="best",
                runner_up_assessment="runner",
                verdict="verdict",
            ),
            RankingLogicItem(
                comparison_axis="axis2",
                best_assessment="best",
                runner_up_assessment="runner",
                verdict="verdict",
            ),
            RankingLogicItem(
                comparison_axis="axis3",
                best_assessment="best",
                runner_up_assessment="runner",
                verdict="verdict",
            ),
        ],
        open_unknowns=[
            OpenUnknown(
                unknown_id="OU-01",
                description="desc",
                impact_if_resolved_positively="pos",
                impact_if_resolved_negatively="neg",
                resolution_method="method",
            )
        ],
        critical_conditions=[
            CriticalCondition(
                condition_id="CC-01",
                statement="stmt",
                verification_method="method",
                verification_timing="timing",
                source="source",
            )
        ],
        confidence_label=ConfidenceLabel.MEDIUM,
        confidence_explanation="説明",
        recommendation_expiry=RecommendationExpiry(
            type=ExpiryType.TIME_BASED,
            description="3ヶ月後",
        ),
    )


class TestValidateConfirmations:
    def test_all_true_succeeds(self):
        result = validate_confirmations({
            "risks_reviewed": True,
            "stop_conditions_reviewed": True,
            "paper_run_understood": True,
        })
        assert isinstance(result, UserConfirmations)
        assert result.risks_reviewed is True
        assert result.stop_conditions_reviewed is True
        assert result.paper_run_understood is True

    def test_missing_key_raises(self):
        with pytest.raises(ApprovalError):
            validate_confirmations({
                "risks_reviewed": True,
                "stop_conditions_reviewed": True,
                # paper_run_understood missing
            })

    def test_false_value_raises(self):
        with pytest.raises(ApprovalError):
            validate_confirmations({
                "risks_reviewed": True,
                "stop_conditions_reviewed": False,
                "paper_run_understood": True,
            })

    def test_empty_dict_raises(self):
        with pytest.raises(ApprovalError):
            validate_confirmations({})


class TestCreateApproval:
    def _confirmations(self) -> UserConfirmations:
        return UserConfirmations(
            risks_reviewed=True,
            stop_conditions_reviewed=True,
            paper_run_understood=True,
        )

    def test_approve_best_candidate(self):
        rec = _make_recommendation()
        approval = create_approval(
            "run_ap_test", "C01", self._confirmations(), rec
        )
        assert approval.candidate_id == "C01"
        assert approval.run_id == "run_ap_test"

    def test_approve_runner_up(self):
        rec = _make_recommendation()
        approval = create_approval(
            "run_ap_test", "C02", self._confirmations(), rec
        )
        assert approval.candidate_id == "C02"

    def test_reject_invalid_candidate(self):
        rec = _make_recommendation()
        with pytest.raises(ApprovalError):
            create_approval(
                "run_ap_test", "C03", self._confirmations(), rec
            )

    def test_custom_virtual_capital(self):
        rec = _make_recommendation()
        approval = create_approval(
            "run_ap_test", "C01", self._confirmations(), rec,
            virtual_capital=5_000_000,
        )
        assert approval.runtime_config.initial_virtual_capital == 5_000_000

    def test_default_virtual_capital(self):
        rec = _make_recommendation()
        approval = create_approval(
            "run_ap_test", "C01", self._confirmations(), rec,
        )
        assert approval.runtime_config.initial_virtual_capital == 1_000_000

    def test_approval_requires_re_approval_list(self):
        rec = _make_recommendation()
        approval = create_approval(
            "run_ap_test", "C01", self._confirmations(), rec,
        )
        assert len(approval.re_approval_required) > 0


class TestCreateReApproval:
    def _paper_run_state(self) -> PaperRunState:
        return PaperRunState(
            paper_run_id="pr_test",
            approval_id="run_ap_test_AP_old123",
            candidate_id="C01",
            started_at=datetime.utcnow(),
            status=PaperRunStatus.HALTED,
            current_snapshot=CurrentSnapshot(
                day_count=10,
                virtual_capital_initial=1_500_000,
                virtual_capital_current=1_200_000,
            ),
        )

    def test_reapprove_same_candidate(self):
        approval = create_reapproval(
            paper_run_state=self._paper_run_state(),
            confirmations=UserConfirmations(
                risks_reviewed=True,
                stop_conditions_reviewed=True,
                paper_run_understood=True,
            ),
            candidate_id="C01",
        )
        assert approval.run_id == "run_ap_test"
        assert approval.candidate_id == "C01"
        assert approval.runtime_config.initial_virtual_capital == 1_500_000

    def test_reapprove_rejects_different_candidate(self):
        with pytest.raises(ApprovalError):
            create_reapproval(
                paper_run_state=self._paper_run_state(),
                confirmations=UserConfirmations(
                    risks_reviewed=True,
                    stop_conditions_reviewed=True,
                    paper_run_understood=True,
                ),
                candidate_id="C02",
            )

    def test_changed_candidate_reapproval_allows_different_candidate(self):
        approval = create_changed_candidate_reapproval(
            paper_run_state=self._paper_run_state().model_copy(
                update={"status": PaperRunStatus.RE_EVALUATING}
            ),
            confirmations=UserConfirmations(
                risks_reviewed=True,
                stop_conditions_reviewed=True,
                paper_run_understood=True,
            ),
            candidate_id="C02",
        )
        assert approval.run_id == "run_ap_test"
        assert approval.candidate_id == "C02"
        assert approval.runtime_config.initial_virtual_capital == 1_500_000

    def test_changed_candidate_reapproval_rejects_same_candidate(self):
        with pytest.raises(ApprovalError):
            create_changed_candidate_reapproval(
                paper_run_state=self._paper_run_state().model_copy(
                    update={"status": PaperRunStatus.RE_EVALUATING}
                ),
                confirmations=UserConfirmations(
                    risks_reviewed=True,
                    stop_conditions_reviewed=True,
                    paper_run_understood=True,
                ),
                candidate_id="C01",
            )
