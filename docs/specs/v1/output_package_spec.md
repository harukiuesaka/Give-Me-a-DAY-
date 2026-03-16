# Give Me a DAY v1 — Output Package Specification

**Document type**: Product output specification
**Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
**Version**: v1 draft
**Status**: Design phase — pre-implementation
**Upstream dependency**: v1_core_loop_spec.md

---

## Design Principle

Give Me a DAY の最終出力は「回答」ではない。**判断材料のパッケージ**である。

ユーザーが受け取るのは：
- 何が検討されたか
- 何が棄却されたか、なぜか
- 何が推奨されるか、どの条件下でか
- 何がまだわかっていないか
- 次に自分が何をすべきか

「これが正解です」という出力は、このプロダクトの設計上ありえない。

---

## Output Package 全体構造

```
Recommendation Package
├── 1. Executive Summary
├── 2. Goal Understanding
├── 3. Research Framing
├── 4. Candidate Comparison
│   ├── 4a. Candidate Briefs (per candidate)
│   └── 4b. Comparison Matrix
├── 5. Evidence Assessment
├── 6. Validation Plans
├── 7. Rejection Report
├── 8. Recommendation
│   ├── 8a. Best Candidate (conditional)
│   ├── 8b. Runner-up
│   └── 8c. Conditions & Unknowns
├── 9. Next Steps
└── 10. Re-evaluation Triggers
```

---

## 1. Executive Summary

### 目的
推奨パッケージ全体の要点を1画面で把握させる。ユーザーがここだけ読んでも「何が推奨されたか」「どの程度信頼できるか」「何が未解決か」がわかる状態。

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|---|------|
| run_id | string | このパッケージの一意識別子 |
| created_at | ISO-8601 | 生成日時 |
| goal_oneliner | string | ユーザーのゴールを1文で要約 |
| recommendation_headline | string | 推奨内容を1文で。best_candidate_id = null の場合は「現時点で推奨可能な候補なし」 |
| confidence_label | low / medium / high | 機械的に算出。計画段階では low か medium がほぼ全て |
| confidence_rationale | string | なぜこの confidence か。2–3文 |
| candidates_evaluated | int | 評価した候補数 |
| candidates_rejected | int | 棄却した候補数 |
| critical_conditions_count | int | 推奨を無効化しうる条件の数 |
| open_unknowns_count | int | 未解決の不確実性の数 |
| recommendation_expiry | string | 推奨の有効期限（時間/イベント/証拠ベース） |

### 非専門ユーザー向け表示
信号機モデルで表示する。

- 🟢 **推奨あり・条件少（confidence: medium 以上、critical_conditions ≤ 2）**: 「条件付きで推奨できる方向性があります」
- 🟡 **推奨あり・条件多 or confidence: low**: 「方向性はありますが、確認すべき点が多く残っています」
- 🔴 **推奨なし（best_candidate_id = null）**: 「現時点では推奨できる方向がありません。理由と次のステップを確認してください」

信号機の色だけで判断させない。必ず1文の説明を付ける。

### Builder 向け表示
全フィールドをそのまま JSON で公開。加えて、各フィールドから対応する詳細セクションへのアンカーリンク。

---

## 2. Goal Understanding

### 目的
「あなたのゴールをこう理解しました」をユーザーに確認させる。ここでの認識齟齬は全下流に伝播する。

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|---|------|
| raw_goal | string | ユーザーの原文（そのまま） |
| interpreted_goal | string | システムが解釈した構造化ゴール |
| success_definition | string | 「何をもって成功とするか」の明示定義 |
| risk_preference | enum | very_low / low / medium / high |
| time_horizon | enum | fast / one_day / one_week / one_month / quality_over_speed |
| constraints_summary | string[] | ユーザーが示した制約の一覧 |
| must_not_do | string[] | 明示的な禁止事項 |
| open_uncertainties | string[] | Goal Intake 時点で確定できなかった事項 |

### 非専門ユーザー向け表示
対話形式で提示。

