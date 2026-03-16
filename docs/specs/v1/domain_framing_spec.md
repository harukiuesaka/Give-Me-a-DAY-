# Give Me a DAY v1 — Domain Framing Design Specification

**Document type**: Internal logic + domain knowledge specification
**Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
**Version**: v1 draft
**Status**: Design phase — pre-implementation
**Input**: UserIntent Object (from Goal Intake, Step 1)
**Output**: DomainFrame Object (consumed by Research Spec Compilation, Step 3)
**Schema reference**: internal_schema_v1_consolidated.md §2 (DomainFrame Object)

---

## 1. Domain Framing の目的

Domain Framing は「ユーザーの願望を、検証可能な研究問題に変換するステップ」である。

Goal Intake が「何をしたいか」を取得するのに対し、Domain Framing は「何を検証すべきか」を定義する。この変換がプロダクトの中核的価値。

ユーザーが言う:
> 「日本株でモメンタム戦略を試したい」

システムが変換する:
> 「日本株市場においてモメンタムファクターが、取引コスト控除後かつ複数の市場レジームを通じて、統計的に有意なリスク調整後リターンを生むか」

この変換には3つの操作が含まれる:

1. **再定義 (Reframe)**: 「作りたい」を「検証すべき」に転換する
2. **分解 (Decompose)**: 1つの願望を、独立に検証可能な複数の主張に分解する
3. **文脈化 (Contextualize)**: 既知の研究成果・市場条件・レジーム前提を明示的に紐付ける

Domain Framing を飛ばすと、下流の全ステップが「ユーザーが言ったことをそのまま実現する」モードで動き、Give Me a DAY は汎用コード生成ツールに堕落する。

---

## 2. UserIntent → DomainFrame 変換ロジック

### 変換の全体フロー

```
UserIntent
  │
  ├─ raw_goal ─────────────────→ Strategy Archetype 判定
  │                                   │
  │                                   ↓
  ├─ user_goal_summary ─────────→ reframed_problem 生成
  │                                   │
  │                                   ↓
  ├─ success_definition ─────────→ testable_claims 分解
  │                                   │
  ├─ risk_preference ────────────→ regime_dependencies 抽出
  │                                   │
  ├─ must_not_do ────────────────→ 制約の文脈化
  │                                   │
  ├─ available_inputs ───────────→ comparable_known_approaches 選定
  │                                   │
  └─ open_uncertainties ─────────→ critical_assumptions 特定
                                      │
                                      ↓
                                DomainFrame Object
```

### Step 2a: Strategy Archetype 判定

`raw_goal` と `user_goal_summary` を解析し、ユーザーのゴールがどの戦略アーキタイプに該当するかを判定する。アーキタイプは testable_claims の分解パターンと comparable_known_approaches の選定を決定する。

v1 で扱うアーキタイプ（§3 のドメインパターン辞書で詳述）:

| Archetype ID | Name | 検出キーワード例 |
|-------------|------|----------------|
| `FACTOR` | ファクター投資 | モメンタム、バリュー、クオリティ、サイズ、低ボラ、ファクター、マルチファクター |
| `STAT_ARB` | 統計的アービトラージ | ペアトレード、裁定、平均回帰、共和分、スプレッド |
| `EVENT` | イベントドリブン | 決算、M&A、IPO、自社株買い、配当、イベント |
| `MACRO` | マクロ戦略 | 金利、為替、GDP、インフレ、マクロ、景気循環、セクターローテーション |
| `ML_SIGNAL` | 機械学習シグナル | 機械学習、予測モデル、ニューラルネット、特徴量、AI |
| `ALT_DATA` | オルタナティブデータ活用 | 衛星、SNS、クレジットカード、オルタナティブ、非伝統的 |
| `HYBRID` | 複合型 | 上記の複数に該当 |
| `UNCLASSIFIED` | 未分類 | 上記のいずれにも明確に該当しない |

判定ルール:
- キーワードマッチ + 文脈解析で判定。単一キーワードの存在だけでは判定しない（「モメンタム」が含まれていても、文脈が「組織のモメンタム」であれば非該当）
- 複数アーキタイプに該当する場合は `HYBRID` とし、primary / secondary を記録
- いずれにも該当しない場合は `UNCLASSIFIED` とし、Follow-up で明確化（§5 で詳述）

### Step 2b: reframed_problem 生成

UserIntent の `user_goal_summary` を、以下のテンプレートに変換する。

**変換テンプレート**:
```
「[対象市場/資産クラス] において [戦略アプローチ/ファクター/シグナル] が、
[制約条件] のもとで、[成功指標] の観点から検証に耐えるか」
```

変換時に強制的に追加する要素:
- **対象市場**: raw_goal から抽出。未指定の場合は open_uncertainties に追加し、仮に「指定なし（全市場）」としては**進めない**。市場未指定は testable_claims が立てられない。Follow-up で明確化。
- **制約条件**: must_not_do + 暗黙の制約（取引コスト、流動性）
- **成功指標**: success_definition から導出

**変換例**:

| user_goal_summary | reframed_problem |
|-------------------|-----------------|
| 日本株でモメンタム戦略を試したい | 日本株市場においてモメンタムファクターが、取引コスト控除後かつ流動性制約のもとで、リスク調整後リターンの観点から統計的に有意な超過収益を生むか |
| 決算発表後の株価の動きで利益を出せるか調べたい | 日本株（または対象市場）において決算発表後の株価アノマリーが、取引可能なタイムフレームと実務的な執行条件のもとで、再現可能かつ経済的に有意な収益機会を提供するか |
| マクロ指標で株のセクターを切り替える戦略 | マクロ経済指標の変動がセクター間のリターン格差を予測する力を持ち、その予測力が取引コストとタイミング遅延を控除した後も経済的に有意か |

