# Give Me a DAY v1 — Internal Core Loop Specification

**Document type**: Internal system specification
**Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
**Version**: v1 draft
**Status**: Design phase — pre-implementation

---

## Loop Architecture Overview

このループはユーザー向け画面ではない。内部処理パイプラインである。
9ステップは直列に見えるが、Step 7 (Audit) が Step 4–6 にフィードバックループを持つ。

```
[1] Goal Intake
      ↓
[2] Domain Framing
      ↓
[3] Research Spec Compilation
      ↓
[4] Candidate Generation ←──────────┐
      ↓                              │
[5] Evidence Planning                │
      ↓                              │ (revision if all
[6] Validation Plan Generation       │  candidates rejected)
      ↓                              │
[7] Audit / Rejection ──────────────┘
      ↓
[8] Conditional Recommendation
      ↓
[9] Re-evaluation Trigger
```

Step 7 で全候補が棄却された場合、Step 4 に戻り候補を再生成する。
ただし v1 では再生成は最大1回。2回棄却されたら「現時点で推奨可能な候補なし」を正式出力とする。

---

## Step 1: Goal Intake

### Objective
ユーザーの自然言語ゴールを構造化し、User Intent Object を生成する。

### Why it matters
ここで取りこぼした意図や制約は、下流の全ステップに伝播する。特に投資リサーチドメインでは「何を達成したいか」と「何を絶対にやってはいけないか」の両方が明示されないと、候補生成が的外れになる。

### Inputs
- ユーザーの自然言語テキスト（1文～数段落）
- （あれば）過去の run_id によるコンテキスト

### Outputs
User Intent Object:
```
{
  run_id, created_at,
  raw_goal,
  domain: "investment_research",
  user_goal_summary,
  success_definition,
  risk_preference: very_low | low | medium | high,
  time_horizon_preference: fast | one_day | one_week | one_month | quality_over_speed,
  automation_preference: advice_only | research_assist | semi_automated | full_if_safe,
  must_not_do: [],
  available_inputs: [],
  open_uncertainties: []
}
```

### Key decisions

1. **曖昧入力の扱い**: ユーザーが risk_preference や time_horizon を明示しない場合、推測して埋めるのではなく、`open_uncertainties` に入れて Step 2 以降で補完を試みる。推測による穴埋めは false confidence の温床。

2. **domain フィールドの固定**: v1 では `domain` は常に `"investment_research"` に固定。ユーザーが投資リサーチ外のゴールを入力した場合、明示的に「v1 のスコープ外」と返す。曖昧に受け入れない。

3. **must_not_do の能動的抽出**: ユーザーが言及しなくても、投資ドメインの典型的禁止事項（例: レバレッジ使用の可否、特定資産クラスの除外、短期売買の制限）を確認リストとして提示し、該当するものを `must_not_do` に格納する。

4. **success_definition の強制**: 「利益を出す」のような曖昧な定義は受け付けない。最低でも「何に対して」「どの程度」「どの期間で」を含む定義を要求する。確定できない場合は `open_uncertainties` へ。

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| ユーザーが過度に曖昧なゴールしか出さない | high | 最低限の構造化質問セットを用意し、3往復以内で Intent Object を埋める。3往復超えたら「現時点の理解で進める」と宣言し open_uncertainties に残りを格納 |
| ユーザーの stated goal と real goal が乖離 | medium | success_definition の具体性を強制することで暗黙の乖離を表面化させる |
| must_not_do の取りこぼし | high | ドメイン固有の禁止事項チェックリストで能動的に確認 |
| ユーザーが投資ドメイン外の要求を投資っぽく見せて入力 | low | domain framing (Step 2) で検出しリジェクト |

### Explicitly out of scope
- 自然言語のニュアンス分析や感情推定
- ユーザーの過去の投資実績の取り込み
- 規制適合性チェック（v1 は規制アドバイスを出さない）
- 複数ドメインにまたがるゴールの分解

### v1 implementation notes
- Intent Object は JSON として内部的に保持。ユーザーには要約を自然言語で返す。
- 構造化質問セットは投資リサーチ特化で固定（汎用テンプレートにしない）。
- 質問セットの項目: ゴール、成功基準、リスク許容度、時間軸、利用可能データ、禁止事項、自動化許容度。最大7問。
- `open_uncertainties` は空でも許容するが、その場合 Step 3 で「不確実性ゼロと判断した根拠」をログに残す。

---

## Step 2: Domain Framing

### Objective
ユーザーのゴールを「投資リサーチにおける検証可能な問題」として再定義する。

### Why it matters
ユーザーは「〜するシステムを作りたい」と言うが、プロダクトが扱うのは「そのシステムの方向性は検証に耐えるか」という問題。この変換がこのステップの仕事。ここを飛ばすと、下流が「システムを設計する」タスクになり、Give Me a DAY のプロダクト価値が消える。

### Inputs
- User Intent Object (Step 1 output)

