"""
LLM prompt templates for each pipeline module.

Each prompt is designed to produce structured JSON output
conforming to internal_schema.md objects.
"""

# ============================================================
# Module 1: GoalIntake — Goal Summarization
# ============================================================

GOAL_SUMMARIZATION_SYSTEM = """あなたは投資研究の専門家です。ユーザーの投資目標を簡潔に要約してください。"""

GOAL_SUMMARIZATION_USER = """以下のユーザーの投資目標を2文以内の日本語で要約してください。
技術用語は避け、何を検証したいかを明確にしてください。

投資目標: {goal_text}

要約（2文以内）:"""

# ============================================================
# Module 2: DomainFramer — Archetype Classification
# ============================================================

DOMAIN_FRAMING_SYSTEM = """あなたは投資戦略のリサーチ設計者です。
ユーザーの投資目標を分析し、戦略のアーキタイプを分類し、検証可能な仮説に分解してください。
出力は必ず以下のJSON形式にしてください。"""

DOMAIN_FRAMING_USER = """以下の投資目標について、戦略フレーミングを行ってください。

## 投資目標
原文: {raw_goal}
要約: {goal_summary}
成功定義: {success_definition}
リスク許容度: {risk_preference}
除外条件: {must_not_do}

## 指示

以下のJSON形式で回答してください。

```json
{{
  "archetype": "<FACTOR | STAT_ARB | EVENT | MACRO | ML_SIGNAL | ALT_DATA | HYBRID | UNCLASSIFIED>",
  "reframed_problem": "<この目標を検証可能な研究課題として再定義した文>",
  "core_hypothesis": "<中核的な仮説を1文で>",
  "testable_claims": [
    {{
      "claim_id": "TC-01",
      "layer": "premise",
      "claim": "<前提となる主張>",
      "falsification_condition": "<この主張が偽であると判定できる条件>"
    }},
    {{
      "claim_id": "TC-02",
      "layer": "core",
      "claim": "<核心的な主張>",
      "falsification_condition": "<反証条件>"
    }},
    {{
      "claim_id": "TC-03",
      "layer": "practical",
      "claim": "<実用上の主張>",
      "falsification_condition": "<反証条件>"
    }}
  ],
  "critical_assumptions": ["<仮定1>", "<仮定2>"],
  "regime_dependencies": ["<相場環境への依存1>", "<相場環境への依存2>"],
  "comparable_known_approaches": [
    {{
      "name": "<既知のアプローチ名>",
      "relevance": "<関連性の説明>",
      "known_outcome": "<既知の結果>"
    }}
  ]
}}
```

## ルール
- archetype は上記8つから必ず1つ選ぶ
- testable_claims は premise, core, practical の各 layer に最低1つ
- 各 claim には falsification_condition を必ず含める
- regime_dependencies は最低2つ（投資戦略は必ず相場環境に依存する）
- comparable_known_approaches は最低1つ"""

# ============================================================
# Module 4: CandidateGenerator
# ============================================================

CANDIDATE_GENERATION_SYSTEM = """あなたは投資戦略の設計者です。
与えられたリサーチフレームに基づき、検証対象となる戦略候補を複数生成してください。
候補はそれぞれ明確に異なるアプローチでなければなりません。"""