### Step 2c: testable_claims 分解

reframed_problem を、独立に検証可能な複数の主張に分解する。分解パターンはアーキタイプごとに異なる（§3 で詳述）。

**分解の原則**:

1. **独立検証可能性**: 各 claim は他の claim の結果に依存せず、単独でテスト可能
2. **反証条件の必須性**: 各 claim に `falsification_condition` を付与。「何のデータがあれば否定できるか」が言語化できない claim は claim として不成立
3. **段階的構造**: claims は「前提条件 → 核心主張 → 実務的成立性」の3層で構成。前提 claim が棄却されたら核心 claim の検証は不要
4. **網羅性**: reframed_problem の全側面をカバー。1つの claim だけでは reframed_problem 全体を検証できない

**3層構造**:

```
Layer 1: 前提条件 claims
  「このファクター/シグナル/パターンは統計的に存在するか」
  → 存在しなければ、以降の検証は不要

Layer 2: 核心主張 claims
  「この存在が、投資戦略として活用可能な大きさ・安定性を持つか」
  → 存在するが小さすぎる、不安定すぎる場合は実用性なし

Layer 3: 実務的成立性 claims
  「取引コスト・流動性・執行制約を考慮した後も収益性が残るか」
  → 理論的には有効でも、実務で消える場合は不成立
```

### Step 2d: regime_dependencies 抽出

以下のソースから regime_dependencies を能動的に抽出する:

1. **アーキタイプ固有のレジーム依存**: 各アーキタイプには典型的なレジーム依存がある（§3 で詳述）
2. **ユーザーの暗黙前提**: raw_goal に特定期間の言及がある場合（例:「コロナ以降うまくいっている」→ 低金利・高流動性レジームへの依存を示唆）
3. **risk_preference との連動**: very_low / low の場合、レジーム転換時のリスクが特に重要。regime_dependencies の粒度を上げる

**regime_dependencies が空の場合はエラー。** 全ての投資戦略はレジームに依存する。依存がないと主張する候補は、依存を認識していないだけ。システムは最低1つのレジーム依存を強制的に記録する。

デフォルトで追加するレジーム依存（全アーキタイプ共通）:
- 市場全体のトレンド方向（上昇/下降/横ばい）
- ボラティリティ環境（高/低）

### Step 2e: comparable_known_approaches 選定

アーキタイプとユーザーのゴールに基づき、学術研究・実務で既知の類似アプローチを列挙する。

目的:
- 「車輪の再発明」の検出: ユーザーのアイデアが既知の手法そのものなら、既知の結果を出発点にできる
- ベースライン設定の材料: comparable approaches は Step 4 の baseline 候補の参考になる
- 棄却済み手法の警告: 既知手法が既に「機能しない」と結論されている場合、その情報を早期に提示

v1 の知識ベース範囲は §7 で定義。

### Step 2f: critical_assumptions 特定

以下を `critical_assumptions` に記録する:

1. reframed_problem の成立に必要な前提（例: 「モメンタムファクターが日本株市場で機能する」はそれ自体が検証対象だが、「日本株市場が十分に流動的である」はその前提）
2. UserIntent の `open_uncertainties` から導出される暗黙の前提
3. アーキタイプ固有の典型的前提（§3 で詳述）

---

## 3. ドメインパターン辞書

各アーキタイプに対し、testable_claims の分解パターン、典型的レジーム依存、典型的前提、comparable_known_approaches を定義する。

---

### Archetype: FACTOR — ファクター投資

#### 説明
特定の企業属性（ファクター）がリターンの予測力を持つという仮説に基づく戦略。バリュー、モメンタム、クオリティ、サイズ、低ボラティリティ等。

#### testable_claims 分解パターン

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L1-前提 | 「[ファクター名]が[対象市場]において過去[N年]にわたり、リターンとの統計的に有意な関係を持つ」 | 「[対象市場]の[N年]データでファクターリターンのt値 < 2.0、またはp値 > 0.05」 |
| L1-前提 | 「[ファクター名]のリターン分布がバックテスト可能な統計的性質を持つ（正規性、定常性の程度）」 | 「ファクターリターンの時系列に単位根が存在、またはADF検定で非定常と判定」 |
| L2-核心 | 「[ファクター名]のリターンが、サンプル外期間でもサンプル内期間の[X%]以上を維持する」 | 「サンプル外Sharpeがサンプル内Sharpeの50%未満」 |
| L2-核心 | 「[ファクター名]のリターンが複数のレジーム（上昇/下降/高ボラ/低ボラ）を通じて正であるか、少なくとも壊滅的でない」 | 「特定レジームでファクターリターンが年率-10%以下」 |
| L3-実務 | 「ファクターに基づくポートフォリオのターンオーバーが、取引コスト控除後もリターンを残す水準である」 | 「年間ターンオーバー × 片道コスト > ファクターリターンの50%」 |
| L3-実務 | 「ファクターポートフォリオの構成銘柄が、十分な流動性を持つ」 | 「ポートフォリオの10%以上の銘柄で、日次取引量 < 必要取引量」 |

#### 典型的 regime_dependencies
- 金利環境（バリューファクターは金利上昇期に強い傾向）
- 市場トレンド方向（モメンタムは強いトレンド期に機能しやすい）
- ボラティリティ環境（低ボラファクターは高ボラ期に逆行する傾向）
- ファクタークラウディング（同一ファクターへの資金集中度合い）

