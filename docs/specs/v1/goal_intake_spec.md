# Give Me a DAY v1 — Goal Intake Design Specification

**Document type**: UX + internal logic specification
**Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
**Version**: v1 draft
**Status**: Design phase — pre-implementation
**Upstream dependencies**: internal_schema_v1_consolidated.md (UserIntent Object)
**Downstream consumers**: Domain Framing (Step 2), and transitively all subsequent steps

---

## 1. Goal Intake の目的

Goal Intake は「ユーザーの頭の中にある意図を、検証パイプラインが処理可能な構造に変換する入口」である。

ただし、この「変換」は一般的なアプリの onboarding とは根本的に異なる。一般的な onboarding は「ユーザーが何を望んでいるか」を聞く。Give Me a DAY の Goal Intake は「ユーザーが何を検証すべきか」を聞く——あるいは、ユーザーが自分で気づいていない場合は、検証すべき形に変換する準備を整える。

Goal Intake の3つの責務:

1. **意図の構造化**: 自然言語のゴールを UserIntent Object のフィールドに分解する
2. **推奨品質に直結する不確実性の低減**: downstream の Recommendation の条件文 (critical_conditions) や未知数 (open_unknowns) に直接影響する情報を、この段階で可能な限り確定する
3. **スコープ外の早期検出**: 投資リサーチドメイン外のゴールを、下流に流す前にここで止める

Goal Intake は「ユーザーの話を聞く場」ではなく「推奨の品質を左右する情報を最小手数で取得する場」である。

---

## 2. 質問セット（最大7問）

### 設計原則

- 最大7問。これ以上は離脱率が上がる
- 質問の順序に意味がある。広い→狭い、自由→制約の順
- 全質問が UserIntent Object の少なくとも1フィールドに直結する
- 「あったら便利」な質問は入れない。「なければ downstream が壊れる」質問だけ
- ユーザーが全問にスキップなしで答えた場合に、UserIntent Object が最低限成立する設計

---

### Q1: ゴール（自由記述）

**表示テキスト**:
```
どんな投資の仕組みを検討していますか？
やりたいこと、試してみたいアイデア、解決したい課題を自由に書いてください。
```

**補足テキスト（小さく表示）**:
```
例：
・「日本株でモメンタム戦略を試したい」
・「決算発表前後の株価の動きで利益を出せるか調べたい」
・「マクロ指標と株式リターンの関係を検証したい」
・「既存のバリュー戦略を改善できないか検討したい」
```

#### 意図
ユーザーの「生の意図」を取得する。この回答は `raw_goal` にそのまま格納され、以後の全処理の原点になる。自由記述にすることで、ユーザーの頭の中にある言葉をそのまま取れる。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `raw_goal` | 回答をそのまま格納 |
| `user_goal_summary` | システムが raw_goal を要約して生成 |
| `domain` | 回答内容が投資リサーチドメインに該当するか判定。非該当 → スコープ外応答 |

#### 形式: 自由記述
選択式にしない理由: ユーザーのゴールは予測不能な多様性を持つ。選択肢で制約すると、ユーザーの本当の意図を取りこぼす。

---

### Q2: 成功の定義（半構造化）

**表示テキスト**:
```
この検討がうまくいったとしたら、どんな結果が出ていれば「成功」と言えますか？
```

**入力ガイド（プレースホルダー付き3欄）**:

```
何を達成したいか:     [                                        ]
  例: 市場平均を上回るリターン / リスクを抑えた安定収益 / 特定の仮説の正否の判明

どの程度:             [                                        ]
  例: 年率5%以上 / 最大損失10%以内 / 統計的に有意な結果

どのくらいの期間で:    [                                        ]
  例: 3年以上のバックテスト / 半年の検証期間 / まず1ヶ月の予備調査
```

#### 意図
`success_definition` を構造的に取得する。「儲かる」のような曖昧な定義を、「何を・どの程度・どの期間で」の3次元に分解する。この3次元が定まらないと、Validation Plan の pass/fail 閾値が設定できず、Recommendation の条件文が書けない。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `success_definition` | 3欄の回答を結合して生成 |
| → ResearchSpec.`disqualifying_failures` | 「どの程度」欄がメトリクス閾値の原材料になる |
| → ValidationPlan.`metrics[].pass_threshold` | 同上 |
| → Recommendation.`critical_conditions` | 成功定義が未達の場合 → 推奨無効条件に |