### Outputs
Domain Frame Object:
```
{
  run_id,
  reframed_problem: string,
  core_hypothesis: string,
  testable_claims: [],
  critical_assumptions: [],
  domain_specific_risks: [],
  regime_dependencies: [],
  comparable_known_approaches: []
}
```

### Key decisions

1. **reframed_problem の粒度**: ユーザーの「モメンタム戦略を使ったシステムが欲しい」は「モメンタムファクターが対象市場・期間において統計的に有意なリターンを生むか、その条件は何か」に再定義される。"作りたい" から "検証すべき" への変換が本質。

2. **testable_claims の分解**: 1つのゴールを複数の検証可能な主張に分解する。例: 「日本株のモメンタム戦略」→ (a) 日本株市場でモメンタムファクターは過去N年有意か (b) 取引コスト控除後も有意か (c) 特定レジーム（低ボラ / 高ボラ）で有意性が消えないか。

3. **regime_dependencies の明示**: 投資戦略は市場レジームに強く依存する。このステップで「どのレジーム前提で話しているか」を明示的に記録する。ユーザーが意識していない場合も強制的に問う。

4. **comparable_known_approaches の列挙**: ユーザーのアイデアに類似する既知のアプローチを列挙し、「既に検証済みの知見」と「ユーザーが新たに主張していること」を分離する。車輪の再発明を検出する。

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| reframed_problem がユーザーの意図とずれる | high | 再定義結果をユーザーに確認させるチェックポイントを設置 |
| testable_claims が検証不可能な形で書かれる | high | 各 claim に対し「何のデータがあれば棄却できるか」を必須フィールドとして付与。棄却条件が書けない claim は claim として不成立 |
| regime_dependencies を軽視し、全天候型を暗黙に仮定 | critical | regime_dependencies が空の場合はエラー扱い。最低1つのレジーム条件を明示させる |
| comparable_known_approaches が不完全で、既知の失敗パターンを見落とす | medium | 投資リサーチドメインの典型的アプローチカタログを内部参照データとして保持 |

### Explicitly out of scope
- マクロ経済予測そのもの
- ユーザーのゴールの優劣判断（「この戦略はやめた方がいい」は Step 7 の仕事）
- 実装アーキテクチャの検討（まだ早い）
- 規制・コンプライアンスの判断

### v1 implementation notes
- domain framing は投資リサーチドメインの知識ベースに依存する。v1 ではファクター投資・統計的アービトラージ・イベントドリブン・マクロ戦略・オルタナティブデータ活用の5大カテゴリをカバー。
- reframed_problem は必ず「〜は〜の条件下で検証可能か」の形式で記述する。
- comparable_known_approaches は学術論文・実務上の既知戦略の概要レベル。詳細なリテラチャーレビューは v1.5。
- ユーザー確認チェックポイントはこのステップの出力後に1回。「この理解で正しいか」のYes/No + 修正。

---

## Step 3: Research Spec Compilation

### Objective
Domain Frame を、検証実行に必要な全条件を記述した Research Spec Object に変換する。

### Why it matters
これは候補生成・証拠計画・検証計画の共通入力仕様書。ここの精度が低いと、候補が的外れになり、検証計画が空虚になり、棄却判定が恣意的になる。全下流モジュールの品質上限を決める。

### Inputs
- User Intent Object (Step 1)
- Domain Frame Object (Step 2)

### Outputs
Research Spec Object:
```
{
  spec_id, run_id,
  primary_objective: string,
  secondary_objectives: [],
  problem_frame: string,
  assumption_space: [],
  constraints: {
    time, budget, tooling: [], forbidden_behaviors: []
  },
  evidence_requirements: {
    required_data: [],
    optional_data: [],
    proxy_data_allowed: bool,
    evidence_gaps: []
  },
  validation_requirements: {
    must_test: [],
    must_compare: [],
    disqualifying_failures: [],
    minimum_evidence_standard: weak | moderate | strong
  },
  recommendation_requirements: {
    must_return_runner_up: true,
    must_return_rejections: true,
    must_surface_unknowns: true,
    allow_no_valid_candidate: true
  }
}
```

### Key decisions

1. **assumption_space の網羅性**: すべての候補に共通する前提（市場の効率性の程度、取引コストの仮定、データの品質仮定など）をここで明示する。候補固有の前提は Candidate Object 側に持つ。共通前提と候補固有前提の分離が重要。

2. **minimum_evidence_standard の決定ロジック**: ユーザーの risk_preference と time_horizon_preference から機械的に決定する。
   - risk_preference = very_low → strong
   - risk_preference = low + time_horizon = quality_over_speed → strong
   - risk_preference = medium → moderate
   - risk_preference = high + time_horizon = fast → weak（ただし警告付き）
   - これ以外の組み合わせ → moderate をデフォルトとし、理由を明記