#### 典型的 critical_assumptions
- 市場にファクターリターンを生む構造的非効率が存在し、裁定されきっていない
- ファクターの計測方法が結果に過度に依存しない（ファクター定義の頑健性）
- 過去のファクターリターンが将来を予測する（定常性仮定）

#### comparable_known_approaches
- Fama-French 3/5ファクターモデル
- AQR のファクター研究
- 各地域市場でのファクターリターンの実証研究
- ファクタータイミング研究（Arnott et al., Asness et al.）

#### 変換例

**UserIntent**:
```
raw_goal: "日本株でバリュー戦略をやりたい"
success_definition: "市場平均を年率3%上回る / 5年以上"
risk_preference: medium
```

**DomainFrame**:
```json
{
  "reframed_problem": "日本株市場においてバリューファクター（PBR, PER等の指標で測定）が、取引コストと流動性制約のもとで、5年以上の期間にわたりTOPIXを年率3%以上上回るリスク調整後リターンを生むか",
  "core_hypothesis": "日本株市場にバリュープレミアムが存在し、実務的に収穫可能である",
  "testable_claims": [
    {
      "claim_id": "TC-01",
      "claim": "日本株市場において、PBR下位銘柄群が上位銘柄群に対し、過去20年間で統計的に有意なリターン格差を持つ",
      "falsification_condition": "PBR下位-上位のロングショートリターンのt値 < 2.0"
    },
    {
      "claim_id": "TC-02",
      "claim": "バリューファクターリターンがサンプル外期間（直近5年）でもサンプル内期間の50%以上を維持する",
      "falsification_condition": "サンプル外Sharpeがサンプル内Sharpeの50%未満"
    },
    {
      "claim_id": "TC-03",
      "claim": "バリューファクターリターンが下落相場（TOPIXが年率-10%以下の期間）で壊滅的でない",
      "falsification_condition": "下落相場期間のバリューファクターの最大ドローダウンがTOPIXの最大ドローダウンの1.5倍超"
    },
    {
      "claim_id": "TC-04",
      "claim": "バリューポートフォリオ（月次リバランス）のターンオーバーコストが、ファクターリターンの50%以内である",
      "falsification_condition": "年間ターンオーバー × 推定片道コスト（20bps想定）> ファクター年率リターンの50%"
    }
  ],
  "critical_assumptions": [
    "日本株市場に価格発見が不完全な領域が存在し、バリュー銘柄が系統的に過小評価されている",
    "使用する財務データ（PBR等）がpoint-in-timeで利用可能であり、報告ラグが適切に考慮される",
    "バリューファクターの定義（PBR vs PER vs 複合）が結果に過度な影響を与えない"
  ],
  "regime_dependencies": [
    "金利環境: 日本の超低金利環境はバリューファクターに独自の影響を与える可能性（金利正常化時に挙動が変わるリスク）",
    "市場トレンド: 下落相場ではバリュートラップ（割安だが業績悪化する銘柄）リスクが増大",
    "ファクタークラウディング: 日本株でのバリュー戦略の普及度合いによるアルファ侵食"
  ],
  "comparable_known_approaches": [
    {
      "name": "Fama-French バリューファクター（日本市場）",
      "relevance": "同一市場での同一ファクターの学術的検証結果が存在",
      "known_outcome": "長期的にはプレミアムが存在するが、2010年代は低迷期が長かった"
    },
    {
      "name": "AQR Japan Value",
      "relevance": "実務運用者による日本バリュー戦略の実績",
      "known_outcome": "長期的にはプラスだが、短期的な大幅ドローダウンが複数回発生"
    }
  ]
}
```

---

### Archetype: STAT_ARB — 統計的アービトラージ

#### 説明
価格の統計的関係（共和分、平均回帰、スプレッドの安定性）を利用する戦略。ペアトレード、バスケットトレード、統計的平均回帰を含む。

#### testable_claims 分解パターン

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L1 | 「[対象ペア/バスケット]の価格スプレッドが統計的に平均回帰性を持つ（共和分検定で有意）」 | 「Engle-Granger 共和分検定 or Johansen 検定で有意でない（p > 0.05）」 |
| L1 | 「平均回帰の半減期が、取引可能なタイムフレーム内である」 | 「推定半減期 > ポジション保有の実務的上限（例: 60営業日）」 |
| L2 | 「スプレッドの平均回帰パターンがサンプル外で安定している」 | 「サンプル外期間でのスプレッドの回帰速度がサンプル内の50%未満に低下」 |
| L2 | 「スプレッドの乖離が十分な頻度で発生し、年間の取引機会が十分にある」 | 「年間のエントリーシグナル発生回数 < 12回」 |
| L3 | 「スプレッド取引の執行コスト（両建て）が、スプレッド回帰による利益を侵食しない」 | 「1取引あたりの往復コスト > 平均スプレッド回帰幅の30%」 |
| L3 | 「ペアの構成銘柄の借株コスト（ショート側）が戦略の収益性を棄損しない」 | 「平均借株コスト > スプレッドリターンの20%」 |

#### 典型的 regime_dependencies
- 市場の相関構造の安定性（相関ブレイクダウン期にペア関係が崩壊）
- ボラティリティレジーム（高ボラ期にスプレッドが拡大し収束しないリスク）
- 流動性レジーム（流動性危機時にショートサイドの借株困難化）