```
あなたのゴール:
「{raw_goal}」

私たちの理解:
{interpreted_goal}

成功の定義:
{success_definition}

リスクの許容度: {risk_preference_label}
時間軸: {time_horizon_label}

制約:
- {constraints_summary[0]}
- {constraints_summary[1]}
...

まだ確定していないこと:
- {open_uncertainties[0]}
...
```

「まだ確定していないこと」を明示的に見せることが重要。隠さない。

### Builder 向け表示
User Intent Object の全フィールドをそのまま表示。open_uncertainties が下流のどのステップに影響するかのトレーサビリティマップを付加。

---

## 3. Research Framing

### 目的
ユーザーのゴールが「検証問題」としてどう再定義されたかを示す。「作りたい」から「検証すべき」への変換の透明性を担保する。

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|---|------|
| reframed_problem | string | 検証可能な問題としての再定義文 |
| core_hypothesis | string | 中核仮説の1文表現 |
| testable_claims | object[] | 分解された検証可能な主張。各項目に `claim`, `falsification_condition` を含む |
| critical_assumptions | string[] | この問題定義が依拠する前提 |
| regime_dependencies | string[] | どの市場レジーム前提で議論しているか |
| comparable_known_approaches | object[] | 類似する既知手法。各項目に `name`, `relevance`, `known_outcome` を含む |

### 非専門ユーザー向け表示

```
あなたのゴールを検証問題として再定義すると:
「{reframed_problem}」

核心の仮説:
「{core_hypothesis}」

この仮説を検証するために確認すべきこと:
1. {testable_claims[0].claim}
   → これが否定される条件: {testable_claims[0].falsification_condition}
2. ...

この分析が前提としていること:
- {critical_assumptions[0]}
- ...

似たアプローチで過去に知られていること:
- {comparable_known_approaches[0].name}: {comparable_known_approaches[0].known_outcome}
```

**falsification_condition（棄却条件）を必ず見せる。** ユーザーに「この仮説は壊れうる」ことを最初から意識させる。

### Builder 向け表示
Domain Frame Object の全フィールド + Research Spec Object の assumption_space, evidence_requirements, validation_requirements を展開表示。

---

## 4. Candidate Comparison

### 目的
検討された候補の全体像と、候補間の比較を透明に提示する。「なぜこの候補が選ばれたか」ではなく「何と比較して選ばれたか」が主題。

### 4a. Candidate Briefs（候補ごと）

各候補について:

| フィールド | 型 | 説明 |
|-----------|---|------|
| candidate_id | string | 候補識別子 |
| name | string | 候補の短い名前 |
| candidate_type | enum | baseline / conservative / exploratory / hybrid |
| status | enum | recommended / runner_up / rejected |
| summary | string | 2–3文の概要 |
| core_approach | string | アプローチの核心を1文で |
| core_assumptions | string[] | この候補固有の前提 |
| expected_strengths | string[] | 想定される強み |
| expected_weaknesses | string[] | 想定される弱み |
| known_risks | string[] | 既知のリスク |
| validation_burden | enum | low / medium / high |
| implementation_complexity | enum | low / medium / high |
| audit_summary | string | Audit 結果の要約（2–3文） |
| rejection_reason | string / null | 棄却された場合の理由 |

### 4b. Comparison Matrix

全候補を同一軸で並べる表。

| 比較軸 | 型 | 説明 |
|--------|---|------|
| metrics | string[] | 比較に使用した評価軸の一覧 |
| matrix | object | candidate_id × metric の値マップ |
| baseline_reference | string | どの候補が baseline か |
| notes | string | 比較上の注意事項 |

**比較軸（v1 固定）**:
1. 検証可能性（Validation feasibility）: 現在の evidence で検証がどの程度可能か
2. 前提の堅牢性（Assumption robustness）: 前提が崩れた場合のダメージ
3. 実装複雑度（Implementation complexity）
4. レジーム依存度（Regime sensitivity）: 特定市場環境への依存度
5. 検証コスト（Validation cost）: 検証に必要な時間・データ・労力
6. 既知手法との距離（Novelty vs known approaches）: 既知の検証済み手法からの乖離度

