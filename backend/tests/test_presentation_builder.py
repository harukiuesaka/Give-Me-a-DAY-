"""Tests for PresentationBuilder module (Round 2.5)."""

from src.domain.models import (
    Audit,
    AuditStatus,
    Candidate,
    CandidateAssumption,
    CandidateCard,
    CandidateLabel,
    CandidateType,
    ConfidenceLabel,
    CriticalCondition,
    ExpiryType,
    ImplementationComplexity,
    OpenUnknown,
    PresentationContext,
    RankingLogicItem,
    Recommendation,
    RecommendationExpiry,
    ValidationBurden,
)
from src.pipeline.presentation_builder import (
    build_markdown_export,
    build_presentation,
)


def _make_recommendation() -> Recommendation:
    return Recommendation(
        run_id="run_pres_test",
        best_candidate_id="C01",
        runner_up_candidate_id="C02",
        rejected_candidate_ids=["C03"],
        ranking_logic=[
            RankingLogicItem(comparison_axis=f"axis{i}", best_assessment="b", runner_up_assessment="r", verdict="v")
            for i in range(3)
        ],
        open_unknowns=[
            OpenUnknown(unknown_id="OU-01", description="d", impact_if_resolved_positively="p",
                        impact_if_resolved_negatively="n", resolution_method="m")
        ],
        critical_conditions=[
            CriticalCondition(condition_id="CC-01", statement="s", verification_method="v",
                              verification_timing="t", source="s")
        ],
        confidence_label=ConfidenceLabel.MEDIUM,
        confidence_explanation="説明",
        recommendation_expiry=RecommendationExpiry(type=ExpiryType.TIME_BASED, description="3ヶ月後"),
    )


def _make_candidate(cid: str, ctype: CandidateType) -> Candidate:
    return Candidate(
        candidate_id=cid,
        name=f"Candidate {cid}",
        candidate_type=ctype,
        summary=f"Summary for {cid}",
        architecture_outline=["アーキテクチャ概要"],
        core_assumptions=[
            CandidateAssumption(assumption_id=f"{cid}-A1", statement="前提", failure_impact="影響")
        ],
        validation_burden=ValidationBurden.MEDIUM,
        implementation_complexity=ImplementationComplexity.MEDIUM,
        known_risks=["リスク1", "リスク2"],
    )


def _make_audit(
    cid: str,
    *,
    status: AuditStatus = AuditStatus.PASSED_WITH_WARNINGS,
    residual_risks: list[str] | None = None,
    rejection_reason: str | None = None,
) -> Audit:
    return Audit(
        candidate_id=cid,
        audit_status=status,
        residual_risks=residual_risks or ["監査リスク1", "監査リスク2"],
        surviving_assumptions=["前提"] if status != AuditStatus.REJECTED else [],
        rejection_reason=rejection_reason,
    )