#### 典型的 critical_assumptions
- ペアの共和分関係が構造的（経済的理由がある）であり、偶然の相関ではない
- スプレッドの平均回帰速度が時間的に安定している
- ショートセリングが実行可能かつ合理的なコストで可能

#### comparable_known_approaches
- Gatev et al. (2006) の距離法ペアトレード
- 共和分ベースのペアトレード（Engle-Granger法）
- ETF間の統計的アービトラージ

---

### Archetype: EVENT — イベントドリブン

#### 説明
特定の企業イベント（決算発表、M&A、IPO、自社株買い等）の前後で株価に系統的なパターンが存在するという仮説に基づく戦略。

#### testable_claims 分解パターン

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L1 | 「[イベント種類]の前後[N日]に、[対象市場]で統計的に有意な超過リターン（CAR）が存在する」 | 「イベントスタディのCAR（累積超過リターン）のt値 < 2.0」 |
| L1 | 「このイベントパターンが十分な頻度で発生し、戦略として成立するサンプルサイズがある」 | 「年間イベント数 < 50 で統計的検出力が不足」 |
| L2 | 「イベントパターンがサンプル外期間でも再現する」 | 「サンプル外CARがサンプル内CARの50%未満、または統計的に非有意」 |
| L2 | 「イベントの「サプライズ」成分を事前に推定可能か（予測可能部分 vs サプライズ部分の分離）」 | 「サプライズ指標のリターン予測力がゼロと区別不能」 |
| L3 | 「イベント発生からポジション構築までの実務的なタイムラグを考慮しても超過リターンが残る」 | 「イベント公表からT+1（翌営業日）で執行した場合、CARが消失」 |
| L3 | 「イベント周辺の流動性（スプレッド拡大、出来高変動）を考慮しても超過リターンが残る」 | 「イベント周辺のスプレッド拡大コストがCARの50%以上を侵食」 |

#### 典型的 regime_dependencies
- 市場全体のセンチメント（楽観期 vs 悲観期でイベント反応が異なる）
- ボラティリティ環境（高ボラ期にイベント効果が市場ノイズに埋もれる）
- イベントの密度（決算シーズンの集中度）

#### 典型的 critical_assumptions
- イベントの定義が明確で、事前に検出可能（曖昧なイベント定義は data snooping の温床）
- イベント日が正確に記録されており、point-in-time で利用可能
- イベントに対する市場の反応パターンが時間的に安定している

#### comparable_known_approaches
- Post-Earnings Announcement Drift (PEAD)
- Merger Arbitrage の実証研究
- IPO アンダープライシング研究
- 自社株買いアナウンスメント効果

---

### Archetype: MACRO — マクロ戦略

#### 説明
マクロ経済指標の変動を利用し、資産クラス間・セクター間・国間のアロケーションを行う戦略。

#### testable_claims 分解パターン

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L1 | 「[マクロ指標]が[資産/セクターのリターン格差]に対し、統計的に有意な予測力を持つ」 | 「マクロ指標のリターン予測回帰のR² < 1%かつt値 < 2.0」 |
| L1 | 「マクロ指標の変動がアセットリターンに先行する（同時性や逆因果ではない）」 | 「Granger因果性検定で有意でない、またはリード・ラグ分析で先行関係が確認できない」 |
| L2 | 「予測力がサンプル外でも維持される（特に構造変化を含む期間で）」 | 「サンプル外のout-of-sample R²が負（ランダム予測以下）」 |
| L2 | 「マクロ指標の公表タイミング（報告ラグ）を考慮した後も予測力が残る」 | 「point-in-time データ（速報値ベース）での予測力が確定値ベースの50%未満」 |
| L3 | 「アロケーション変更の頻度と取引コストが、予測力による超過リターンを消さない」 | 「リバランスコスト > マクロシグナルによる超過リターンの50%」 |

#### 典型的 regime_dependencies
- **構造変化リスクが最大のアーキタイプ**: マクロ環境自体がレジーム。金利環境、インフレ環境、通貨体制の変化で過去のパターンが完全に崩壊する可能性
- 中央銀行の政策レジーム（量的緩和 vs 引き締め）
- グローバルな資本移動のパターン

#### 典型的 critical_assumptions
- マクロ指標とアセットリターンの関係が構造的（経済理論に基づく）であり、偶然の相関ではない
- マクロ指標の速報値が十分な精度を持つ（改定による大幅な変更がリターン予測を無効化しない）
- 過去の政策レジームでのパターンが、現在のレジームにも適用可能

#### comparable_known_approaches
- Business Cycle Investing（景気循環投資）
- Risk Parity のマクロバリアント
- Tactical Asset Allocation 研究
- イールドカーブベースのシグナル研究

---

### Archetype: ML_SIGNAL — 機械学習シグナル

#### 説明
機械学習モデルを使って市場の予測シグナルを生成する戦略。特徴量設計、モデル選択、ハイパーパラメータチューニングを含む。