#### 形式: 半構造化（3欄の自由記述）
完全な自由記述にしない理由: 「うまくいったら嬉しい」のような非定量回答を防ぐ。3欄に分けることで、定量性を暗黙に要求する。
完全な選択式にしない理由: 成功の定義は候補ごとに異なりすぎる。選択肢では網羅不能。

---

### Q3: リスク許容度（選択式）

**表示テキスト**:
```
一時的な損失をどの程度まで許容できますか？
```

**選択肢**:

| 選択肢 | ラベル | 内部値 | 補足テキスト |
|--------|-------|--------|------------|
| A | ほぼ損失を出したくない | `very_low` | 安全性最優先。リターンが低くても構わない |
| B | 小さい損失なら許容できる | `low` | 10%程度の一時的な値下がりは受け入れられる |
| C | ある程度の損失は覚悟している | `medium` | 20-30%の値下がりも戦略の範囲内と考える |
| D | 大きな損失もリターンのためなら受け入れる | `high` | 50%以上の損失も可能性として許容する |

#### 意図
`risk_preference` を取得する。この値は ResearchSpec の `minimum_evidence_standard` を機械的に決定し、Audit の棄却閾値に影響する。ユーザーの主観的リスク許容度と、システムが要求する検証基準をここで接続する。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `risk_preference` | 選択値をそのまま格納 |
| → ResearchSpec.`minimum_evidence_standard` | very_low → strong, low+quality_over_speed → strong, medium → moderate, high+fast → weak |
| → Audit severity 調整 | risk_preference = very_low/low の場合、RGM-02 (レジーム転換未考慮) が disqualifying になる |
| → Recommendation.`confidence_label` | low risk_preference は evidence coverage の要求を引き上げる |

#### 形式: 選択式（単一選択）
自由記述にしない理由: リスク許容度を自由記述で聞くと「普通くらい」のような回答が来る。離散的な4段階に強制することで、下流の機械的判定に接続できる。

---

### Q4: 時間軸（選択式）

**表示テキスト**:
```
この検討にどのくらいの時間をかけたいですか？
```

**選択肢**:

| 選択肢 | ラベル | 内部値 | 補足テキスト |
|--------|-------|--------|------------|
| A | まず概要を素早く知りたい | `fast` | 大まかな方向性を把握する。深い検証はこの後 |
| B | 1日で結論が欲しい | `one_day` | 今日中に判断材料を揃えたい |
| C | 1週間かけてしっかり検討したい | `one_week` | 複数の選択肢を比較して判断したい |
| D | 1ヶ月かけて徹底的に検証したい | `one_month` | 実データでの検証まで含めて進めたい |
| E | 時間より検証の質を優先する | `quality_over_speed` | 必要な時間をかけてでも正確な結果を出したい |

#### 意図
`time_horizon_preference` を取得する。この値は Recommendation の有効期限 (`recommendation_expiry`) と Re-evaluation Trigger の `default_recheck_interval` を決定する。また、`minimum_evidence_standard` の算出にも影響する。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `time_horizon_preference` | 選択値をそのまま格納 |
| → Recommendation.`recommendation_expiry` | fast→weekly, one_week→biweekly, one_month→monthly, quality_over_speed→quarterly |
| → ReEvaluationTriggerSet.`default_recheck_interval` | 同上 |
| → ResearchSpec.`minimum_evidence_standard` | risk_preference との組合せで決定 |
| → ValidationPlan 全体の規模感 | fast → テスト数を最小限に。quality_over_speed → 全テスト型を使用 |

#### 形式: 選択式（単一選択）
自由記述にしない理由: 同上。下流で機械的に使用する値を、曖昧さなく取得するため。

---

### Q5: 利用可能なデータ（複数選択 + 自由記述）

**表示テキスト**:
```
現在、以下のうち利用できるデータや環境はありますか？（複数選択可）
```

**選択肢**:

| 選択肢 | ラベル | 内部タグ |
|--------|-------|---------|
| A | 株価・出来高データ（日次以上） | `price_daily` |
| B | 株価データ（分足・ティック） | `price_intraday` |
| C | 企業の決算・財務データ | `fundamental` |
| D | マクロ経済指標（GDP、金利、為替等） | `macro` |
| E | オルタナティブデータ（SNS、衛星、カード決済等） | `alternative` |
| F | ニュース・アナリスト予想 | `sentiment` |
| G | 資金フロー・ポジションデータ | `flow` |
| H | プログラミング環境（Python等） | `tooling_code` |
| I | バックテストツール（Zipline、Backtrader等） | `tooling_backtest` |
| J | 特にない / わからない | `none` |

