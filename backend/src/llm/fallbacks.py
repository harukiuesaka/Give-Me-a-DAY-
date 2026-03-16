"""
Template-based fallbacks when LLM is unavailable.

Each fallback produces structurally valid output for the investment research domain.
Quality is lower than LLM output but sufficient for pipeline progression.
"""

from src.domain.models import (
    Archetype,
    Candidate,
    CandidateAssumption,
    CandidateType,
    ClaimLayer,
    ComparableApproach,
    DomainFrame,
    ImplementationComplexity,
    TestableClaim,
    UserIntent,
    ValidationBurden,
)


def fallback_goal_summary(goal_text: str) -> str:
    """Fallback goal summarization: first 200 chars."""
    return goal_text[:200]


def fallback_domain_classification(goal_text: str) -> str:
    """Keyword-based domain classification fallback."""
    return "investment_research"


# ============================================================
# DomainFramer fallback
# ============================================================

# Keyword → archetype mapping for fallback classification
_ARCHETYPE_KEYWORDS: dict[str, list[str]] = {
    "FACTOR": ["モメンタム", "バリュー", "ファクター", "factor", "momentum", "value",
               "クオリティ", "サイズ", "配当", "quality", "size", "dividend", "低ボラ"],
    "STAT_ARB": ["裁定", "ペアトレード", "スプレッド", "arbitrage", "pair", "spread",
                 "共和分", "cointegration", "mean reversion", "平均回帰"],
    "EVENT": ["イベント", "決算", "earnings", "event", "M&A", "IPO", "自社株買い",
              "公募", "配当落ち"],
    "MACRO": ["マクロ", "金利", "GDP", "CPI", "VIX", "macro", "景気", "インフレ",
              "セクターローテーション", "アセットアロケーション", "資産配分"],
    "ML_SIGNAL": ["機械学習", "ML", "ニューラル", "予測モデル", "machine learning",
                  "deep learning", "LSTM", "ランダムフォレスト"],
    "ALT_DATA": ["オルタナティブ", "SNS", "衛星", "alternative data", "NLP",
                 "テキスト", "センチメント"],
}


def fallback_classify_archetype(goal_text: str) -> Archetype:
    """Keyword-based archetype classification."""
    text_lower = goal_text.lower()
    scores: dict[str, int] = {}
    for archetype, keywords in _ARCHETYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[archetype] = score

    if not scores:
        return Archetype.UNCLASSIFIED

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    return Archetype(best)


# Per-archetype fallback claim templates
_ARCHETYPE_CLAIM_TEMPLATES: dict[str, list[dict]] = {
    "FACTOR": [
        {"layer": "premise", "claim": "対象ファクターが対象市場において有意なリターンプレミアムを持つ",
         "falsification": "ファクターの長期リターンプレミアムが統計的に有意でない（p > 0.05）"},
        {"layer": "core", "claim": "ファクターに基づくポートフォリオがベンチマークを上回るリスク調整後リターンを生む",
         "falsification": "バックテスト期間でベンチマーク対比のリスク調整後リターンが負"},
        {"layer": "practical", "claim": "取引コストとリバランス頻度を考慮しても実行可能である",
         "falsification": "取引コスト込みのネットリターンがグロスリターンの50%未満"},
    ],
    "STAT_ARB": [
        {"layer": "premise", "claim": "対象ペアまたはバスケットに統計的に有意な関係性が存在する",
         "falsification": "共和分検定またはADF検定でp > 0.05"},
        {"layer": "core", "claim": "関係性の乖離が予測可能な期間内に回帰する",
         "falsification": "平均回帰期間が想定の2倍以上"},
        {"layer": "practical", "claim": "取引コストとスプレッドを考慮しても収益性がある",
         "falsification": "ネットリターンが負"},
    ],
    "EVENT": [
        {"layer": "premise", "claim": "対象イベントが株価に統計的に有意な影響を与える",
         "falsification": "イベント前後の累積超過リターン(CAR)が統計的に有意でない"},
        {"layer": "core", "claim": "イベント効果が事前に予測可能である",
         "falsification": "事前予測精度がランダム以下"},
        {"layer": "practical", "claim": "イベントの発生頻度とリターンが実行コストを上回る",
         "falsification": "年間の期待リターンが取引コスト合計を下回る"},
    ],
    "MACRO": [
        {"layer": "premise", "claim": "マクロ指標と資産クラスリターンの間に有意な関係がある",
         "falsification": "マクロ変数とリターンの相関が統計的に有意でない"},
        {"layer": "core", "claim": "マクロ指標に基づくアセットアロケーションがベンチマークを上回る",
         "falsification": "バックテストでベンチマーク対比のリターンが負"},
        {"layer": "practical", "claim": "マクロデータの取得遅延を考慮しても実行可能である",
         "falsification": "リアルタイムで利用可能なデータでの結果が事後データの結果と大幅に乖離"},
    ],
}