3. **disqualifying_failures の事前定義**: 「この結果が出たら候補は即棄却」の条件をここで定義する。例: バックテストの Sharpe < 0.3、最大ドローダウン > 許容値、取引コスト控除後リターンが負。これが曖昧だと Step 7 の棄却判定が恣意的になる。

4. **recommendation_requirements の固定**: v1 では4つのフラグすべてを true に固定。「runner-up なし」「棄却なし」「未知数隠蔽」「必ず候補を出す」の挙動は全て許可しない。これはプロダクトの根本原則。

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| assumption_space が暗黙の前提を取りこぼす | critical | 投資リサーチ向けの前提チェックリスト（市場効率性、流動性、取引コスト、データバイアス、レジーム安定性、生存者バイアス等）を用意し、各項目を明示的に走査 |
| disqualifying_failures が厳しすぎて全候補が即死 | medium | 閾値はユーザーの risk_preference に連動させる。ただし「取引コスト控除後リターン負」は risk_preference に関係なく disqualifying |
| evidence_requirements が入手不可能なデータを required に入れる | high | required_data の各項目に availability_status (available / obtainable / unavailable) を付与。unavailable が required に入っている場合は Step 5 で警告 |
| spec が巨大になりすぎて下流で扱えない | low | primary_objective は1つに限定。secondary は最大3つ。assumption_space は最大15項目 |

### Explicitly out of scope
- データの実取得（計画のみ）
- 実装レベルの技術仕様
- 費用見積もり
- ベンダー選定

### v1 implementation notes
- Research Spec は一度生成したら Step 7 のフィードバック以外では変更しない。ユーザーが前提を変えたい場合は新しい run として最初から回す。
- recommendation_requirements の4つの true は v1 ではハードコード。設定変更不可。
- evidence_requirements.required_data の各項目は、後続の Evidence Planning (Step 5) で詳細化される。ここでは「カテゴリレベル」（例: 「日次終値データ」「ファンダメンタル四半期データ」）で記述。

---

## Step 4: Candidate Generation

### Objective
Research Spec に基づき、複数の候補システム方向を生成する。最低3候補（baseline / conservative / exploratory）。

### Why it matters
単一候補の推奨は比較なき推奨であり、プロダクトの根本価値に反する。候補の多様性が比較・棄却の品質を決める。

### Inputs
- Research Spec Object (Step 3)
- Domain Frame Object (Step 2)（comparable_known_approaches を参照）

### Outputs
Candidate Object の配列（最低3、最大5）:
```
{
  candidate_id, name,
  candidate_type: baseline | conservative | exploratory | hybrid,
  summary,
  architecture_outline: [],
  core_assumptions: [],
  required_inputs: [],
  validation_burden: low | medium | high,
  implementation_complexity: low | medium | high,
  expected_strengths: [],
  expected_weaknesses: [],
  known_risks: []
}
```

### Key decisions

1. **候補タイプの強制分散**: 全候補が同系統にならないよう、candidate_type の分布を強制する。v1 ルール: baseline 1つ + conservative 1つ + exploratory 1つを必須とし、任意で hybrid を追加可能。同一 type が2つ以上存在する場合、差異が architecture_outline レベルで明確に異なることを要求。

2. **baseline の定義**: baseline は「最もシンプルで、既知の手法に最も近い候補」。ユーザーのゴールに対する素朴な解。これが比較の基準線になる。baseline を sophisticated にすると比較の意味が薄れる。

3. **core_assumptions の独立性**: 各候補の core_assumptions は Research Spec の assumption_space とは別に記述する。Spec の assumption_space は全候補共通の前提。Candidate の core_assumptions はその候補固有の追加前提。重複は許容しない。

4. **known_risks の事前記入**: 候補生成時点で既知のリスクを記入する。Step 7 の Audit はこれに加えて新たなリスクを発見する。候補生成者が自らのリスクを書けないのは候補の成熟度不足の証拠。

5. **validation_burden の見積もり**: 候補の検証にどの程度のデータ・時間・計算資源が必要かを low/medium/high で見積もる。これは Step 6 の Validation Plan の実行可能性判断に使う。

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| 候補が表面的に異なるだけで本質的に同じ | critical | architecture_outline の差異を定量評価。共通コンポーネントが70%以上の場合はエラー |
| exploratory 候補が実行不可能なほど wild | medium | exploratory でも Research Spec の constraints 内であることを検証。constraints 違反は候補として不成立 |
| baseline が既にユーザーのゴールに対して不適切 | medium | baseline が disqualifying_failures に即抵触する場合、それ自体を Audit で記録した上で比較基準としては残す |
| 候補数が少なすぎる（3未満） | high | 3候補未満はシステムエラー。生成を再試行 |
| core_assumptions が曖昧 | high | 各 assumption に対し「これが偽だった場合、候補はどう壊れるか」の回答を必須化 |

### Explicitly out of scope
- 候補の実装コード生成
- 候補間の優劣判定（Step 7-8 の仕事）
- データの実取得
- 候補のバックテスト実行