**追加自由記述欄**:
```
上記以外に使えるデータやツールがあれば教えてください（任意）:
[                                                            ]
```

#### 意図
`available_inputs` を取得する。この情報は Evidence Planning (Step 5) の `availability` 判定に直結する。ユーザーが何を持っているかによって、候補の実行可能性が変わる。「特にない」の回答も重要な情報——evidence_gap が多くなることを意味する。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `available_inputs` | 選択タグ + 自由記述を配列として格納 |
| → EvidencePlan.`evidence_items[].availability` | available_inputs に含まれるカテゴリ → available。含まれない → obtainable_with_effort or unavailable |
| → EvidencePlan.`coverage_metrics` | available_inputs の充実度が coverage_percentage の初期見積もりに影響 |
| → Candidate の実行可能性判断 | tooling が none の場合、高度な ML 候補は validation_burden: high になる |

#### 形式: 複数選択 + 自由記述
複数選択にする理由: データの種類は有限のカテゴリに分類可能。Evidence Taxonomy の7カテゴリに対応。
自由記述も付ける理由: 選択肢にない特殊なデータ（独自収集データ等）を拾うため。

---

### Q6: やってはいけないこと（複数選択 + 自由記述）

**表示テキスト**:
```
検討から除外したいものはありますか？（複数選択可。なければスキップ可）
```

**選択肢**:

| 選択肢 | ラベル | 内部タグ |
|--------|-------|---------|
| A | 空売り（ショートセリング） | `no_short_selling` |
| B | レバレッジ（借入による投資の拡大） | `no_leverage` |
| C | デリバティブ（先物・オプション） | `no_derivatives` |
| D | 日中取引（デイトレード） | `no_intraday_trading` |
| E | 特定の資産クラス（例：暗号資産、コモディティ等） | `no_specific_asset` |
| F | 完全自動での売買実行 | `no_auto_execution` |
| G | 特にない | `none` |

**追加自由記述欄**:
```
上記以外に除外したいものがあれば教えてください（任意）:
[                                                            ]
```

#### 意図
`must_not_do` を能動的に取得する。投資ドメインでは「禁止事項」がゴールの記述と同等に重要。ユーザーが自発的に言わない禁止事項が多い（例: 空売り制限は言及されないことが多いが、戦略の方向性を大きく左右する）。

選択肢を提示することで「ああ、空売りは考えてなかったけど、確かに使いたくないな」というケースを拾う。これがないと、Step 4 で空売り前提の候補が生成され、Step 7 でユーザーが「それは嫌だ」と言い、手戻りが発生する。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `must_not_do` | 選択タグ + 自由記述を配列として格納 |
| → ResearchSpec.`constraints.forbidden_behaviors` | must_not_do をそのまま継承 |
| → Candidate Generation の制約条件 | must_not_do に含まれる手法を使用する候補は生成しない |
| → Audit | 候補が must_not_do に違反していないかのチェック |

#### 形式: 複数選択 + 自由記述（スキップ可能）
スキップ可能にする理由: 禁止事項がないユーザーもいる。強制すると離脱する。
選択肢を出す理由: 一般的なアプリの「制約はありますか？」という open-ended な質問では、投資ドメイン固有の重要禁止事項が拾えない。

---

### Q7: 自動化の希望度（選択式）

**表示テキスト**:
```
どこまでの支援を期待しますか？
```

**選択肢**:

| 選択肢 | ラベル | 内部値 | 補足テキスト |
|--------|-------|--------|------------|
| A | 分析と助言だけほしい | `advice_only` | 自分で判断して実行する。検証の方向性と材料がほしい |
| B | 調査・分析を手伝ってほしい | `research_assist` | データ収集や分析の一部を手伝ってほしい |
| C | 半自動で実行してほしい | `semi_automated` | 判断は自分がするが、実行はシステムに任せたい |
| D | 安全なら完全自動にしたい | `full_if_safe` | リスク管理が十分なら自動で運用してほしい |

#### 意図
`automation_preference` を取得する。この値は Audit の observability カテゴリの severity を調整する。`full_if_safe` で OBS-04（停止条件未定義）が disqualifying になる。`advice_only` なら observability は low severity。