# Default claims for unmatched archetypes
_DEFAULT_CLAIMS = [
    {"layer": "premise", "claim": "提案された投資アプローチに理論的根拠がある",
     "falsification": "既存の学術研究で類似アプローチが否定されている"},
    {"layer": "core", "claim": "過去データでの検証でベンチマークを上回る",
     "falsification": "バックテストでベンチマーク対比のリターンが負"},
    {"layer": "practical", "claim": "コストとリスクを考慮して実行可能である",
     "falsification": "取引コスト込みのネットリターンが負"},
]


def fallback_domain_frame(intent: UserIntent) -> DomainFrame:
    """Generate a DomainFrame without LLM, using templates."""
    archetype = fallback_classify_archetype(intent.raw_goal)

    claim_templates = _ARCHETYPE_CLAIM_TEMPLATES.get(
        archetype.value, _DEFAULT_CLAIMS
    )
    claims = [
        TestableClaim(
            claim_id=f"TC-{i+1:02d}",
            layer=ClaimLayer(t["layer"]),
            claim=t["claim"],
            falsification_condition=t["falsification"],
        )
        for i, t in enumerate(claim_templates)
    ]

    # Regime dependencies — all investment strategies have these
    regime_deps = ["市場トレンドの方向性（上昇/下降/横ばい）", "ボラティリティ環境（高/低）"]
    if archetype == Archetype.MACRO:
        regime_deps.append("金利サイクルの位置")
    if archetype == Archetype.FACTOR:
        regime_deps.append("ファクタープレミアムの持続性")

    # Comparable approaches
    comparables = _get_fallback_comparables(archetype)

    return DomainFrame(
        run_id=intent.run_id,
        archetype=archetype,
        reframed_problem=f"{intent.user_goal_summary}は、過去データと統計的検証により実行可能かどうか",
        core_hypothesis=f"{intent.user_goal_summary}が統計的に有意なリターンを生む",
        testable_claims=claims,
        critical_assumptions=[
            "過去のパターンが将来にある程度持続する",
            "使用するデータが十分な品質を持つ",
            "取引コストが想定範囲内に収まる",
        ],
        regime_dependencies=regime_deps,
        comparable_known_approaches=comparables,
    )


def _get_fallback_comparables(archetype: Archetype) -> list[ComparableApproach]:
    """Get comparable known approaches per archetype."""
    comparables_map: dict[str, list[dict]] = {
        "FACTOR": [
            {"name": "Fama-French 3ファクターモデル",
             "relevance": "ファクター投資の基準モデル",
             "known_outcome": "長期ではバリューとサイズプレミアムが存在するが、近年はバリュープレミアムが縮小"},
        ],
        "STAT_ARB": [
            {"name": "ペアトレーディング（共和分ベース）",
             "relevance": "統計的裁定の代表的手法",
             "known_outcome": "2000年代以降、収益性が低下傾向"},
        ],
        "MACRO": [
            {"name": "デュアルモメンタム（Gary Antonacci）",
             "relevance": "マクロベースのアセットアロケーション",
             "known_outcome": "長期では市場を上回るリスク調整後リターンが報告されているが、直近は低迷期あり"},
        ],
        "EVENT": [
            {"name": "決算サプライズ戦略（PEAD）",
             "relevance": "イベントドリブンの代表例",
             "known_outcome": "学術研究で一貫して超過リターンが確認されているが、執行コストで削減される"},
        ],
    }
    entries = comparables_map.get(archetype.value, [
        {"name": "パッシブインデックス投資",
         "relevance": "すべての戦略のベンチマーク",
         "known_outcome": "長期では大多数のアクティブ戦略を上回る"}
    ])
    return [ComparableApproach(**e) for e in entries]


# ============================================================
# CandidateGenerator fallback
# ============================================================