### v1 implementation notes
- 候補生成はドメイン知識に強く依存する。v1 では投資リサーチの典型的アプローチパターン（ファクターモデル、統計モデル、ML モデル、ルールベース、ハイブリッド）をテンプレートとして内部保持。
- candidate_id は run_id + 連番で自動生成。
- architecture_outline は実装アーキテクチャではなく「概念的な構成要素の列挙」。例: [データ取得 → ファクター計算 → シグナル生成 → ポートフォリオ構築 → リスク管理 → 実行]。
- 候補は生成後に変更しない。Step 7 で棄却された後に修正版を作る場合は、新しい candidate_id を振る。

---

## Step 5: Evidence Planning

### Objective
各候補に対し、検証に必要なデータ・証拠を具体化し、取得可能性を評価する。

### Why it matters
候補の妥当性は「どんな証拠で検証するか」「その証拠は実際に手に入るか」に依存する。ここが弱いと、Validation Plan が「理想的にはこうテストすべき」という空論になる。

### Inputs
- Research Spec Object (Step 3) — evidence_requirements
- Candidate Object 配列 (Step 4)

### Outputs
各候補に紐づく Evidence Plan:
```
{
  candidate_id,
  evidence_items: [
    {
      item_id,
      category: price | fundamental | alternative | macro | sentiment | flow | metadata,
      description,
      requirement_level: required | optional | proxy_acceptable,
      availability: available | obtainable_with_effort | unavailable,
      quality_concerns: [],
      known_biases: [],
      temporal_coverage: { start, end, frequency },
      proxy_option: null | { description, quality_loss_estimate }
    }
  ],
  critical_gaps: [],
  gap_severity: none | manageable | blocking,
  notes
}
```

### Key decisions

1. **availability の3段階判定**:
   - `available`: ユーザーが既に持っている、または無料/低コストで即座に取得可能
   - `obtainable_with_effort`: 有料サービス契約、データベンダーへの依頼、手動収集等で取得可能だが時間・コストが発生
   - `unavailable`: 原理的に取得不可能、または法的・倫理的に取得不可

2. **proxy 許容の判定基準**: Research Spec の `proxy_data_allowed` が true でも、無条件に proxy を許容しない。proxy を使う場合は `quality_loss_estimate` を必須記入。quality_loss_estimate が「致命的」と判定された場合、proxy は使用不可。

3. **known_biases の強制列挙**: 投資データには survivorship bias、look-ahead bias、backfill bias、selection bias が頻出する。各 evidence_item に対しこれらのバイアスチェックを走査し、該当するものを記録。

4. **gap_severity の判定ロジック**:
   - `blocking`: required かつ unavailable の evidence_item が1つ以上ある
   - `manageable`: required だが obtainable_with_effort、または proxy_acceptable で proxy_option がある
   - `none`: required の全 evidence_item が available

5. **blocking gap がある候補の扱い**: 即棄却ではなく、Step 7 の Audit に「evidence gap: blocking」として渡す。Audit が棄却判定する。Evidence Planning は事実の記録に徹する。

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| evidence_item の粒度が粗すぎて検証計画が立てられない | high | 各項目に temporal_coverage (開始・終了・頻度) を必須化 |
| proxy の quality_loss_estimate が楽観的すぎる | critical | proxy 使用時は Audit で必ず追加検証項目として flagging |
| known_biases の見落とし | high | ドメイン固有バイアスチェックリスト（survivorship, look-ahead, backfill, selection, reporting delay）を全 evidence_item に走査 |
| ユーザーの available_inputs (Step 1) と evidence_items の不整合 | medium | available_inputs に含まれるデータと evidence_items を照合し、カバレッジレポートを生成 |

### Explicitly out of scope
- データの実取得・ダウンロード
- データクレンジング・前処理の実行
- データベンダーの価格比較
- データ品質の実測定（計画レベルの品質懸念の列挙のみ）

### v1 implementation notes
- evidence category は投資リサーチに特化した7分類（price / fundamental / alternative / macro / sentiment / flow / metadata）で固定。
- v1 では availability の判定はユーザーの自己申告 + 一般的な公開データの可用性情報に基づく。実際のデータアクセス検証は v1.5。
- critical_gaps は Recommendation Object の open_unknowns に直接流れる重要フィールド。

---

## Step 6: Validation Plan Generation

### Objective
各候補に対し、具体的な検証手順・指標・失敗条件・比較対象を定義する。

### Why it matters
検証計画のないシステム候補は「もっともらしい仮説」に過ぎない。失敗条件のない検証計画は「必ず成功するテスト」であり、無意味。このステップが Audit の判定材料を生む。

### Inputs
- Research Spec Object (Step 3) — validation_requirements
- Candidate Object 配列 (Step 4)
- Evidence Plan 配列 (Step 5)