#### Downstream 接続

| UserIntent Field | マッピング |
|-----------------|----------|
| `automation_preference` | 選択値をそのまま格納 |
| → Audit OBS カテゴリの severity 調整 | full_if_safe → OBS-04 is disqualifying. advice_only → OBS is low |
| → Candidate Generation | full_if_safe → 監視・停止機構を architecture_outline に含む候補を生成 |
| → Output Package の表示調整 | advice_only → Validation Plan をユーザー実行型で表示。full_if_safe → 実装要件を詳細表示 |

#### 形式: 選択式（単一選択）
自由記述にしない理由: 自動化の度合いは4段階で十分に分類できる。下流で機械的に使用する。

---

## 3. 質問意図の集約マップ

```
Q1 (ゴール)           → raw_goal, user_goal_summary, domain判定
Q2 (成功の定義)        → success_definition → disqualifying_failures, pass_threshold, critical_conditions
Q3 (リスク許容度)      → risk_preference → minimum_evidence_standard, Audit severity
Q4 (時間軸)           → time_horizon_preference → recommendation_expiry, recheck_interval
Q5 (利用可能データ)    → available_inputs → evidence availability, coverage_metrics
Q6 (禁止事項)         → must_not_do → constraints, candidate generation bounds
Q7 (自動化希望度)      → automation_preference → Audit OBS severity
```

7問で UserIntent Object の全フィールドが埋まる。`open_uncertainties` は Q1–Q7 の回答から「確定できなかった事項」として自動生成される。

---

## 4. Downstream 接続の全体図

```
                    Q1   Q2   Q3   Q4   Q5   Q6   Q7
                    ──   ──   ──   ──   ──   ──   ──
UserIntent          ✓    ✓    ✓    ✓    ✓    ✓    ✓    ← 全問が直結
  ↓
DomainFrame              ✓              ✓              ← 成功定義が testable_claims に、
                                                         データ状況が framing に影響
  ↓
ResearchSpec        ✓    ✓    ✓    ✓    ✓    ✓    ✓    ← 全フィールドがSpec構築に貢献
  ↓
Candidate                          ✓    ✓    ✓         ← 時間軸/データ/禁止事項が候補の幅を決める
  ↓
EvidencePlan                            ✓              ← 利用可能データが availability を決定
  ↓
ValidationPlan           ✓    ✓    ✓                   ← 成功定義/リスク/時間が検証計画の規模を決める
  ↓
Audit                    ✓    ✓              ✓    ✓    ← 成功定義/リスクが棄却閾値、禁止事項/自動化がseverity
  ↓
Recommendation      ✓    ✓    ✓    ✓    ✓    ✓    ✓    ← 全問の情報が推奨の条件文に影響
```

---

## 5. 自由記述 vs 選択式の判定基準と一覧

| 質問 | 形式 | 判定理由 |
|------|------|---------|
| Q1 ゴール | 自由記述 | ユーザーの意図は事前に予測不能。選択肢で制約すると本当の意図を取りこぼす |
| Q2 成功の定義 | 半構造化（3欄） | 完全自由だと曖昧になり、完全選択式では網羅不能。3次元（何を/どの程度/いつまで）に分解 |
| Q3 リスク許容度 | 選択式（4択） | 下流で機械的に使用。離散4段階で十分 |
| Q4 時間軸 | 選択式（5択） | 下流で機械的に使用。離散5段階で十分 |
| Q5 利用可能データ | 複数選択 + 自由記述 | カテゴリは有限（Evidence Taxonomy 7分類 + ツール2分類）。特殊データは自由記述で補完 |
| Q6 禁止事項 | 複数選択 + 自由記述 | ドメイン固有の典型禁止事項は有限。提示しないと拾えない。特殊な制約は自由記述で補完 |
| Q7 自動化希望度 | 選択式（4択） | 下流で機械的に使用。離散4段階で十分 |

**原則**: 下流で enum / 機械的判定に使うフィールド → 選択式。下流で自然言語処理が必要なフィールド → 自由記述。

---

## 6. 曖昧回答に対する Follow-up ルール

### Follow-up の設計原則

- Follow-up は **最大3往復** まで。3往復を超えたら「現時点の理解で進む」と宣言し、不明点は `open_uncertainties` に格納
- Follow-up は「なぜそれを聞くのか」の理由を必ず添える。理由なき再質問は不信感を生む
- Follow-up は追加質問ではなく、「あなたの回答をこう理解しましたが合っていますか？」の確認形式を優先