# Per-archetype candidate templates
_ARCHETYPE_CANDIDATE_TEMPLATES: dict[str, list[dict]] = {
    "FACTOR": [
        {
            "name": "単純モメンタム戦略（12ヶ月リターン）",
            "type": "baseline",
            "summary": "過去12ヶ月のリターンに基づきトップ銘柄を選択する古典的なモメンタム戦略。"
                       "学術研究で広く検証されたベースライン。",
            "architecture": ["過去12ヶ月リターンを計算", "上位20%の銘柄を選択", "月次リバランス"],
            "assumptions": [("モメンタム効果が持続する", "モメンタムクラッシュにより大きな損失が発生")],
            "inputs": ["日次株価データ(OHLCV)", "銘柄ユニバース構成情報"],
            "strengths": ["学術研究で広く検証済み", "実装がシンプル"],
            "weaknesses": ["モメンタムクラッシュに脆弱", "トレンド反転時に損失"],
            "risks": ["モメンタムクラッシュリスク", "高回転率による取引コスト"],
            "burden": "low", "complexity": "low",
        },
        {
            "name": "リスク調整モメンタム戦略",
            "type": "conservative",
            "summary": "ボラティリティで調整したモメンタムシグナルを使い、リスクを抑えた堅実な変種。"
                       "過去リターンをボラティリティで割ることで安定性を重視。",
            "architecture": ["過去12ヶ月リターン/ボラティリティを計算", "上位20%を選択",
                             "ポジションサイズをボラティリティ逆数で調整", "月次リバランス"],
            "assumptions": [("ボラティリティ調整がリスク・リターン比を改善する",
                             "低ボラ銘柄がアンダーパフォームする局面で有効性低下")],
            "inputs": ["日次株価データ(OHLCV)", "銘柄ユニバース構成情報"],
            "strengths": ["ドローダウンが小さい傾向", "リスク調整後リターンが改善される可能性"],
            "weaknesses": ["トレンドが強い局面で単純モメンタムに劣る可能性", "計算がやや複雑"],
            "risks": ["低ボラティリティ異常（低ボラ銘柄への集中）", "ボラティリティ推定誤差"],
            "burden": "medium", "complexity": "medium",
        },
        {
            "name": "マルチファクター統合戦略",
            "type": "exploratory",
            "summary": "モメンタムに加えバリュー・クオリティファクターを組み合わせた統合アプローチ。"
                       "単一ファクターの弱点を分散により軽減する。",
            "architecture": ["複数ファクタースコアを計算（モメンタム、バリュー、クオリティ）",
                             "Zスコアで正規化", "複合スコアで銘柄ランキング",
                             "上位20%を選択", "月次リバランス"],
            "assumptions": [("ファクター間の分散効果が有効である",
                             "ファクター同時ドローダウンで分散効果が消失")],
            "inputs": ["日次株価データ(OHLCV)", "財務データ（PBR, ROE等）", "銘柄ユニバース構成情報"],
            "strengths": ["ファクター分散によるリスク低減", "単一ファクターの弱点を緩和"],
            "weaknesses": ["パラメータが多く過学習リスク", "ファクター重み付けの恣意性"],
            "risks": ["全ファクター同時不調のリスク", "過学習リスク", "パラメータチューニング依存"],
            "burden": "high", "complexity": "high",
        },
    ],
}


def fallback_generate_candidates(
    run_id: str,
    archetype: Archetype,
    forbidden_behaviors: list[str],
) -> list[Candidate]:
    """Generate candidates without LLM using archetype templates."""
    templates = _ARCHETYPE_CANDIDATE_TEMPLATES.get(archetype.value)
    if not templates:
        templates = _ARCHETYPE_CANDIDATE_TEMPLATES["FACTOR"]  # Safe default

    candidates = []
    for i, t in enumerate(templates):
        cid = f"{run_id}_C{i+1:02d}"
        candidate = Candidate(
            candidate_id=cid,
            name=t["name"],
            candidate_type=CandidateType(t["type"]),
            summary=t["summary"],
            architecture_outline=t["architecture"],
            core_assumptions=[
                CandidateAssumption(
                    assumption_id=f"{cid}_CA{j+1:02d}",
                    statement=a[0],
                    failure_impact=a[1],
                )
                for j, a in enumerate(t["assumptions"])
            ],
            required_inputs=t["inputs"],
            validation_burden=ValidationBurden(t["burden"]),
            implementation_complexity=ImplementationComplexity(t["complexity"]),
            expected_strengths=t["strengths"],
            expected_weaknesses=t["weaknesses"],
            known_risks=t["risks"],
        )
        candidates.append(candidate)

    return candidates