### Outputs
各候補に紐づく Validation Plan Object:
```
{
  validation_plan_id,
  candidate_id,
  test_sequence: [
    {
      test_id,
      test_type: offline_backtest | walk_forward | paper_run | stress_test |
                 out_of_sample | regime_split | monte_carlo | sensitivity,
      description,
      required_evidence_items: [],
      metrics: [
        {
          name,
          calculation_method,
          pass_threshold,
          fail_threshold,
          comparison_target: null | baseline_candidate | benchmark | absolute_value
        }
      ],
      time_windows: [],
      failure_conditions: [],
      execution_prerequisites: [],
      estimated_effort: low | medium | high
    }
  ],
  plan_completeness: complete | partial_due_to_evidence_gaps | minimal,
  comparison_matrix: {
    candidates_compared: [],
    comparison_metrics: [],
    comparison_method: string
  },
  notes
}
```

### Key decisions

1. **test_sequence の順序強制**: テストは段階的に実行する設計。v1 のデフォルト順序:
   1. offline_backtest（基本的なバックテスト）
   2. out_of_sample（サンプル外検証）
   3. walk_forward（ウォークフォワード）
   4. regime_split（レジーム別分析）
   5. stress_test（ストレステスト）
   6. sensitivity（パラメータ感度分析）
   各テストに `execution_prerequisites` があり、前段テストの pass が後段の前提条件になる。

2. **failure_conditions の必須化**: 各テストに最低1つの failure_condition を持つ。failure_condition が書けないテストは設計不良。「このテストは何が起きたら失敗か」が言語化できないなら、そのテストは有意味ではない。

3. **comparison_matrix の強制**: 候補間比較は Step 8 の Recommendation の根拠。全候補を同一メトリクスで比較可能な構造を強制。baseline 候補は必ず比較対象に含める。

4. **metrics の pass/fail 閾値設定**: Research Spec の disqualifying_failures と連動。disqualifying に該当するメトリクスは fail_threshold が即棄却基準。non-disqualifying なメトリクスは比較材料として使用。

5. **plan_completeness の判定**: Evidence Plan の gap_severity に連動。
   - gap_severity = none → plan_completeness = complete
   - gap_severity = manageable → plan_completeness = partial_due_to_evidence_gaps
   - gap_severity = blocking → plan_completeness = minimal

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| failure_conditions が甘く設定され、全候補が pass してしまう | critical | Research Spec の disqualifying_failures を failure_conditions に自動マッピング。手動追加分は Audit でレビュー |
| 検証計画が実行不可能なほど重い | medium | estimated_effort を全テスト合計し、ユーザーの time_horizon_preference と照合。乖離が大きい場合は警告 |
| out_of_sample テストのデータ期間が不十分 | high | 最低要件: out_of_sample 期間 ≥ in_sample 期間の 1/3。これを下回る場合は Audit に flagging |
| comparison_matrix の指標が候補間で不公平 | medium | 全候補に同一メトリクスセットを適用。候補固有のメトリクスは追加は可だが、共通セットの省略は不可 |
| バックテスト期間の恣意的選択 | high | time_windows に選択根拠を必須記入。「結果が良い期間を選んだ」は Audit で検出 |

### Explicitly out of scope
- テストの実行（計画のみ）
- バックテストエンジンの実装
- データ取得の実行
- パフォーマンスレポートの生成

### v1 implementation notes
- test_type は投資リサーチに特化した8種に固定。汎用テストカテゴリは設けない。
- 各テストの metrics は投資ドメインの標準指標（Sharpe, Sortino, max drawdown, calmar, win rate, profit factor, turnover, transaction cost impact 等）から選択。カスタム指標は description で記述可能だが calculation_method を必須。
- comparison_matrix は必ず baseline 候補を含む。baseline なしの比較は不可。
- v1 では paper_run テストは「計画として記述可能」だが、実行支援は v1.5。

---

## Step 7: Audit / Rejection

### Objective
全候補を体系的に批判し、棄却すべき候補を棄却理由付きで落とす。

### Why it matters
**これがプロダクトの差別化の核。** 「何でも推奨するエンジン」ではなく「弱い方向を棄却するエンジン」。ここの品質がプロダクト全体の信頼性を決定する。Audit が甘ければ Give Me a DAY は「もっともらしいが検証されていない推奨を返す」だけのツールに堕落する。

### Inputs
- Candidate Object 配列 (Step 4)
- Evidence Plan 配列 (Step 5)
- Validation Plan 配列 (Step 6)
- Research Spec Object (Step 3) — disqualifying_failures, minimum_evidence_standard

### Outputs
各候補に紐づく Audit Object:
```
{
  candidate_id,
  audit_status: passed | passed_with_warnings | rejected,
  issues: [
    {
      issue_id,
      severity: low | medium | high | critical,
      category: assumption | evidence_gap | leakage_risk | complexity |
                realism | observability | regime_dependency |
                overfitting_risk | cost_assumption | recommendation_risk,
      title,
      explanation,
      mitigation: string | null,
      disqualifying: bool
    }
  ],
  rejection_reason: null | string,
  surviving_assumptions: [],
  residual_risks: []
}
```