### 質問別 Follow-up ルール

#### Q1: ゴール — 曖昧回答パターンと対応

| 曖昧パターン | 例 | Follow-up | 理由の説明 |
|-------------|---|-----------|----------|
| 漠然すぎる | 「投資で稼ぎたい」 | 「具体的には、どの市場・資産で、どのようなアプローチを考えていますか？たとえば、日本株、米国株、FX などの市場や、割安株を見つける、トレンドに乗る、といったアプローチです」 | 候補生成の方向性を絞るために必要 |
| ドメイン外 | 「社内の業務効率化をしたい」 | 「申し訳ありませんが、Give Me a DAY は投資リサーチ・戦略検証に特化したサービスです。投資に関するゴールでしたら改めてお聞かせください」 | v1 スコープ外。即座に redirect |
| 複数ゴール混在 | 「モメンタムもバリューも試したい」 | 「それぞれ検証の方向が異なりますので、まずどちらか1つに絞って進め、もう1つは別の検討として扱うことを推奨します。どちらを先に検討しますか？」 | 1 run = 1 primary_objective |
| 既製品の丸投げ | 「儲かるシステムを作って」 | 「Give Me a DAY は自動で利益を保証するサービスではなく、投資アイデアの検証を支援するサービスです。検討したいアイデアや仮説があれば教えてください」 | プロダクトの非約束事項の明確化 |

#### Q2: 成功の定義 — 曖昧回答パターンと対応

| 曖昧パターン | 例 | Follow-up |
|-------------|---|-----------|
| 「何を」が曖昧 | 「うまくいくこと」 | 「"うまくいく" を具体的に測るとしたら、何が上がればいいですか？（リターン、勝率、リスク調整後リターン、など）」 |
| 「どの程度」が曖昧 | 「まあまあの成績」 | 「"まあまあ" はどのくらいの数字をイメージしていますか？たとえば年率3%、10%、それとも市場平均と同程度？」 |
| 「いつまで」が欠落 | 「年率10%以上」 | 「この年率10%は、何年くらいの期間で安定して出せていれば成功と考えますか？」 |
| 全欄空白 | （スキップ） | 「成功の基準が定まらないと、検証で"何をもって良い結果とするか"が決められません。大まかでも構いませんので、何か1つだけ教えていただけますか？」 |

**Q2 の Follow-up は最重要。** success_definition が埋まらないと disqualifying_failures が設定できず、Validation Plan の全テストが pass/fail 閾値なしになり、Audit が機能不全になる。

Q2 で 2往復しても具体化しない場合の最終手段:
```
「現時点では成功基準を仮置きして進めます。仮に『リスク調整後リターンが市場平均を上回ること。
ただし最大損失は [Q3の回答に基づく] 以内』とします。この後の検証結果を見てから、
基準を修正することもできます。」
```
→ 仮置き基準を `success_definition` に入れ、「仮置きである」旨を `open_uncertainties` に追加。

#### Q3–Q4, Q7: 選択式質問

Follow-up 不要。選択肢を選べば値が確定する。未選択（スキップ）の場合:
- Q3 (リスク許容度): デフォルト `medium`。`open_uncertainties` に「リスク許容度は仮置き (medium)」を追加
- Q4 (時間軸): デフォルト `one_week`。`open_uncertainties` に「時間軸は仮置き (one_week)」を追加
- Q7 (自動化): デフォルト `advice_only`。`open_uncertainties` に追加

**デフォルト値は保守側に設定する。** medium / one_week / advice_only は、それぞれの軸で中立〜保守的。

#### Q5: 利用可能データ

| 曖昧パターン | 例 | Follow-up |
|-------------|---|-----------|
| 全選択肢「わからない」 | J を選択 | Follow-up なし。`available_inputs: ["none"]` として処理。Evidence Plan で全データが obtainable_with_effort or unavailable になる。これは正常な入力 |
| 曖昧な自由記述 | 「ちょっとしたデータはある」 | 「そのデータは、株価のような数値データですか？ニュースのようなテキストデータですか？どのくらいの期間分ありますか？」 |

#### Q6: 禁止事項

Follow-up 不要。スキップ可能。スキップ時は `must_not_do: []`（禁止事項なし）。

---

## 7. Recommendation-critical Uncertainty の低減戦略