#### testable_claims 分解パターン

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L1 | 「[特徴量セット]が[ターゲット変数]に対し、サンプル内で線形モデルを上回る予測力を持つ」 | 「MLモデルのサンプル内R² or AUCが線形モデルと統計的に差がない」 |
| L1 | 「モデルの予測力が特定の少数特徴量に過度に依存していない」 | 「上位3特徴量のSHAP寄与度 > 全体の80%」 |
| L2 | 「モデルの予測力がウォークフォワードテストで安定して維持される」 | 「ウォークフォワード期間のうち50%以上で、ランダム予測を下回る」 |
| L2 | 「モデルが線形モデル（baseline）に対し、取引シグナルの質の観点で有意に優れる」 | 「MLシグナルに基づくポートフォリオのSharpeが線形モデルベースと統計的に差がない」 |
| L3 | 「モデルの再学習頻度と計算コストが実務的に持続可能」 | 「再学習に要する時間が、学習データの更新頻度を超える」 |
| L3 | 「モデルの出力するシグナルの回転率が、取引コスト控除後の収益を残す」 | 「MLシグナルのターンオーバーが線形モデルの3倍以上かつコスト控除後リターンが逆転」 |

#### 典型的 regime_dependencies
- データ分布の非定常性（学習期間と予測期間でデータ分布が変化する）
- 市場マイクロ構造の変化（HFTの普及等によるシグナルの劣化）
- 特徴量の情報陳腐化速度

#### 典型的 critical_assumptions
- 特徴量に含まれる情報が将来のリターンに予測力を持ち、その予測力は学習期間のアーティファクトではない
- 過学習が適切に制御されている（正則化、交差検証、アンサンブル等）
- モデルのブラックボックス性が、戦略の運用・監視を妨げない

**ML_SIGNAL の特殊ルール**: このアーキタイプでは、L1 の claim に「線形モデルを上回る」を**必須で含める**。ML を使う正当化として、シンプルなモデルでは捉えられない関係が存在することを示す責務がある。Audit Rubric CMP-01（不要な複雑性）と直結。

#### comparable_known_approaches
- Gu, Kelly, Xiu (2020) "Empirical Asset Pricing via Machine Learning"
- 各種 Kaggle 金融コンペの知見
- ファクター投資との比較研究

---

### Archetype: ALT_DATA — オルタナティブデータ活用

#### 説明
非伝統的データ（衛星画像、Webトラフィック、クレジットカード決済等）を投資シグナルに変換する戦略。

#### testable_claims 分解パターン

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L1 | 「[オルタナティブデータ]が[ターゲット変数（例: 売上、業績、株価）]に対し、伝統的データでは得られない追加的な情報を持つ」 | 「オルタナティブデータの追加で、伝統的データのみのモデルのR²が統計的に改善しない」 |
| L1 | 「オルタナティブデータの歴史が、統計的推論に十分な期間ある」 | 「利用可能なデータ期間 < 3年、かつサンプルサイズ < 100」 |
| L2 | 「追加情報の優位性がデータの広範な利用後も持続する（情報の希少性プレミアム）」 | 「データの利用者数増加後に、予測力が統計的に有意に低下」 |
| L2 | 「データの品質（backfill、カバレッジ変動、方法論変更）を考慮した後も有意性が残る」 | 「backfill 期間を除外した場合、予測力が消失」 |
| L3 | 「データ取得コスト + 処理コストが、データによる追加リターンを下回る」 | 「年間データコスト > データに基づくシグナルの超過リターン × 運用額」 |

#### 典型的 regime_dependencies
- データの情報優位性の持続期間（他の市場参加者が同一データを使い始めるまでの期間）
- データの季節性（衛星画像の天候依存、小売データの季節調整等）
- データベンダーの事業継続性

#### 典型的 critical_assumptions
- データが表面上示す関係が因果的（または少なくとも安定的に先行する）であり、偶然の相関ではない
- データのbackfillが存在しないか、backfill期間が明確に除外されている
- データの処理パイプラインが再現可能

#### comparable_known_approaches
- 衛星データと小売売上予測の実証研究
- Webトラフィックと企業業績予測
- クレジットカードデータの投資応用事例

---

### Archetype: HYBRID — 複合型

primary アーキタイプ + secondary アーキタイプの組合せ。testable_claims は各アーキタイプの claims を結合し、追加で以下の claims を含める:

| Layer | Claim Template | Falsification Condition Template |
|-------|---------------|--------------------------------|
| L2-追加 | 「[primary]と[secondary]の組合せが、個別使用に対して有意に改善する」 | 「組合せシグナルのSharpeが、個別シグナルの最良と統計的に差がない」 |
| L3-追加 | 「組合せの複雑性増加に見合う改善がある（複雑性あたりの改善量）」 | 「情報比率の改善が、パラメータ数の増加に比例しない」 |

---

### Archetype: UNCLASSIFIED — 未分類

アーキタイプが判定できない場合。

処理:
1. ユーザーに Follow-up:「あなたのアプローチは以下のどれに近いですか？」と6アーキタイプを提示
2. ユーザーが選択 → 該当アーキタイプのパターンを適用
3. ユーザーが「どれにも当てはまらない」→ 汎用の testable_claims テンプレートを使用:

| Layer | Claim Template |
|-------|---------------|
| L1 | 「提案するアプローチが対象市場で統計的に有意な超過リターンを生む」 |
| L2 | 「その有意性がサンプル外で再現する」 |
| L3 | 「実務的制約を考慮した後もリターンが残る」 |

汎用テンプレートは粒度が粗いため、downstream での Evidence Planning と Validation Planning の精度が下がる。Recommendation の confidence_label が下がる要因として `open_uncertainties` に記録。

---

## 4. パターンごとの変換例（追加）

### 例: EVENT アーキタイプ

**UserIntent**:
```
raw_goal: "決算発表前後の株価の動きで利益を出せるか調べたい"
success_definition: "年間リターン10%以上 / 勝率60%以上 / 3年"
risk_preference: medium
must_not_do: ["no_short_selling"]
```