### 非専門ユーザー向け表示

候補を「カード」として並べ、各カードに:
- 候補名
- タイプラベル（「基準案」「堅実案」「挑戦案」）
- ステータスバッジ（推奨 / 次点 / 棄却）
- 強み・弱みの箇条書き（各最大3項目）
- 棄却候補には棄却理由を赤字で明示

Comparison Matrix は簡易レーダーチャートまたは棒グラフで表示。軸名は日本語のわかりやすい表現に変換。

**棄却候補を非表示にしない。** 棄却情報はプロダクト価値の一部。デフォルト表示。折りたたみは許容するが、存在を隠さない。

### Builder 向け表示
Candidate Object 全フィールド + Comparison Matrix の生データ（JSON）。各候補の architecture_outline を展開表示。Audit Object へのリンク。

---

## 5. Evidence Assessment

### 目的
推奨候補の検証に必要な証拠が「どの程度揃っているか」を示す。証拠の充足度がユーザーの次のアクションを決める。

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|---|------|
| evidence_coverage | object | { required_total, required_available, required_obtainable, required_unavailable } |
| coverage_percentage | number | required_available / required_total × 100 |
| critical_gaps | object[] | 各項目に `description`, `severity`, `impact_on_recommendation`, `mitigation_option` |
| proxy_data_used | object[] | 代替データの使用箇所。各項目に `original`, `proxy`, `quality_loss_estimate` |
| bias_warnings | object[] | 検出されたデータバイアス。各項目に `evidence_item`, `bias_type`, `severity`, `mitigation` |

### 非専門ユーザー向け表示

```
証拠の充足度: {coverage_percentage}%

必要なデータのうち:
  ✅ 入手済み: {required_available} 件
  🔶 取得可能（要対応）: {required_obtainable} 件
  ❌ 入手困難: {required_unavailable} 件
```

critical_gaps がある場合:
```
⚠️ 重要な証拠の欠落:
- {critical_gaps[0].description}
  → 推奨への影響: {critical_gaps[0].impact_on_recommendation}
  → 対処法: {critical_gaps[0].mitigation_option}
```

proxy_data_used がある場合:
```
📌 代替データの使用:
- {proxy_data_used[0].original} の代わりに {proxy_data_used[0].proxy} を使用
  → 品質への影響: {proxy_data_used[0].quality_loss_estimate}
```

bias_warnings がある場合:
```
⚠️ データバイアスの警告:
- {bias_warnings[0].bias_type}: {bias_warnings[0].evidence_item}
```

### Builder 向け表示
Evidence Plan Object の全フィールド。各 evidence_item の temporal_coverage, quality_concerns, known_biases を展開。availability ステータスのフィルタリングビュー。

---

## 6. Validation Plans

### 目的
推奨候補（と runner-up）に対し、「どうやって検証するか」の具体的計画を提示する。ユーザーが次に実行すべきテストの設計図。

### 必須フィールド（推奨候補 + runner-up の各候補につき）

| フィールド | 型 | 説明 |
|-----------|---|------|
| candidate_id | string | 対象候補 |
| plan_completeness | enum | complete / partial_due_to_evidence_gaps / minimal |
| test_sequence | object[] | 順序付きテスト一覧 |

各テスト:

| フィールド | 型 | 説明 |
|-----------|---|------|
| test_id | string | テスト識別子 |
| test_type | enum | offline_backtest / walk_forward / out_of_sample / regime_split / stress_test / sensitivity / paper_run / monte_carlo |
| purpose | string | なぜこのテストが必要か。1文 |
| method_summary | string | テスト方法の要約 |
| required_data | string[] | このテストに必要なデータ |
| metrics | object[] | 各メトリクスに `name`, `pass_threshold`, `fail_threshold` |
| failure_conditions | string[] | このテストの失敗条件 |
| estimated_effort | enum | low / medium / high |
| prerequisites | string[] | 先行テストの pass が必要な場合 |