class TestBuildPresentation:
    def test_returns_exactly_2_cards(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
            _make_candidate("C03", CandidateType.EXPLORATORY),
        ]
        cards, context = build_presentation(rec, candidates)
        assert len(cards) == 2

    def test_primary_and_alternative_labels(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        cards, _ = build_presentation(rec, candidates)
        labels = {c.label for c in cards}
        assert CandidateLabel.PRIMARY in labels
        assert CandidateLabel.ALTERNATIVE in labels

    def test_cards_are_valid_models(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        cards, _ = build_presentation(rec, candidates)
        for card in cards:
            assert isinstance(card, CandidateCard)
            assert card.expected_return_band is not None
            assert card.estimated_max_loss is not None
            assert 2 <= len(card.key_risks) <= 3

    def test_context_is_valid(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
            _make_candidate("C03", CandidateType.EXPLORATORY),
        ]
        _, context = build_presentation(rec, candidates)
        assert isinstance(context, PresentationContext)
        assert context.candidates_evaluated == 3
        assert context.candidates_rejected == 1
        assert context.candidates_presented == 2

    def test_return_band_has_disclaimer(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        cards, _ = build_presentation(rec, candidates)
        for card in cards:
            assert "バックテスト未実施" in card.expected_return_band.disclaimer

    def test_key_risks_prefer_audit_residual_risks(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        audits = [
            _make_audit("C01", residual_risks=["監査由来リスク1", "監査由来リスク2"]),
            _make_audit("C02", residual_risks=["監査由来リスク3", "監査由来リスク4"]),
        ]

        cards, _ = build_presentation(rec, candidates, audits=audits)
        assert cards[0].key_risks[0].startswith("監査由来")

    def test_rejection_headline_prefers_audit_reason(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
            _make_candidate("C03", CandidateType.EXPLORATORY),
        ]
        audits = [
            _make_audit("C01", status=AuditStatus.PASSED),
            _make_audit("C02", status=AuditStatus.PASSED_WITH_WARNINGS),
            _make_audit(
                "C03",
                status=AuditStatus.REJECTED,
                rejection_reason="C03 はブロッキングなエビデンス不足で棄却されました。追加データが必要です。",
            ),
        ]

        _, context = build_presentation(rec, candidates, audits=audits)
        assert context.rejection_headline is not None
        assert "エビデンス不足" in context.rejection_headline

    def test_zero_survivor_path_returns_no_cards_without_crash(self):
        rec = Recommendation(
            run_id="run_pres_test",
            best_candidate_id=None,
            runner_up_candidate_id=None,
            rejected_candidate_ids=["C01", "C02"],
            ranking_logic=[
                RankingLogicItem(comparison_axis=f"axis{i}", best_assessment="b", runner_up_assessment="r", verdict="v")
                for i in range(3)
            ],
            open_unknowns=[
                OpenUnknown(
                    unknown_id="OU-01",
                    description="d",
                    impact_if_resolved_positively="p",
                    impact_if_resolved_negatively="n",
                    resolution_method="m",
                )
            ],
            critical_conditions=[
                CriticalCondition(
                    condition_id="CC-01",
                    statement="s",
                    verification_method="v",
                    verification_timing="t",
                    source="s",
                )
            ],
            confidence_label=ConfidenceLabel.LOW,
            confidence_explanation="説明",
            recommendation_expiry=RecommendationExpiry(type=ExpiryType.TIME_BASED, description="3ヶ月後"),
        )
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        audits = [
            _make_audit(
                "C01",
                status=AuditStatus.REJECTED,
                rejection_reason="C01 は Paper Run only の境界を超える運用を前提としているため棄却されました。",
            ),
            _make_audit(
                "C02",
                status=AuditStatus.REJECTED,
                rejection_reason="C02 は将来情報に依存する疑いが強いため棄却されました。",
            ),
        ]

        cards, context = build_presentation(rec, candidates, audits=audits)
        assert cards == []
        assert context.candidates_presented == 0
        assert context.rejection_headline is not None
        assert "Paper Run" in context.rejection_headline

    def test_overfitting_rejection_reason_can_surface_in_headline(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
            _make_candidate("C03", CandidateType.EXPLORATORY),
        ]
        audits = [
            _make_audit("C01", status=AuditStatus.PASSED),
            _make_audit("C02", status=AuditStatus.PASSED_WITH_WARNINGS),
            _make_audit(
                "C03",
                status=AuditStatus.REJECTED,
                rejection_reason="C03 は OOS で性能が崩れており過学習リスクが高いため棄却されました。再検証が必要です。",
            ),
        ]

        _, context = build_presentation(rec, candidates, audits=audits)
        assert context.rejection_headline is not None
        assert "OOS" in context.rejection_headline


class TestMarkdownExport:
    def test_produces_markdown(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        cards, context = build_presentation(rec, candidates)
        md = build_markdown_export(cards, context, "テスト目標")
        assert "# Give Me a DAY" in md
        assert "テスト目標" in md
        assert "おすすめの方向" in md
        assert "代替の方向" in md

    def test_markdown_includes_caveats(self):
        rec = _make_recommendation()
        candidates = [
            _make_candidate("C01", CandidateType.BASELINE),
            _make_candidate("C02", CandidateType.CONSERVATIVE),
        ]
        cards, context = build_presentation(rec, candidates)
        md = build_markdown_export(cards, context, "テスト目標")
        assert "注意事項" in md
        assert "バックテスト未実施" in md