### Key decisions

1. **棄却の閾値ロジック**:
   - `disqualifying: true` の issue が1つでもあれば → `audit_status = rejected`
   - `severity: critical` かつ `mitigation: null` → 自動的に `disqualifying: true`
   - `severity: critical` かつ `mitigation` あり → Audit は `disqualifying: false` と判定可能だが、`recommendation_risk` カテゴリの warning を追加必須
   - `severity: high` が3つ以上 → `passed_with_warnings` とし、Recommendation で条件付き注釈を強制

2. **投資ドメイン固有の批判カテゴリ（10分類）**:
   - `assumption`: 根拠が弱いか検証されていない前提
   - `evidence_gap`: 必要な証拠が不足または取得不可
   - `leakage_risk`: look-ahead bias, survivorship bias, data snooping
   - `complexity`: 実装・運用・保守の複雑さが妥当性を超えている
   - `realism`: 取引コスト、流動性、スリッページ等の実務的現実性
   - `observability`: 稼働中にシステムの健全性を監視できるか
   - `regime_dependency`: 特定市場レジームへの過度な依存
   - `overfitting_risk`: パラメータ数、最適化期間、自由度の過大
   - `cost_assumption`: データコスト、インフラコスト、取引コストの仮定の甘さ
   - `recommendation_risk`: この候補を推奨した場合に発生するリスク

3. **全候補棄却時の挙動**: 全候補が rejected の場合:
   - 1回目: Step 4 に戻り、棄却理由を制約条件として追加した上で候補を再生成
   - 2回目: 「現時点で推奨可能な候補なし」を正式出力とする。これはプロダクトの正常動作であり、異常ではない。`allow_no_valid_candidate: true` がこれを保証

4. **surviving_assumptions と residual_risks の出力**: passed / passed_with_warnings の候補について、Audit を通過した後も残存する前提とリスクを明記する。これが Step 8 の「条件付き」の条件になる。

5. **Audit の独立性**: Audit は候補生成 (Step 4) のロジックとは独立に動作する。候補生成が「この候補は強い」と判断しても、Audit が独自に棄却できる。候補生成者とAuditorsの分離が品質の鍵。

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| Audit が寛容すぎて全候補 pass | critical | 各 Audit に最低 issue 件数の下限は設けないが、issue 0件の候補に対しては「Audit が十分に機能したか」のメタ検証を実施。投資ドメインで issue 0 は極めて非現実的 |
| Audit が厳格すぎて全候補 rejected | medium | 1回の再生成を許容。2回連続全棄却は正常出力として処理 |
| leakage_risk の検出漏れ | critical | look-ahead bias / survivorship bias / data snooping のチェックリストを全候補に走査。evidence_items の temporal_coverage と validation plan の time_windows を照合し、未来データ参照の可能性を検出 |
| overfitting_risk の過小評価 | high | パラメータ数 / サンプルサイズ比を定量評価。比率が高い場合は自動 flagging |
| Audit の根拠が曖昧で「なんとなく reject」になる | high | 各 issue に explanation を必須化。explanation が1文以下の issue は無効 |

### Explicitly out of scope
- 候補の修正・改善提案（Audit は批判のみ。改善は次の候補生成サイクルで）
- バックテスト結果に基づく Audit（v1 では計画レベルの Audit。結果ベースは v1.5）
- 規制適合性の Audit
- ユーザーの能力・経験に基づく実行可能性の Audit

### v1 implementation notes
- 10個の批判カテゴリは v1 で固定。カテゴリの追加は v1.5 で検討。
- Audit は各候補に対して独立に実行。候補間の相対比較は Step 8 の仕事。
- 棄却理由 (rejection_reason) は1文ではなく、最低3文の構造化テキスト（何が問題か → なぜ致命的か → 修正可能性の有無）。
- surviving_assumptions は Recommendation Object の critical_conditions に直接マッピングされる。
- Audit のメタ検証（Audit 自体の品質チェック）は v1.5。v1 では issue 0件時の警告のみ。

---

## Step 8: Conditional Recommendation

### Objective
Audit を通過した候補から、条件付きで最良候補を選定し、推奨パッケージを生成する。

### Why it matters
これがユーザーが最終的に受け取る成果物。ただし「最良」は無条件ではなく、「これらの前提が正しい限り、これらの証拠が得られれば、この条件下で最良」という形式。条件を省略した推奨は Give Me a DAY のプロダクト価値の否定。

### Inputs
- Audit Object 配列 (Step 7)
- Candidate Object 配列 (Step 4)
- Validation Plan 配列 (Step 6)
- Evidence Plan 配列 (Step 5)
- Research Spec Object (Step 3)