### 非専門ユーザー向け表示

テストを「段階」として見せる。ステップバイステップのチェックリスト形式。

```
検証計画: {candidate_name}
計画の完成度: {plan_completeness_label}

Step 1: {test_sequence[0].test_type_label}
  目的: {test_sequence[0].purpose}
  方法: {test_sequence[0].method_summary}
  成功基準: {metrics の pass_threshold を自然言語化}
  失敗条件: {failure_conditions を自然言語化}
  必要な労力: {estimated_effort_label}

Step 2: ...
（Step 1 が成功した場合のみ進む）
```

**failure_conditions を省略しない。** テストの意味は「何をもって失敗とするか」にある。

### Builder 向け表示
Validation Plan Object の全フィールド + comparison_matrix。各テストの metrics を表形式で展開。test_sequence のDAG（依存関係グラフ）を表示。

---

## 7. Rejection Report

### 目的
棄却された候補とその理由を明示する。**棄却情報はプロダクト価値の中核。** ユーザーが「なぜこの方向はダメなのか」を理解することで、将来の意思決定品質が上がる。

### 必須フィールド（棄却候補ごと）

| フィールド | 型 | 説明 |
|-----------|---|------|
| candidate_id | string | 棄却された候補 |
| candidate_name | string | 候補名 |
| candidate_type | enum | baseline / conservative / exploratory / hybrid |
| rejection_reason | string | 棄却理由の構造化テキスト（3文以上: 何が問題 → なぜ致命的 → 修正可能性） |
| disqualifying_issues | object[] | 棄却を決定した issue の一覧 |
| non_disqualifying_issues | object[] | 棄却原因ではないが発見された他の問題 |
| salvageable_elements | string[] | この候補から再利用可能な要素（あれば） |
| lesson | string | この棄却から得られる教訓。1–2文 |

各 issue:

| フィールド | 型 | 説明 |
|-----------|---|------|
| category | enum | assumption / evidence_gap / leakage_risk / complexity / realism / observability / regime_dependency / overfitting_risk / cost_assumption / recommendation_risk |
| title | string | 問題の見出し |
| explanation | string | 問題の説明（2文以上） |
| severity | enum | low / medium / high / critical |

### 非専門ユーザー向け表示

```
❌ 棄却: {candidate_name}（{candidate_type_label}）

理由:
{rejection_reason}

致命的な問題:
1. [{category_label}] {disqualifying_issues[0].title}
   {disqualifying_issues[0].explanation}

2. ...

この候補から学べること:
{lesson}
```

棄却候補はデフォルトで展開表示（折りたたみは2候補目以降）。1つ目の棄却候補は常に見せる。

### Builder 向け表示
Audit Object の全フィールド。各 issue の severity × category マトリクス表示。salvageable_elements のタグ付き一覧。

---

## 8. Recommendation

### 目的
条件付きで最良候補を提示する。「最良」が無条件でないことを構造的に保証する。

### 8a. Best Candidate（条件付き推奨）

| フィールド | 型 | 説明 |
|-----------|---|------|
| candidate_id | string / null | 推奨候補。null = 推奨なし |
| candidate_name | string / null | 推奨候補名 |
| recommendation_statement | string | 推奨文。必ず条件節を含む。「{conditions}の条件下で、{candidate_name}を推奨する」の形式 |
| ranking_logic | string[] | なぜこの候補が best か。比較軸ごとの根拠。最低3軸 |
| surviving_assumptions | string[] | Audit を通過したが残存する前提 |
| residual_risks | string[] | 推奨候補に残るリスク |
| confidence_label | low / medium / high | 機械的算出 |
| confidence_explanation | string | confidence の根拠。3文以上 |

### 8b. Runner-up