### 定義
「Recommendation-critical uncertainty」とは、**解消されないままだと Recommendation の confidence_label を下げるか、critical_conditions の数を増やす不確実性**のこと。

### 7問で低減すべき4大 uncertainty

| # | Uncertainty | 低減する質問 | 低減できない場合の影響 |
|---|------------|------------|-------------------|
| 1 | 「何を検証すべきか」がわからない | Q1 + Q2 | DomainFrame.testable_claims が空虚になる。ResearchSpec.primary_objective が定まらない。全下流が方向を失う |
| 2 | 「何をもって成功/失敗とするか」がわからない | Q2 | disqualifying_failures が設定不能。Validation Plan の pass/fail が不定。Audit が棄却判定できない。confidence_label は強制 low |
| 3 | 「検証に使えるデータがあるか」がわからない | Q5 | EvidencePlan.coverage_percentage が不明。Evidence gap の深刻度が判断不能。confidence_label は強制 low |
| 4 | 「やってはいけないことがあるか」がわからない | Q6 | 禁止事項に違反する候補が生成される → ユーザー拒否 → 手戻り。Audit では検出不能（ドメイン知識ではなくユーザー固有の制約のため） |

### 低減の優先順位

| 優先度 | Uncertainty | 理由 |
|--------|------------|------|
| 1 (最優先) | #2 成功/失敗基準 | これが不定だと Validation Plan 全体が成立しない。他のどの uncertainty よりも下流への影響が大きい |
| 2 | #1 検証対象 | ゴール自体が曖昧だと候補生成が的外れになる |
| 3 | #4 禁止事項 | 手戻りのコストが大きい。早期に確定すべき |
| 4 | #3 利用可能データ | 重要だが、Step 5 (Evidence Planning) で詳細化される。Goal Intake では概要把握で十分 |

### Follow-up の投資配分

3往復の Follow-up 予算のうち:
- Q2 (成功定義) への Follow-up に最大2往復を投入
- Q1 (ゴール) への Follow-up に最大1往復を投入
- Q3–Q7 への Follow-up には予算を使わない（選択式のため不要、またはデフォルト値で処理可能）

---

## 8. v1 で聞くべきでない質問

| 聞くべきでない質問 | なぜ聞かない | 代替処理 |
|------------------|-------------|---------|
| 「投資経験はどのくらいですか？」 | ユーザーの能力評価はプロダクトの責務外。回答がバイアスを生む（「上級者」と答えたユーザーに高度な候補を偏重する等）。Audit はユーザーの能力に関係なく一律の基準で候補を批判すべき | 不要。Audit 基準はユーザー属性に依存しない |
| 「予算はいくらですか？」 | v1 では実行コスト見積もりを出さない。予算情報は候補の実行可能性判断に使えるが、正確なコスト推定が不可能な計画段階では misleading | v1.5 で検討 |
| 「どのプログラミング言語を使いますか？」 | コード生成はプロダクトの中心価値ではない。言語選択は候補の検証品質に影響しない | 不要 |
| 「過去のポートフォリオを教えてください」 | プライバシーの問題。かつ、過去の実績は将来の戦略検証とは無関係 | 不要 |
| 「どの証券会社を使っていますか？」 | v1 では執行インフラを扱わない | v2 で検討 |
| 「リアルタイムの市場データにアクセスできますか？」 | Q5 で price_intraday を聞いている。さらに粒度を上げる質問は Goal Intake では不要。Evidence Planning で詳細化 | Step 5 で詳細化 |
| 「具体的にどの銘柄に興味がありますか？」 | 特定銘柄への関心は戦略の検証設計には不要。特定銘柄バイアスを持ち込むリスクがある | 不要。戦略レベルで検討 |
| 「AI/機械学習を使いたいですか？」 | 手法の選択は候補生成 (Step 4) の責務。Goal Intake でユーザーに手法を選ばせると、探索空間を不必要に狭める | Step 4 で候補として自然に含める |

---

## 9. Goal Intake の完成条件

### 最低完成条件（Minimum Viable Intake）

以下の条件を全て満たした場合、Goal Intake は完了とし、Step 2 (Domain Framing) に進む。