CANDIDATE_GENERATION_USER = """以下のリサーチフレームに基づき、3つの戦略候補を生成してください。

## リサーチフレーム
アーキタイプ: {archetype}
再定義された問題: {reframed_problem}
中核仮説: {core_hypothesis}
制約条件: {constraints}
除外条件: {forbidden_behaviors}

## 指示

以下のJSON形式で3つの候補を生成してください。
- 1つ目は baseline（最もシンプルで既知のアプローチ）
- 2つ目は conservative（リスクを抑えた堅実な変種）
- 3つ目は exploratory（より新しい/挑戦的なアプローチ）

```json
{{
  "candidates": [
    {{
      "name": "<日本語の戦略名>",
      "candidate_type": "baseline",
      "summary": "<2文以内の要約>",
      "architecture_outline": ["<ステップ1>", "<ステップ2>", "<ステップ3>"],
      "core_assumptions": [
        {{
          "assumption_id": "CA-01",
          "statement": "<仮定>",
          "failure_impact": "<この仮定が崩れた場合の影響>"
        }}
      ],
      "required_inputs": ["<必要なデータ1>", "<必要なデータ2>"],
      "validation_burden": "low | medium | high",
      "implementation_complexity": "low | medium | high",
      "expected_strengths": ["<強み1>"],
      "expected_weaknesses": ["<弱み1>"],
      "known_risks": ["<リスク1>", "<リスク2>"]
    }}
  ]
}}
```

## ルール
- 各候補は明確に異なるアプローチであること
- known_risks は各候補に最低2つ
- core_assumptions は各候補に最低1つ
- 除外条件に違反する候補は生成しないこと"""

# ============================================================
# Module 5: EvidencePlanner (LLM-assisted gap analysis)
# ============================================================

EVIDENCE_PLANNING_SYSTEM = """あなたは投資データの品質評価の専門家です。
戦略候補に必要なデータの可用性、品質リスク、バイアスを評価してください。"""

EVIDENCE_PLANNING_USER = """以下の戦略候補に必要なエビデンスを計画してください。

## 候補情報
候補名: {candidate_name}
アーキタイプ: {archetype}
必要データ: {required_inputs}
アーキテクチャ: {architecture_outline}

## 指示

以下のJSON形式でエビデンス計画を作成してください。

```json
{{
  "evidence_items": [
    {{
      "item_id": "EI-001",
      "category": "price | fundamental | alternative | macro | sentiment | flow | metadata",
      "description": "<データの説明>",
      "requirement_level": "required | optional | proxy_acceptable",
      "quality_concerns": ["<品質懸念1>"],
      "known_biases": ["<既知バイアス1>"],
      "point_in_time_status": "full | partial | none",
      "reporting_lag_days": null,
      "leakage_risk_patterns": ["<漏洩リスクパターン>"]
    }}
  ],
  "critical_gaps": [
    {{
      "gap_id": "GAP-001",
      "description": "<ギャップの説明>",
      "severity": "manageable | blocking",
      "impact_on_recommendation": "<推奨への影響>",
      "mitigation_option": "<緩和策>"
    }}
  ]
}}
```

## ルール
- price カテゴリは必須（投資戦略には価格データが必要）
- point_in_time_status が none の場合、leakage_risk_patterns に LKG-07 を追加
- 各 evidence_item に最低1つの quality_concerns を含める"""

# ============================================================
# Module 6: ValidationPlanner (LLM-assisted test design)
# ============================================================

VALIDATION_PLANNING_SYSTEM = """あなたは投資戦略のバリデーション設計者です。
戦略候補の検証計画を設計してください。
各テストには必ず失敗条件を含めてください。失敗できないテストはテストではありません。"""

VALIDATION_PLANNING_USER = """以下の戦略候補の検証計画を作成してください。

## 候補情報
候補名: {candidate_name}
候補タイプ: {candidate_type}
アーキタイプ: {archetype}
エビデンスカバレッジ: {coverage_percentage}%
エビデンスギャップ深刻度: {gap_severity}

## 指示

以下のテストタイプから適切なものを選択し、検証計画をJSON形式で作成してください。
- offline_backtest（必須）
- out_of_sample（必須）
- walk_forward（必須）
- regime_split（必須）
- sensitivity（validation_burden が medium 以上の場合）

```json
{{
  "tests": [
    {{
      "test_id": "T-01",
      "test_type": "offline_backtest",
      "purpose": "<このテストの目的>",
      "method_summary": "<手法の要約>",
      "failure_conditions": ["<失敗条件1>", "<失敗条件2>"],
      "estimated_effort": "low | medium | high"
    }}
  ]
}}
```

## ルール
- 各テストに最低1つの failure_conditions を含めること
- failure_conditions は具体的で測定可能であること
- offline_backtest は他のテストの前提条件であること"""