| フィールド | 型 | 説明 |
|-----------|---|------|
| candidate_id | string / null | 次点候補 |
| candidate_name | string / null | 次点候補名 |
| why_not_best | string | なぜ best ではないか。2文以上 |
| conditions_where_preferred | string | runner-up が best を逆転する条件 |

### 8c. Conditions & Unknowns

| フィールド | 型 | 説明 |
|-----------|---|------|
| critical_conditions | object[] | 推奨を無効化しうる条件 |
| open_unknowns | object[] | 未解決の不確実性 |
| recommendation_expiry | object | 推奨の有効期限 |

各 critical_condition:

| フィールド | 型 | 説明 |
|-----------|---|------|
| condition_id | string | 条件識別子 |
| statement | string | 「もし〜なら、この推奨は無効」の否定条件文 |
| verification_method | string | この条件をどうやって検証するか |
| verification_timing | string | いつ検証すべきか |

各 open_unknown:

| フィールド | 型 | 説明 |
|-----------|---|------|
| unknown_id | string | 不確実性識別子 |
| description | string | 何がわかっていないか |
| impact_if_resolved_positively | string | 好転した場合の推奨への影響 |
| impact_if_resolved_negatively | string | 悪転した場合の推奨への影響 |
| resolution_method | string | どうやって解消するか |

### 非専門ユーザー向け表示

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
推奨
━━━━━━━━━━━━━━━━━━━━━━━━━━

{recommendation_statement}

信頼度: {confidence_label_icon} {confidence_label_jp}
{confidence_explanation}

なぜこの方向か:
- {ranking_logic[0]}
- {ranking_logic[1]}
- {ranking_logic[2]}

⚠️ この推奨が成り立つ条件:
1. {critical_conditions[0].statement}
   → 確認方法: {critical_conditions[0].verification_method}
   → 確認時期: {critical_conditions[0].verification_timing}
2. ...

❓ まだわかっていないこと:
1. {open_unknowns[0].description}
   → 好転した場合: {open_unknowns[0].impact_if_resolved_positively}
   → 悪転した場合: {open_unknowns[0].impact_if_resolved_negatively}
2. ...

📅 この推奨の有効期限: {recommendation_expiry.description}

━━━━━━━━━━━━━━━━━━━━━━━━━━
次点
━━━━━━━━━━━━━━━━━━━━━━━━━━

{runner_up.candidate_name}
推奨にならなかった理由: {runner_up.why_not_best}
こちらが有利になる条件: {runner_up.conditions_where_preferred}
```

**critical_conditions と open_unknowns は推奨文の直後に表示。** 推奨だけ読んで条件を無視するリスクを構造的に低減する。

### Builder 向け表示
Recommendation Object の全フィールド。critical_conditions × open_unknowns のクロスリファレンス。各条件から Research Spec の assumption_space、Audit Object の surviving_assumptions へのトレーサビリティ。

---

## 9. Next Steps

### 目的
ユーザーが「次に何をすべきか」を具体的に示す。抽象的な「検証を進めましょう」ではなく、実行可能なタスクリスト。

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|---|------|
| immediate_actions | object[] | 今すぐ着手すべきアクション（優先度順、最大5件） |
| deferred_actions | object[] | 即座ではないが計画すべきアクション |
| decision_points | object[] | ユーザーが判断すべき分岐点 |

各 action:

| フィールド | 型 | 説明 |
|-----------|---|------|
| action_id | string | アクション識別子 |
| description | string | 何をするか |
| purpose | string | なぜ必要か |
| required_resources | string | 何が必要か（データ、ツール、時間） |
| expected_outcome | string | 何が得られるか |
| blocks_if_skipped | string[] | これを飛ばすと何が止まるか |
| priority | enum | critical / high / medium |

各 decision_point:

| フィールド | 型 | 説明 |
|-----------|---|------|
| decision_id | string | 分岐点識別子 |
| question | string | ユーザーが判断すべき問い |
| options | object[] | 選択肢。各項目に `label`, `implication` |
| deadline | string / null | 判断期限（あれば） |

### 非専門ユーザー向け表示

```
次にやるべきこと（優先度順）:

1. 🔴 {immediate_actions[0].description}
   なぜ: {immediate_actions[0].purpose}
   必要なもの: {immediate_actions[0].required_resources}
   これを飛ばすと: {immediate_actions[0].blocks_if_skipped}

2. 🟠 {immediate_actions[1].description}
   ...

あなたが決める必要があること:
❓ {decision_points[0].question}
   選択肢A: {options[0].label} → {options[0].implication}
   選択肢B: {options[1].label} → {options[1].implication}
```

### Builder 向け表示
全アクションと decision_points の依存関係グラフ。Validation Plan の test_sequence との対応マッピング。

---

## 10. Re-evaluation Triggers

### 目的
推奨がいつ・なぜ無効になりうるかを事前定義し、ユーザーが「放置していい期間」と「再検討すべきシグナル」を把握できるようにする。

### 必須フィールド

| フィールド | 型 | 説明 |
|-----------|---|------|
| triggers | object[] | 再評価を促すトリガー一覧 |
| default_recheck_interval | string | 定期再検討の間隔 |

各 trigger:

| フィールド | 型 | 説明 |
|-----------|---|------|
| trigger_id | string | トリガー識別子 |
| trigger_type | enum | time_based / data_based / market_event / assumption_invalidation / performance_degradation |
| description | string | 何が起きたら再検討か |
| detection_method | string | どうやって検出するか |
| urgency | enum | routine / elevated / immediate |
| recommended_action | enum | rerun_full_loop / rerun_from_step_N / update_evidence_only / manual_review |

### 非専門ユーザー向け表示

```
この推奨を見直すべきタイミング:

📅 定期チェック: {default_recheck_interval}ごと

⚡ 即座に見直すべきシグナル:
- {triggers で urgency = immediate のもの}

🔶 注意して観察すべきシグナル:
- {triggers で urgency = elevated のもの}