**DomainFrame**:
```json
{
  "reframed_problem": "日本株市場（仮定）において決算発表後の株価ドリフト（PEAD）が、ロングオンリー制約のもとで、年間リターン10%以上かつ勝率60%以上を3年以上にわたり達成できるか",
  "core_hypothesis": "決算発表後の株価には系統的なドリフトが存在し、ロングポジションのみでも収益機会として活用可能である",
  "testable_claims": [
    {
      "claim_id": "TC-01",
      "claim": "日本株市場の決算発表後5営業日の累積超過リターン(CAR)が、全サンプルで統計的に有意にゼロと異なる",
      "falsification_condition": "CARのt値 < 2.0（イベントスタディのブートストラップ検定でp > 0.05）"
    },
    {
      "claim_id": "TC-02",
      "claim": "決算サプライズ（実績 - コンセンサス予想）の符号がCARの方向を予測する力を持つ",
      "falsification_condition": "ポジティブサプライズ群とネガティブサプライズ群のCAR差のt値 < 2.0"
    },
    {
      "claim_id": "TC-03",
      "claim": "ポジティブサプライズ銘柄のロングポートフォリオ（空売り制約付き）が、サンプル外でも年率10%以上のリターンを達成する",
      "falsification_condition": "サンプル外の年率リターン < 10%が3年中2年以上"
    },
    {
      "claim_id": "TC-04",
      "claim": "決算発表翌営業日の寄付で買い付ける現実的な執行タイミングでもCARの大部分を捕捉可能",
      "falsification_condition": "T+1寄付執行ベースのCARが、T+0終値ベースのCARの50%未満"
    },
    {
      "claim_id": "TC-05",
      "claim": "取引コスト（片道20bps想定）と流動性制約を考慮した後もリターンが残る",
      "falsification_condition": "コスト控除後の年率リターン < 5%（成功基準10%の半分）"
    }
  ],
  "critical_assumptions": [
    "決算発表日が正確に記録されており、point-in-timeで利用可能",
    "コンセンサス予想データがpoint-in-timeで利用可能（予想の修正履歴を含む）",
    "決算発表後のドリフトがアナリストカバレッジの薄い中小型株で特に顕著であるという先行研究に依拠するが、流動性との背反がある"
  ],
  "regime_dependencies": [
    "市場全体のセンチメント: 悲観的な市場ではポジティブサプライズへの反応が鈍化する可能性",
    "決算シーズンの集中度: 日本市場は3月期決算に集中しており、イベント密度が季節的に偏る",
    "ボラティリティ環境: 高ボラ期にはイベント効果がノイズに埋もれる可能性"
  ],
  "comparable_known_approaches": [
    {
      "name": "Post-Earnings Announcement Drift (PEAD)",
      "relevance": "同一現象の学術的検証。米国市場で広範に研究されている",
      "known_outcome": "米国市場では統計的に有意だが、近年では効果の縮小が報告されている"
    },
    {
      "name": "日本市場のPEAD研究（Hou et al.等）",
      "relevance": "日本市場での直接的な先行研究",
      "known_outcome": "存在は確認されているが、米国ほど大きくないとの報告"
    }
  ]
}
```

---

## 5. 曖昧な goal を framing できない場合の扱い

### Framing 不能のパターンと対応

| パターン | 例 | 対応 | 結果 |
|---------|---|------|------|
| 対象市場が特定できない | 「何かいい戦略を教えて」 | Follow-up:「どの市場に興味がありますか？（日本株、米国株、FX、コモディティ等）」 | 回答があれば続行。なければ仮に「日本株」と置き、open_uncertainties に記録 |
| 戦略アプローチが特定できない | 「株で儲ける方法を知りたい」 | Follow-up:「以下のアプローチのうち、興味があるものはありますか？」+ 6アーキタイプの平易な説明を提示 | 選択があれば該当アーキタイプ適用。選択なしなら UNCLASSIFIED 汎用テンプレート |
| 検証ではなく情報取得が目的 | 「日本株の現状を教えて」 | 「Give Me a DAY は投資戦略の検証を支援するサービスです。特定の戦略アイデアや仮説をお持ちでしたら、その検証をお手伝いできます」| 戦略意図がなければ Step 2 不成立。Goal Intake に差し戻し |
| 複数のゴールが混在 | 「バリューもモメンタムもやりたいし、マクロも見たい」 | 「それぞれ検証の方向が異なります。以下から1つ選んで先に進めませんか？ 残りは別の検討として扱えます」| 1 run = 1 primary archetype を強制 |
| 非現実的なゴール | 「確実に年率100%のシステム」 | 「年率100%の安定的なリターンは、過去に持続的に達成された例が極めて少なく、検証の前提として非現実的です。成功基準を調整できますか？」| success_definition の修正を求める。修正しない場合、そのまま進行するが open_uncertainties に「成功基準が非現実的である可能性」を追加。Audit で RCR-01 (過信誘発) が fire する |

### Framing Follow-up の予算

Domain Framing 固有の Follow-up は**最大2往復**。Goal Intake で3往復を消費している場合、Domain Framing で追加2往復、合計5往復が上限。これ以上は離脱リスクが高すぎる。

2往復で解決しない場合:
- UNCLASSIFIED アーキタイプの汎用テンプレートを適用
- open_uncertainties に「戦略アプローチが特定できていない。汎用テンプレートを使用」を追加
- Recommendation の confidence_label が低下する要因として記録

---

## 6. Downstream 接続の詳細

### DomainFrame → ResearchSpec