| # | 条件 | 根拠 |
|---|------|------|
| 1 | `raw_goal` が非空であること | ゴールなしでは何も処理できない |
| 2 | `domain` が `"investment_research"` と判定されたこと | v1 スコープ内確認 |
| 3 | `success_definition` が「何を」「どの程度」の最低2次元を含むこと | 「いつまで」が欠落しても open_uncertainties に入れて続行可能。「何を」「どの程度」がないと disqualifying_failures が設定不能 |
| 4 | `risk_preference` が確定していること | デフォルト (medium) でも可だが、デフォルト使用は open_uncertainties に記録 |
| 5 | `time_horizon_preference` が確定していること | 同上 (one_week) |
| 6 | `automation_preference` が確定していること | 同上 (advice_only) |
| 7 | Follow-up が3往復以内で完了していること | 3往復超は離脱リスク。超えたら現状で確定 |

### 品質段階（Quality Tiers）

| Tier | 条件 | 下流への影響 |
|------|------|------------|
| **Gold** | 全7問に実質的回答。Q2 の3欄全て非空。Q5 で1つ以上のデータカテゴリ選択。open_uncertainties = 0–1 件 | 全下流モジュールがフル品質で稼働 |
| **Silver** | Q1, Q2 に実質的回答。Q3–Q7 は一部デフォルト値。open_uncertainties = 2–3 件 | DomainFrame と ResearchSpec は成立するが、Recommendation の confidence_label が下がる。critical_conditions が増える |
| **Bronze** | Q1 に実質的回答。Q2 は仮置き。Q3–Q7 は大半デフォルト。open_uncertainties ≥ 4 件 | 処理は可能だが confidence_label は強制 low。Recommendation に「入力情報の不足により、推奨の信頼性は低い」の warning が付加 |

**Bronze 未満**（Q1 すらドメイン外 or 空）: Goal Intake 不成立。Step 2 に進まない。

### 完成時の出力

Goal Intake 完了時に以下を生成:

1. **UserIntent Object** — 全フィールドが埋まった JSON
2. **Intake Quality Report** — 品質 Tier (Gold/Silver/Bronze) + open_uncertainties の一覧
3. **ユーザー向け確認画面** — 「あなたのゴールをこう理解しました」の要約表示（Step 2 の DomainFrame 生成前のチェックポイント）

確認画面の表示テンプレート:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
あなたのゴールの確認
━━━━━━━━━━━━━━━━━━━━━━━━━━

ゴール:
{user_goal_summary}

成功の基準:
{success_definition}

リスク許容度: {risk_preference_label}
検討の時間軸: {time_horizon_preference_label}
自動化の希望: {automation_preference_label}

利用可能なデータ・ツール:
{available_inputs を自然言語で列挙}

除外する手法:
{must_not_do を自然言語で列挙。空なら「特になし」}

まだ確定していないこと:
{open_uncertainties を自然言語で列挙。空なら「特になし」}

━━━━━━━━━━━━━━━━━━━━━━━━━━
この理解で正しいですか？  [はい、進める]  [修正する]
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

「修正する」を押した場合:
- 修正対象の質問のみ再表示。全質問のやり直しは行わない
- 修正は1回まで（計2回の確認で離脱リスクが上がるため）。2回目の修正希望には「この後の分析で認識のずれが見つかった場合は調整できます。まずこの理解で進めませんか？」と提案

---

## Appendix A: ドメイン外検出ロジック

Q1 の回答がドメイン外かどうかの判定基準。

### ドメイン内と判定するキーワード / 概念

投資、株、債券、FX、為替、コモディティ、商品先物、仮想通貨、暗号資産、ポートフォリオ、ファクター、モメンタム、バリュー、アルファ、ベータ、リターン、リスク、ヘッジ、裁定、アービトラージ、バックテスト、シグナル、指標、テクニカル、ファンダメンタル、クオンツ、機械学習（投資文脈）、予測モデル（市場予測文脈）、配当、IPO、決算、マクロ、金利、インフレ

### ドメイン外と判定するパターン

- 業務効率化、タスク管理、CRM、マーケティング
- Web開発、アプリ開発（投資関連でない場合）
- 教育、医療、法律、不動産（不動産投資を除く）
- 「AIで何かしたい」のような非特定ゴール

### 境界ケースの扱い

| ケース | 判定 | 理由 |
|--------|------|------|
| 「不動産投資の分析をしたい」 | ドメイン内（条件付き） | 不動産は投資の一形態。ただし REIT 等の金融商品に限定し、実物不動産の仲介等はドメイン外 |
| 「暗号資産のトレーディング戦略」 | ドメイン内 | 金融商品の一種として扱える |
| 「経済予測モデルを作りたい」 | ドメイン内（条件付き） | 投資判断に使う目的なら内。学術研究目的なら open_uncertainties に「投資判断への接続が不明確」を追加して進行 |
| 「機械学習の勉強がしたい」 | ドメイン外 | 投資目的ではない |