📋 定期確認で十分なシグナル:
- {triggers で urgency = routine のもの}
```

### Builder 向け表示
Re-evaluation Trigger Set の全フィールド。各 trigger から assumption_space / regime_dependencies へのトレーサビリティ。

---

## Warnings / Unknowns / Conditions: 必ず含めるべきもの

### 全パッケージ共通の必須 Warning

以下は、パッケージのどのセクションに位置していても、**必ず出力する**。

| Warning 種別 | 内容 | 表示位置 |
|-------------|------|----------|
| **計画段階の限界** | 「この推奨は計画段階の分析に基づいています。実データによるバックテスト・検証は完了していません」 | Executive Summary 直下 + Recommendation 冒頭 |
| **市場環境の前提** | regime_dependencies の要約。「この分析は以下の市場環境を前提としています: {list}」 | Research Framing + Recommendation |
| **データバイアスの注意** | bias_warnings の要約。1件以上あれば表示 | Evidence Assessment + Recommendation |
| **confidence の意味** | 「confidence: {label} は、現在の情報に基づく計画段階の評価です。実検証により変動します」 | Executive Summary |
| **proxy データの使用** | proxy_data_used が1件以上あれば「一部の証拠に代替データを使用しています」 | Evidence Assessment |

### 条件が省略された場合の安全装置

以下のいずれかが空の場合、パッケージは**不正とみなし生成を拒否する**:

| フィールド | 空の場合の扱い |
|-----------|--------------|
| critical_conditions | 生成拒否。条件なしの推奨は存在しない |
| open_unknowns | 生成拒否。計画段階で不確実性ゼロは非現実的 |
| rejection_reason（rejected 候補） | 生成拒否。理由なき棄却は Audit の機能不全 |
| failure_conditions（各テスト） | 生成拒否。失敗しないテストは検証ではない |
| recommendation_expiry | 生成拒否。有効期限なしの推奨は生成しない |

---

## v1 で含めないもの

| 除外対象 | 理由 | 導入予定 |
|---------|------|---------|
| 実装コード | コード生成はプロダクト価値の中心ではない。推奨パッケージ内にコードを含めると「コードが出力の本体」という誤解を生む | v1.5 でオプション付加を検討 |
| バックテスト実行結果 | v1 は計画段階。実行結果のフィードバックは別サイクル | v1.5 |
| パフォーマンス予測値 | 未検証の予測値は false confidence の温床。「Sharpe 1.5 が期待できます」のような出力は禁止 | 含めない（原則禁止） |
| ポートフォリオ構築の具体的指示 | 「何株買え」は推奨パッケージの責務外 | v2 で検討 |
| 取引シグナル | 推奨パッケージは方向性の推奨であり、実行指示ではない | v2 で検討 |
| 他ユーザーの推奨結果との比較 | プライバシー + 文脈依存のため比較は無意味 | 含めない |
| 規制適合性の判断 | 法的助言は提供しない | 含めない |
| コスト見積もり（実装コスト） | 見積もりの精度が担保できない段階 | v1.5 |
| 自動再実行のスケジュール設定 | v1 は trigger の定義のみ。実行はユーザー | v1.5 |
| リアルタイムデータのダッシュボード表示 | v1 はデータソース接続を持たない | v2 |
| 自然言語での対話的な Q&A（パッケージ生成後） | パッケージは静的成果物。対話は別機能 | v1.5 |

---

## Output Package のバリデーションルール

パッケージ生成後、以下を自動検証する。違反がある場合は生成を拒否し、内部エラーとして処理。

### 構造バリデーション

| ルール | 検証内容 |
|--------|---------|
| 全10セクション存在 | いずれのセクションも省略不可 |
| best_candidate_id が Audit で passed / passed_with_warnings | rejected 候補は推奨不可 |
| runner_up が best と異なる | best = runner_up は不可 |
| rejected 候補に rejection_reason あり | 理由なき棄却は不可 |
| critical_conditions 1件以上 | 条件なし推奨は不可 |
| open_unknowns 1件以上 | 不確実性ゼロは不可 |
| recommendation_expiry 存在 | 有効期限なし推奨は不可 |
| 全テストに failure_conditions 1件以上 | 失敗条件なしテストは不可 |
| comparison_matrix に baseline 含む | baseline なし比較は不可 |
| confidence_label が機械的算出と一致 | 手動上書き検出 |

### 内容バリデーション

| ルール | 検証内容 |
|--------|---------|
| recommendation_statement に条件節を含む | 無条件推奨文の検出 |
| ranking_logic が3軸以上 | 比較根拠の不足検出 |
| rejection_reason が3文以上 | 棄却理由の粗さ検出 |
| confidence_explanation が3文以上 | confidence 根拠の粗さ検出 |
| immediate_actions が1件以上 | 次ステップなしは不可 |
| next_validation_steps の各項目に4要素（誰が・何のデータで・どのテストを・どの閾値で） | 粒度不足の検出 |
| testable_claims の各項目に falsification_condition | 棄却不能な主張の検出 |

---

## 表示モードの切り替え

Output Package は単一のデータ構造から2つの表示モードを生成する。

| モード | 対象 | 表示方針 |
|--------|------|---------|
| **Summary View** | 非専門ユーザー | 自然言語中心。専門用語を排除。信号機・カード・ステップ形式。条件と不確実性は省略せず平易に言い換え |
| **Detail View** | Builder / 実装者 | JSON + トレーサビリティ。全フィールド展開。モジュール間の依存関係可視化。フィルタリング・検索可能 |

モード切り替えはユーザーのトグル操作。デフォルトは Summary View。

**原則: Summary View で情報を削らない。表現を変えるだけ。** Detail View にしかない情報は存在してはならない（表示形式が変わるだけで、情報量は同一）。

ただし例外として以下は Detail View のみ:
- 内部 Object ID（run_id, candidate_id 等の技術的識別子）
- モジュール間トレーサビリティマップ
- JSON 生データ