### Outputs
Recommendation Object:
```
{
  best_candidate_id: string | null,
  runner_up_candidate_id: string | null,
  rejected_candidate_ids: [],
  ranking_logic: [],
  open_unknowns: [],
  critical_conditions: [],
  monitoring_or_recheck_rules: [],
  confidence_label: low | medium | high,
  confidence_explanation: string,
  next_validation_steps: [],
  recommendation_expiry: {
    type: time_based | event_based | evidence_based,
    description: string
  }
}
```

### Key decisions

1. **ranking_logic の明示**: best と runner-up の選定理由を比較形式で記述する。「Candidate A は Candidate B より〜の点で優れるが、〜の点で劣る。〜の条件下では A が推奨」。序列の根拠が不透明な推奨は無効。

2. **confidence_label の判定ロジック**:
   - `high`: 全 required evidence が available、Audit の critical issue なし、validation plan が complete、disqualifying failures に抵触する候補特性なし
   - `medium`: 一部 evidence に gap があるが manageable、Audit の critical issue が mitigated、validation plan が partial
   - `low`: evidence gap が blocking に近い、Audit の high severity issue が3+、validation plan が minimal、または全候補棄却で「推奨なし」
   - v1 では confidence_label = high は極めて稀であるべき。計画段階で high confidence はほぼありえない。high が頻出する場合はシステムの calibration を疑う。

3. **critical_conditions の構文**: 各条件は「もし〜なら、この推奨は無効」の否定条件で記述する。例: 「もし 2020年以降の日本株モメンタムファクターのサンプル外 Sharpe が 0.3 未満なら、この推奨は無効」。

4. **best_candidate_id = null の場合**: 全候補棄却時。この場合も ranking_logic（なぜ全候補が不適格か）、open_unknowns、next_validation_steps は必須。「何もわからないので何もできない」は許容しない。

5. **recommendation_expiry の導入**: 推奨には有効期限がある。市場環境の変化、新データの取得、前提の変化によって推奨は無効化される。`type` は以下の3種:
   - `time_based`: N日後に再検討
   - `event_based`: 特定イベント（政策変更、市場レジーム転換等）発生時
   - `evidence_based`: 新しい証拠が得られた時

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| confidence_label が楽観的すぎる | critical | 判定ロジックを機械的に適用。手動での confidence 引き上げは禁止 |
| critical_conditions が曖昧で検証不可能 | high | 各条件に「何のデータで検証するか」「いつ検証するか」を付記 |
| ranking_logic が「総合的に判断」のような空虚な記述 | high | 比較軸を最低3つ明示し、各軸での優劣を個別記述。「総合的」は禁止語 |
| ユーザーが条件部分を無視して best_candidate_id だけを参照する | medium | UX層の問題だがシステム層でも対策: Recommendation Object の先頭に conditions_summary (1段落の平文) を配置 |
| open_unknowns が多すぎて推奨が実質的に無意味 | medium | open_unknowns が5つを超える場合、confidence_label を強制的に low にする |

### Explicitly out of scope
- 推奨候補の実装計画
- ポートフォリオ構築の具体的指示
- 取引シグナルの生成
- リターンの予測値の提示

### v1 implementation notes
- Recommendation Object は最終ユーザー向け出力の構造化データ。これをもとにユーザー向けレポート（自然言語）を生成するが、レポート生成は別モジュール（Reporting）の責務。
- confidence_label = high が出力の10%を超える場合はシステム calibration の見直しフラグ。
- recommendation_expiry は v1 では必須フィールド。有効期限なしの推奨は生成しない。
- next_validation_steps の各項目は「誰が」「何のデータで」「どのテストを」「どの閾値で」の4要素を含む。「バックテストをすべき」レベルの粒度は不可。

---

## Step 9: Re-evaluation Trigger

### Objective
推奨を無効化する条件を事前定義し、ユーザーに「いつ再検討すべきか」を明示する。

### Why it matters
投資リサーチの推奨は時間とともに劣化する。市場レジームの変化、新データの出現、前提の崩壊により、昨日の推奨が今日は有害になりうる。このステップがないと、ユーザーは古い推奨を無批判に使い続けるリスクを負う。

### Inputs
- Recommendation Object (Step 8)
- Domain Frame Object (Step 2) — regime_dependencies
- Research Spec Object (Step 3) — assumption_space

### Outputs
Re-evaluation Trigger Set:
```
{
  run_id,
  triggers: [
    {
      trigger_id,
      trigger_type: time_based | data_based | market_event | assumption_invalidation | performance_degradation,
      description,
      detection_method: string,
      urgency: routine | elevated | immediate,
      affected_elements: [],
      recommended_action: rerun_full_loop | rerun_from_step_N | update_evidence_only | manual_review
    }
  ],
  default_recheck_interval: string,
  notes
}
```

### Key decisions

1. **trigger_type の5分類**:
   - `time_based`: 一定期間経過後の定期再検討
   - `data_based`: 新しいデータセットが利用可能になった時
   - `market_event`: 政策変更、金利変動、市場クラッシュ等
   - `assumption_invalidation`: Research Spec の assumption_space のいずれかが偽と判明した時
   - `performance_degradation`: 推奨候補の実運用パフォーマンスが想定を下回った時