---

## Appendix B: 質問の表示順序と条件分岐

```
[画面1] Q1: ゴール（自由記述）
  ↓
  ドメイン判定
  ├─ ドメイン外 → スコープ外メッセージ → 終了
  └─ ドメイン内 → 続行
  ↓
[画面2] Q2: 成功の定義（3欄）
  ↓
[画面3] Q3 + Q4: リスク許容度 + 時間軸（同一画面に並べる）
  ↓
[画面4] Q5: 利用可能データ（複数選択 + 自由記述）
  ↓
[画面5] Q6 + Q7: 禁止事項 + 自動化希望度（同一画面に並べる）
  ↓
[確認画面] ゴール確認
  ├─ 「はい、進める」→ UserIntent 確定 → Step 2 へ
  └─ 「修正する」→ 該当質問のみ再表示 → 確認画面に戻る
```

**5画面 + 1確認画面 = 計6画面**。7問を5画面に圧縮（Q3+Q4、Q6+Q7を同居）することで、体感的な質問数を減らす。

### 画面設計の原則
- 1画面あたりの回答時間は30秒以内を目標
- プログレスバー表示（画面1: 20%, 画面2: 40%, 画面3: 60%, 画面4: 80%, 画面5: 100%）
- 全画面に「前に戻る」ボタン
- Q6 はスキップ可能であることを明示
- 例文は薄いグレーで表示し、入力の邪魔にならないようにする

---

## Appendix C: UserIntent Object 生成ロジック

Q1–Q7 の回答から UserIntent Object を生成するロジック。

```
FUNCTION generate_user_intent(q1_answer, q2_answer, q3_answer, q4_answer, q5_answer, q6_answer, q7_answer):

  // Domain check
  IF NOT is_investment_domain(q1_answer):
    RETURN out_of_scope_response

  // Build UserIntent
  intent = {
    run_id: generate_uuid(),
    created_at: now(),
    raw_goal: q1_answer.text,
    domain: "investment_research",
    user_goal_summary: summarize(q1_answer.text),    // LLM summarization
    success_definition: combine_q2_fields(q2_answer), // "何を" + "どの程度" + "いつまで"

    risk_preference: q3_answer.value OR "medium",     // default if skipped
    time_horizon_preference: q4_answer.value OR "one_week",
    automation_preference: q7_answer.value OR "advice_only",

    must_not_do: q6_answer.selected_tags + q6_answer.free_text_items,
    available_inputs: q5_answer.selected_tags + q5_answer.free_text_items,

    open_uncertainties: []
  }

  // Populate open_uncertainties
  IF q2_answer.period_field IS EMPTY:
    intent.open_uncertainties.push("成功基準の期間が未定義（仮置きの可能性あり）")

  IF q3_answer.value IS DEFAULT:
    intent.open_uncertainties.push("リスク許容度は仮置き (medium)")

  IF q4_answer.value IS DEFAULT:
    intent.open_uncertainties.push("時間軸は仮置き (one_week)")

  IF q7_answer.value IS DEFAULT:
    intent.open_uncertainties.push("自動化希望度は仮置き (advice_only)")

  IF q5_answer.selected_tags == ["none"]:
    intent.open_uncertainties.push("利用可能なデータなし。全データの入手可能性を評価する必要あり")

  IF q2_answer IS 仮置き:
    intent.open_uncertainties.push("成功基準は仮置き。検証結果を見て再定義が必要")

  // Quality tier
  tier = determine_quality_tier(intent)

  RETURN { intent, tier }
```

### 品質 Tier 判定ロジック

```
FUNCTION determine_quality_tier(intent):

  IF intent.open_uncertainties.length <= 1
     AND intent.success_definition contains all 3 dimensions
     AND intent.available_inputs != ["none"]:
    RETURN "gold"

  IF intent.success_definition contains at least 2 dimensions
     AND intent.open_uncertainties.length <= 3:
    RETURN "silver"

  IF intent.raw_goal IS non-empty AND is_investment_domain(intent.raw_goal):
    RETURN "bronze"

  RETURN "insufficient"  // Does not proceed to Step 2
```