| DomainFrame Field | ResearchSpec Field | 変換ロジック |
|-------------------|-------------------|------------|
| `reframed_problem` | `problem_frame` | そのまま継承 |
| `core_hypothesis` | `primary_objective` | 仮説を目的文に変換:「{core_hypothesis} を検証すること」|
| `testable_claims` | `validation_requirements.must_test` | 各 claim を検証項目に変換 |
| `testable_claims[].falsification_condition` | `validation_requirements.disqualifying_failures` | falsification_condition をメトリクス + 閾値に分解 |
| `critical_assumptions` | `assumption_space` | カテゴリ・falsification_condition を付加して構造化 |
| `regime_dependencies` | `validation_requirements.must_test` に regime_split を追加 | 各依存レジームでの分離テストを要求 |
| `comparable_known_approaches` | Candidate Generation の参考情報 | baseline 候補の設計材料 |

### DomainFrame → EvidencePlan

| DomainFrame Field | EvidencePlan への影響 |
|-------------------|---------------------|
| `testable_claims` | 各 claim の検証に必要なデータカテゴリ（Evidence Taxonomy）を決定 |
| `critical_assumptions` | 前提の検証に必要な追加データを required_data に追加 |
| `regime_dependencies` | レジーム判定用データ（VIX、金利等）を required_data に追加 |
| `comparable_known_approaches` | ベンチマークデータの必要性を判定 |

### DomainFrame → ValidationPlan

| DomainFrame Field | ValidationPlan への影響 |
|-------------------|----------------------|
| `testable_claims` (Layer 1) | offline_backtest + out_of_sample テストの設計 |
| `testable_claims` (Layer 2) | walk_forward + regime_split テストの設計 |
| `testable_claims` (Layer 3) | sensitivity（コスト感度）+ stress_test の設計 |
| `regime_dependencies` | regime_split テストのレジーム区分を決定 |

### DomainFrame → Audit

| DomainFrame Field | Audit への影響 |
|-------------------|--------------|
| `critical_assumptions` | ASM-01〜07 の走査対象。各 assumption が Audit で検査される |
| `regime_dependencies` | RGM-01〜05 の走査対象。依存レジームの検証有無を確認 |
| `comparable_known_approaches` | 既知手法の失敗パターンとの照合。known_outcome が「失敗」なら追加警告 |
| `testable_claims[].falsification_condition` | Validation Plan の failure_conditions と整合性チェック |

---

## 7. v1 で最低限必要なドメイン知識ベース

Domain Framing が機能するには、投資リサーチドメインの知識ベースが必要。v1 で最低限必要な範囲:

### アーキタイプ知識

| 知識カテゴリ | v1 の範囲 | 深さ |
|------------|----------|------|
| FACTOR | バリュー、モメンタム、クオリティ、サイズ、低ボラの5大ファクター。日本株・米国株 | ファクター定義（代表的な計算方法）、学術的な有意性の概要、典型的な問題点 |
| STAT_ARB | ペアトレード、共和分ベースのスプレッド取引 | 共和分検定の概要、半減期の概念、典型的な崩壊パターン |
| EVENT | 決算発表ドリフト(PEAD)、M&Aアービトラージ、自社株買い効果 | イベントスタディの方法論概要、主要な先行研究の結論 |
| MACRO | 景気循環投資、セクターローテーション、イールドカーブシグナル | 主要マクロ指標（GDP、金利、PMI等）とアセットリターンの関係の概要 |
| ML_SIGNAL | 特徴量ベースのリターン予測、過学習リスク | ML投資応用の主要論文の結論、線形モデルとの比較結果 |
| ALT_DATA | 衛星データ、Webデータ、クレジットカードデータの投資応用 | 各データ種別の概要、backfill問題、情報の陳腐化 |

### 市場知識

| 市場 | v1 の範囲 |
|------|----------|
| 日本株 | TOPIX/日経225、東証の市場区分、決算月（3月期集中）、取引時間、呼値、信用取引の仕組み、主要なデータソース |
| 米国株 | S&P500/Russell、セクター分類(GICS)、決算スケジュール、取引時間、主要なデータソース |
| FX | 主要通貨ペア、スワップ、レバレッジの概念。戦略検証の基礎 |
| その他 | コモディティ、債券、暗号資産は基礎的な概念のみ。詳細な知識ベースは v1.5 |

### 検証方法論知識

| 方法論 | v1 の範囲 |
|--------|----------|
| バックテスト | 基本的なバックテスト設計、look-ahead bias の回避、取引コストモデル |
| 統計的検定 | t検定、ブートストラップ、多重検定補正の概要 |
| 時系列分析 | 定常性検定(ADF)、共和分検定(Engle-Granger)、半減期推定の概要 |
| イベントスタディ | CAR計算、超過リターンのベンチマーク設定 |
| 機械学習検証 | ウォークフォワード、交差検証（時系列対応）、過学習診断指標 |

### 知識ベースの形式

v1 では知識ベースは**プロンプト内の構造化テキスト**として保持する。外部データベースや検索エンジンは v1.5。

知識ベースの各項目は以下の構造:
```
{
  "topic": "string",
  "archetype": "FACTOR | STAT_ARB | EVENT | MACRO | ML_SIGNAL | ALT_DATA",
  "key_facts": ["string"],
  "typical_pitfalls": ["string"],
  "seminal_references": ["string"],
  "relevance_to_claims": "string"
}
```

---

## 8. v1 では扱わない高度な framing