2. **urgency の判定**: 
   - `routine`: 定期再検討の一環。月次～四半期。
   - `elevated`: 前提の一部に疑義が生じた。1-2週間以内の再検討を推奨。
   - `immediate`: 前提の根幹が崩壊した可能性。即座に推奨を保留し再検討。

3. **recommended_action の粒度**: 全ループの再実行が常に必要ではない。trigger の種類により、Step 5 (Evidence Planning) からの再開で十分な場合もある。無駄な再計算を避けつつ、必要な再検証は漏らさない。

4. **default_recheck_interval**: ユーザーの time_horizon_preference に連動。
   - fast / one_day → 週次
   - one_week → 隔週
   - one_month → 月次
   - quality_over_speed → 四半期

### Risks / failure modes

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| trigger が多すぎてユーザーが無視する | medium | 最大10 triggers に制限。優先度順にソート |
| trigger の detection_method が曖昧で検出不可能 | high | 各 trigger に具体的な検出条件（指標名、閾値、データソース）を必須化 |
| market_event trigger が後知恵でしか検出できない | medium | 事前に観測可能な proxy indicator を detection_method に含める |
| assumption_invalidation trigger が assumption_space と不整合 | low | assumption_space の各項目に対応する trigger を自動生成し、漏れをチェック |

### Explicitly out of scope
- trigger のリアルタイム監視システムの実装
- 自動再実行のオーケストレーション
- アラート配信システム
- パフォーマンストラッキングダッシュボード

### v1 implementation notes
- v1 では trigger は「定義のみ」。監視・検出・自動再実行は v1.5 以降。
- trigger set は Recommendation Object と一体で出力される。分離しない。
- assumption_space の各項目に対して少なくとも1つの trigger が自動生成されることを検証する。
- performance_degradation trigger は v1 では「定義可能」だが、実パフォーマンスデータのフィードバックは v1.5。v1 では想定パフォーマンス閾値を事前設定するのみ。

---

## ループ全体の制約と原則

### 不変条件（invariants）

1. **全ステップの出力は JSON-serializable であること。** 構造化されていない自然言語のみの出力は中間ステップとして不可。
2. **Step 7 (Audit) を経由しない候補は Step 8 (Recommendation) に到達しない。** バイパス不可。
3. **Recommendation Object の confidence_label は機械的に決定される。** 手動オーバーライド不可。
4. **rejected 候補とその棄却理由は最終出力に含まれる。** 棄却情報の消去は不可。
5. **open_unknowns が空の Recommendation は生成不可。** 計画段階で不確実性ゼロは非現実的であり、それを主張するシステムは calibration が壊れている。

### ステップ間のデータフロー制約

| 上流 | 下流 | 渡すもの | 渡さないもの |
|------|------|----------|------------|
| Step 1 → Step 2 | User Intent Object | ユーザーの過去の投資実績 |
| Step 2 → Step 3 | Domain Frame Object | 実装アーキテクチャ |
| Step 3 → Step 4 | Research Spec Object | 候補の優劣判断 |
| Step 3 → Step 5 | evidence_requirements | データの実体 |
| Step 4 → Step 5 | Candidate Object 配列 | 候補のランキング |
| Step 4 → Step 6 | Candidate Object 配列 | テスト結果 |
| Step 5 → Step 6 | Evidence Plan 配列 | データの実体 |
| Step 6 → Step 7 | Validation Plan 配列 | テスト結果 |
| Step 7 → Step 8 | Audit Object 配列 | 候補の修正提案 |
| Step 8 → Step 9 | Recommendation Object | 実行計画 |

### 全候補棄却時のフロー

```
Step 7: 全候補 rejected
  ↓
  判定: 再生成回数 < 1?
  ├─ Yes → Step 4 に戻る（棄却理由を制約として追加）
  └─ No  → Step 8 に進む（best_candidate_id = null で推奨パッケージ生成）
```

### v1 / v1.5 / v2 のスコープ分離

| 機能 | v1 | v1.5 | v2 |
|------|----|----|-----|
| 計画レベルの core loop 全9ステップ | ✓ | | |
| 投資リサーチドメイン固有知識ベース | ✓ | | |
| ユーザー確認チェックポイント (Step 2 後) | ✓ | | |
| 全候補棄却 → 再生成 (1回) | ✓ | | |
| バックテスト結果に基づく Audit | | ✓ | |
| Evidence の自動取得・検証 | | ✓ | |
| Trigger の自動監視 | | ✓ | |
| パフォーマンスフィードバックループ | | ✓ | |
| 複数ドメイン対応 | | | ✓ |
| 自動再実行オーケストレーション | | | ✓ |
| ユーザーのデータソースへの直接接続 | | | ✓ |