| 高度な framing | 理由 | 導入予定 |
|---------------|------|---------|
| クロスアセット戦略の framing | 複数資産クラス間の関係性の知識が必要。v1 は単一戦略スコープ | v2 |
| ポートフォリオ構築レベルの framing | 「戦略の検証」と「ポートフォリオの最適化」は別問題 | v2 |
| マーケットマイクロ構造に基づく framing | ティックレベルの分析。v1 の粒度を超える | v2 |
| オプション戦略の framing | ギリシャ文字、ボラティリティサーフェス等の専門知識が必要 | v1.5 |
| ESG / サステナビリティ投資の framing | 独自の評価軸と知識体系が必要 | v1.5 |
| リアルタイムトレーディング戦略の framing | 執行遅延、マーケットインパクトの詳細モデリングが必要 | v1.5 |
| 学術論文の自動レビューに基づく framing | 論文検索・要約システムとの統合が必要 | v1.5 |
| 複数戦略の組合せ最適化の framing | 戦略間相関、リスクバジェッティングの知識が必要 | v2 |
| 規制制約を考慮した framing | 法的助言の領域に近づく | 含めない |

---

## 9. 実装に必要な最小構造

### モジュール構成

```
DomainFramingModule
├── ArchetypeClassifier
│   ├── keyword_patterns: dict[archetype_id → keyword_list]
│   ├── context_rules: dict[archetype_id → context_conditions]
│   └── classify(raw_goal, user_goal_summary) → archetype_id
│
├── ProblemReframer
│   ├── reframe_template: string
│   └── reframe(user_goal_summary, archetype, success_definition, must_not_do) → reframed_problem
│
├── ClaimDecomposer
│   ├── claim_patterns: dict[archetype_id → claim_template_list]
│   ├── generic_claims: claim_template_list  (for UNCLASSIFIED)
│   └── decompose(reframed_problem, archetype, success_definition) → testable_claims[]
│
├── RegimeExtractor
│   ├── archetype_regimes: dict[archetype_id → default_regime_list]
│   ├── goal_regime_signals: pattern_list
│   └── extract(archetype, raw_goal, risk_preference) → regime_dependencies[]
│
├── ApproachMatcher
│   ├── knowledge_base: dict[archetype_id → known_approach_list]
│   └── match(archetype, reframed_problem) → comparable_known_approaches[]
│
├── AssumptionExtractor
│   ├── archetype_assumptions: dict[archetype_id → default_assumption_list]
│   └── extract(archetype, reframed_problem, open_uncertainties) → critical_assumptions[]
│
└── FrameValidator
    ├── validate_completeness(domain_frame) → validation_result
    └── validate_falsifiability(testable_claims) → validation_result
```

### FrameValidator の検証ルール

| ルール ID | チェック | 失敗時の処理 |
|----------|-------|------------|
| FV-01 | `reframed_problem` が非空かつ「〜か」の疑問形式 | 再生成 |
| FV-02 | `testable_claims` が3件以上（Layer 1 ≥ 1, Layer 2 ≥ 1, Layer 3 ≥ 1） | 不足 Layer の claim を追加生成 |
| FV-03 | 全 `testable_claims` に `falsification_condition` が存在 | falsification_condition なしの claim を棄却 |
| FV-04 | `regime_dependencies` が1件以上 | デフォルトレジーム（市場トレンド + ボラティリティ）を強制追加 |
| FV-05 | `critical_assumptions` が1件以上 | アーキタイプデフォルト前提を追加 |
| FV-06 | `comparable_known_approaches` が1件以上（UNCLASSIFIED を除く） | 知識ベースから最も近い approach を追加 |
| FV-07 | `falsification_condition` が定量的（数値閾値を含む） | 定性的な条件を定量化するよう再生成 |

### ユーザー確認チェックポイント

DomainFrame 生成後、Step 3 に進む前にユーザー確認を実施。

**確認画面テンプレート**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
検証する問題の確認
━━━━━━━━━━━━━━━━━━━━━━━━━━

あなたのゴール:
「{UserIntent.raw_goal}」

これを検証問題に変換すると:
「{reframed_problem}」

核心の仮説:
「{core_hypothesis}」

検証すべきポイント:
1. {testable_claims[0].claim}
2. {testable_claims[1].claim}
3. ...

この分析が前提としていること:
- {critical_assumptions[0]}
- ...

前提としている市場環境:
- {regime_dependencies[0]}
- ...

似たアプローチの過去の結果:
- {comparable_known_approaches[0].name}: {comparable_known_approaches[0].known_outcome}

━━━━━━━━━━━━━━━━━━━━━━━━━━
この理解で合っていますか？  [はい、進める]  [修正する]
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

「修正する」の場合:
- ユーザーが修正したい箇所を自然言語で指示
- DomainFrame を部分更新（全体再生成はしない）
- 修正は1回まで。2回目の修正希望には「この後の分析で調整可能です」と提案

### DomainFrame Object の完成条件

| 条件 | 要件 |
|------|------|
| reframed_problem | 非空。疑問形式。対象市場・アプローチ・制約・成功指標を含む |
| core_hypothesis | 非空。1文 |
| testable_claims | ≥ 3件。Layer 1/2/3 各1件以上。全件に falsification_condition |
| critical_assumptions | ≥ 1件 |
| regime_dependencies | ≥ 1件 |
| comparable_known_approaches | ≥ 1件（UNCLASSIFIED を除く） |
| ユーザー確認 | 「はい、進める」を取得 |

全条件を満たした場合のみ Step 3 (Research Spec Compilation) に進む。
