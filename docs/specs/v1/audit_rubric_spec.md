# Give Me a DAY v1 — Audit Rubric Specification

**Document type**: Internal system specification
**Domain**: Investment research / Strategy validation / Hypothesis-testing pipelines
**Version**: v1 draft
**Status**: Design phase — pre-implementation
**Upstream dependencies**: v1_core_loop_spec.md, v1_output_package_spec.md, internal_schema.md (Audit Object)

---

## 1. Audit Rubric の目的

Audit Rubric は「候補をどう批判するか」のルールブックである。

Give Me a DAY のプロダクト価値は推奨の生成ではなく、**弱い候補の棄却**にある。棄却の品質は Audit の品質に等しい。Audit が甘ければ全候補が通過し、プロダクトは「何でも推奨するエンジン」に堕落する。Audit が恣意的であれば棄却理由が不透明になり、ユーザーの信頼を失う。

Rubric の責務は3つ:

1. **検出**: 候補に内在する問題を、カテゴリ別のパターンマッチングで発見する
2. **判定**: 発見した問題の深刻度を、再現可能な基準で評価する
3. **棄却決定**: どの問題が候補を disqualify するかを、機械的に決定する

Rubric は「研究委員会の審査基準」であり、「チャットボットの感想」ではない。

---

## 2. 批判カテゴリ一覧

v1 では10カテゴリを使用する。各カテゴリは投資リサーチ／戦略検証ドメインの典型的な失敗パターンに対応する。

| # | Category ID | Category Name | 一言定義 |
|---|------------|---------------|---------|
| 1 | `assumption` | 前提の脆弱性 | 根拠が弱い、未検証、または暗黙の前提 |
| 2 | `evidence_gap` | 証拠の欠落 | 検証に必要な証拠が不足・入手不可 |
| 3 | `leakage_risk` | データリーケージ | 未来情報の混入、生存者バイアス、データスヌーピング |
| 4 | `overfitting_risk` | 過学習リスク | パラメータ過多、サンプル不足、最適化の罠 |
| 5 | `realism` | 実務的非現実性 | 取引コスト・流動性・スリッページ等の実務条件の無視 |
| 6 | `regime_dependency` | レジーム依存 | 特定の市場環境でのみ機能する戦略 |
| 7 | `complexity` | 過剰複雑性 | 検証・実装・運用・保守の複雑さが妥当性を超過 |
| 8 | `observability` | 監視不能性 | 稼働中のシステム健全性を監視できない |
| 9 | `cost_assumption` | コスト仮定の甘さ | データ・インフラ・取引コストの過小評価 |
| 10 | `recommendation_risk` | 推奨リスク | この候補を推奨した場合に発生するメタリスク |

---

## 3–7. カテゴリ別詳細仕様

---

### Category 1: `assumption` — 前提の脆弱性

#### Why it matters
投資戦略の候補は必ず複数の前提に依存する。前提が明示されていなければ検証できず、前提が弱ければ戦略は見かけ上の堅牢さしか持たない。投資リサーチにおける最も頻繁な失敗は「暗黙の前提の崩壊」である。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| ASM-01 | 暗黙の市場効率性仮定 | 候補が市場の非効率性を前提としているが、その非効率性の根拠・持続性を明示していない | 「モメンタムは機能する」と仮定するが、なぜ裁定されないかの説明がない |
| ASM-02 | 定常性の暗黙仮定 | 過去のパターンが将来も継続すると暗黙に仮定。レジーム変化への言及がない | 過去10年のバックテスト結果を将来にそのまま外挿 |
| ASM-03 | 流動性の暗黙仮定 | 必要な取引量が市場で吸収可能であることを検証せずに仮定 | 小型株戦略で日次出来高の制約を考慮していない |
| ASM-04 | データ品質の暗黙仮定 | 使用データにバイアスがない、あるいはクリーンであることを無条件に仮定 | 無料データソースの欠損値・遅延・修正を考慮していない |
| ASM-05 | 因果関係の誤認 | 相関関係を因果関係として扱っている | ファクターXとリターンの相関を「Xがリターンをdriveしている」と断定 |
| ASM-06 | 単一データソース依存 | 核心的な前提が1つのデータソースにのみ依拠 | 戦略の有効性がBloombergの1フィールドにのみ基づく |
| ASM-07 | 学術結果の無批判な援用 | 論文の結果を、市場条件・コスト構造の違いを考慮せずそのまま採用 | 「Fama-Frenchファクターは有意」を日本市場にそのまま適用 |

#### Severity logic

| 条件 | Severity |
|------|----------|
| 前提が明示されておらず、かつ候補の核心ロジックに直結 | critical |
| 前提が明示されているが、検証方法が示されていない | high |
| 前提が明示され検証方法もあるが、検証がまだ実行されていない | medium |
| 前提が明示され、部分的に検証済みだが、完全ではない | low |

#### Disqualifying logic
- ASM-01 または ASM-02 が severity: critical の場合 → `disqualifying: true`
- severity: critical かつ mitigation なし → `disqualifying: true`
- ASM-05（因果関係の誤認）が候補の中核ロジックに関わる場合 → `disqualifying: true`

#### Mitigation guidance
- 暗黙の前提を明示化し、Research Spec の assumption_space に追加
- 各前提に falsification condition（反証条件）を付記
- 学術結果の援用時は、対象市場・期間・コスト条件の差異を明記
- 単一データソース依存は、代替ソースによるクロスバリデーションを計画に追加

#### v1 implementation notes
- ASM-01〜07 のパターンは固定。追加は v1.5。
- 検出は候補の `core_assumptions` フィールドと Research Spec の `assumption_space` を突合して行う。
- 「暗黙」の検出ロジック: 候補の architecture_outline に含まれる概念（例: 「モメンタムシグナル」）に対し、対応する assumption が core_assumptions に存在しない場合に ASM-01/02 を flag。
- 暗黙前提のチェックリスト（v1 固定）: 市場効率性、定常性、流動性、データ品質、因果関係、単一ソース依存、学術結果の適用可能性。

---

### Category 2: `evidence_gap` — 証拠の欠落

#### Why it matters
候補がどれほど論理的に見えても、検証に必要な証拠が不足していれば検証計画は空虚になる。証拠の欠落は「わからない」ではなく「検証できない」を意味し、推奨の信頼性を根底から損なう。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| EVD-01 | 必須証拠の未入手 | Evidence Plan で required かつ availability: unavailable | バックテストに必要なティックデータが存在しない |
| EVD-02 | 証拠の時間的不足 | temporal_coverage が Validation Plan の要求期間をカバーしない | 5年のバックテスト計画に対し3年分のデータしかない |
| EVD-03 | 代替データの品質劣化 | proxy_data_used の quality_loss_estimate が「重大」 | 個別銘柄出来高の proxy としてセクター出来高を使用 |
| EVD-04 | バイアス未検証のデータ | evidence_item に known_biases があり、bias の影響度が未評価 | survivorship bias が存在するが、その影響を定量評価していない |
| EVD-05 | サンプル外データの欠如 | out_of_sample テスト用のデータが確保されていない | 全データをin-sample に使い切り、検証用データが残っていない |
| EVD-06 | 比較基準の証拠不足 | baseline 候補やベンチマークとの比較に必要なデータが不足 | 候補のパフォーマンスは計算可能だが、ベンチマークの同期間データがない |

#### Severity logic

| 条件 | Severity |
|------|----------|
| required かつ unavailable。proxy も不可 | critical |
| required かつ unavailable だが proxy が存在（quality_loss: 重大） | high |
| required かつ obtainable_with_effort。合理的な期間内に取得可能 | medium |
| optional データの欠如 | low |
| EVD-05（サンプル外欠如）→ overfitting_risk を伴うため常に | high 以上 |

#### Disqualifying logic
- EVD-01 が1件以上かつ proxy 不可 → `disqualifying: true`
- EVD-05 かつ候補の validation_burden が high → `disqualifying: true`
- EVD-02 で temporal_coverage が要求の50%未満 → `disqualifying: true`

#### Mitigation guidance
- EVD-01: 代替データソースの調査、または候補のスコープ縮小（データが存在する市場・期間に限定）
- EVD-02: バックテスト期間の短縮。ただし短縮が統計的有意性を損なう場合は warning 追加
- EVD-03: proxy 使用時の感度分析を Validation Plan に追加
- EVD-04: バイアスの影響度定量化テストを Validation Plan に追加
- EVD-05: データ分割の再設計。最低でも30%をサンプル外に確保

#### v1 implementation notes
- Evidence Plan の `gap_severity` と直接連動。gap_severity: blocking は EVD-01 に自動マッピング。
- EVD-04 の検出は Evidence Plan の `known_biases` フィールドを走査。known_biases が非空かつ対応する Validation Plan に bias 影響度テストがない場合に flag。
- EVD-05 の検出は Validation Plan の test_sequence に out_of_sample テストが存在するかを確認し、対応するデータが Evidence Plan に確保されているかを照合。

---

### Category 3: `leakage_risk` — データリーケージ

#### Why it matters
データリーケージは投資リサーチにおける最も深刻な技術的失敗。バックテスト結果を劇的に歪め、実運用で再現不可能なパフォーマンスを生む。リーケージが存在する候補は、見かけ上どれほど優秀でも信頼に値しない。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| LKG-01 | Look-ahead bias | シグナル生成時点で利用不可能な情報を使用 | 当日の終値を使って当日の売買シグナルを生成 |
| LKG-02 | Survivorship bias | 分析対象が生存銘柄のみで構成 | 上場廃止銘柄を含まないユニバースでバックテスト |
| LKG-03 | Data snooping | 同一データセットで仮説生成と仮説検証を実施 | データを見てパターンを発見し、同じデータで「発見」を確認 |
| LKG-04 | Publication bias の援用 | 有意な結果のみ報告された研究に基づく戦略設計 | メタ分析なしで単一論文の有意な結果を戦略の根拠にする |
| LKG-05 | Backfill bias | データベンダーが事後的に追加・修正したデータを使用 | ヘッジファンドDBの過去リターンに後から追加された良好な成績 |
| LKG-06 | 報告ラグの無視 | 財務データの公表タイミングと利用タイミングの不整合 | 3月期決算データを4月1日から利用可能と仮定（実際は6月公表） |
| LKG-07 | ポイントインタイム違反 | 分析時点で実際に利用可能だったデータバージョンを使用していない | 改訂後のGDPデータを初回発表時点で利用可能だったかのように扱う |

#### Severity logic

| 条件 | Severity |
|------|----------|
| LKG-01〜03 のいずれか。候補の核心ロジックに関わる | critical |
| LKG-01〜03 のいずれか。核心ではないが結果に影響しうる | high |
| LKG-04〜07 のいずれか。影響度が定量評価されていない | high |
| LKG-04〜07 のいずれか。影響度が定量評価済みで軽微 | medium |
| リーケージの可能性があるが、Validation Plan にリーケージ検出テストが含まれている | medium（テスト結果待ち） |

#### Disqualifying logic
- LKG-01（look-ahead bias）が候補のシグナル生成ロジックに存在 → `disqualifying: true`
- LKG-02（survivorship bias）が候補のユニバース構築に存在し、修正不可 → `disqualifying: true`
- LKG-03（data snooping）が候補の仮説検証プロセス全体に該当 → `disqualifying: true`
- 上記以外でも severity: critical かつ mitigation なし → `disqualifying: true`

#### Mitigation guidance
- LKG-01: データのタイムスタンプを厳密に管理。「各データポイントは、いつから利用可能だったか」を Evidence Plan に明記
- LKG-02: point-in-time ユニバースの構築。上場廃止・合併・分割を反映
- LKG-03: 仮説生成データと検証データの明確な分離。サンプル分割の事前定義
- LKG-05: データベンダーの backfill ポリシーを確認。backfill なしの期間のみ使用
- LKG-06/07: データの公表スケジュールを Evidence Plan に記録。point-in-time データベースの使用を推奨

#### v1 implementation notes
- leakage_risk は Audit の中で最も機械的に検出可能なカテゴリ。
- 検出ロジック: Candidate の architecture_outline 内の「データ使用時点」と Evidence Plan の temporal_coverage / known_biases を照合。
- LKG-01 の検出: シグナル生成ステップで使用するデータの availability_timestamp と、シグナル生成タイミングを比較。availability_timestamp ≥ signal_timestamp なら flag。
- LKG-02 の検出: Evidence Plan のデータに survivorship bias が known_biases として記録されているか確認。記録なしの場合も、ユニバースデータの種別（指数構成銘柄 etc.）から推定 flag。
- **Leakage は投資ドメインで最も致命的な問題類型。このカテゴリの検出精度はプロダクト品質の最重要指標。**

---

### Category 4: `overfitting_risk` — 過学習リスク

#### Why it matters
パラメータチューニングの結果としての好成績は、将来のパフォーマンスを予測しない。過学習はバックテスト上の成功と実運用の失敗の最大の乖離要因。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| OVF-01 | パラメータ過多 | 自由度（パラメータ数）がサンプルサイズに対して過大 | 20個のパラメータを100データポイントで最適化 |
| OVF-02 | 最適化期間の恣意性 | バックテスト期間が結果が良い期間に恣意的に限定 | 「2015-2020年は有効」だが2020-2023年を含めると崩壊 |
| OVF-03 | 多重検定未補正 | 多数の戦略バリアントをテストし、最良のものだけ採用 | 200個のパラメータ組合せから最良を選び、統計的有意と報告 |
| OVF-04 | モデル複雑度の正当化欠如 | 複雑なモデルがシンプルなモデルより有意に優れるか未検証 | ディープラーニングモデルを使うが、線形モデルとの比較がない |
| OVF-05 | 交差検証の未実施 | 時系列交差検証（walk-forward等）が計画されていない | 単一の train/test 分割のみ |
| OVF-06 | 情報比率の過信 | サンプル内 Sharpe/IR が非現実的に高い | バックテスト Sharpe > 3.0（実運用での持続性が極めて疑わしい） |

#### Severity logic

| 条件 | Severity |
|------|----------|
| OVF-01 でパラメータ数 / サンプルサイズ > 0.1 | critical |
| OVF-01 でパラメータ数 / サンプルサイズ 0.05–0.1 | high |
| OVF-03 で検定数 > 20 かつ多重検定補正なし | critical |
| OVF-02 で期間選択の根拠が明示されていない | high |
| OVF-04 で baseline（シンプルモデル）との比較がない | high |
| OVF-05 で walk-forward が計画されていない | high |
| OVF-06 でサンプル内 Sharpe > 2.0 | high（警告）、> 3.0 で critical |

#### Disqualifying logic
- OVF-01 でパラメータ数 / サンプルサイズ > 0.15 → `disqualifying: true`
- OVF-03 で検定数 > 50 かつ多重検定補正なし → `disqualifying: true`
- OVF-06 でサンプル内 Sharpe > 3.0 かつ out_of_sample 検証なし → `disqualifying: true`

#### Mitigation guidance
- OVF-01: パラメータ数の削減。正則化の導入。AIC/BIC による選択
- OVF-02: 期間選択の根拠を明記。複数期間での検証を計画に追加
- OVF-03: Bonferroni 補正、FDR 制御、または bootstrap による多重検定補正
- OVF-04: baseline モデル（線形回帰、等ウェイト等）との比較を必須化
- OVF-05: walk-forward 検証を Validation Plan に追加
- OVF-06: out_of_sample Sharpe と in_sample Sharpe の比率を確認。比率 < 0.5 は warning

#### v1 implementation notes
- OVF-01 の検出: Candidate の architecture_outline からパラメータ数を推定。Evidence Plan のサンプルサイズとの比率を算出。比率が閾値を超えたら自動 flag。
- OVF-06 の「非現実的に高い Sharpe」閾値（2.0 / 3.0）は投資実務の経験則に基づく。学術研究では Sharpe > 2.0 の戦略が実運用で持続した例は極めて稀。
- OVF-04 は Candidate Generation (Step 4) で baseline 候補を必須にした設計と連動。baseline がない場合はこの Audit パターンが常に high で fire する。

---

### Category 5: `realism` — 実務的非現実性

#### Why it matters
バックテスト上は有効でも、実運用で再現不可能な戦略は無価値。取引コスト、流動性、スリッページ、執行遅延は理論モデルと実務の最大のギャップ。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| RLM-01 | 取引コストの過小評価 | 取引コストがゼロまたは非現実的に低い値で仮定 | 手数料・スプレッド・市場インパクトを無視 |
| RLM-02 | 流動性制約の無視 | 必要な取引量が対象銘柄の日次出来高に対して過大 | 日次出来高の10%以上を取引する前提 |
| RLM-03 | スリッページの無視 | 注文が理論価格で約定する前提 | 指値価格で確実に約定すると仮定 |
| RLM-04 | 執行遅延の無視 | シグナル発生から執行までのタイムラグを考慮していない | シグナル発生と同時に約定する前提 |
| RLM-05 | ショートセリング制約の無視 | 空売りが無制限に可能と仮定 | 借株コスト・空売り規制・リコールリスクを無視 |
| RLM-06 | リバランスコストの無視 | 頻繁なリバランスのコスト累積を考慮していない | 日次リバランスのターンオーバーコストが未計算 |
| RLM-07 | 市場インパクトの無視 | 大口注文が市場価格に与える影響を未考慮 | 時価総額の小さい銘柄で大量取引 |

#### Severity logic

| 条件 | Severity |
|------|----------|
| RLM-01 で取引コストがゼロ仮定。候補の期待リターンが低い（年率 < 5%） | critical |
| RLM-01 で取引コストが過小だが候補の期待リターンが十分に高い | high |
| RLM-02 で必要取引量 > 対象銘柄平均出来高の5% | critical |
| RLM-02 で必要取引量 1-5% | high |
| RLM-03〜04 でスリッページ/遅延がリターンの10%以上を侵食しうる | critical |
| RLM-05 で戦略がロング/ショート両建て必須 | high |
| RLM-06 で年間ターンオーバー > 1200%（日次リバランス相当） | critical |

#### Disqualifying logic
- RLM-01 で取引コストゼロ仮定 + 候補の期待リターンが取引コスト控除後にマイナスの可能性が高い → `disqualifying: true`
- RLM-02 で必要取引量 > 対象銘柄平均出来高の10% → `disqualifying: true`
- RLM-06 で年間ターンオーバー > 2400% かつコスト影響未評価 → `disqualifying: true`

#### Mitigation guidance
- RLM-01: 現実的な取引コストモデルを Validation Plan に追加（片道 5-50bps のレンジで感度分析）
- RLM-02: ポジションサイズの上限を出来高ベースで制約
- RLM-04: 執行遅延を明示的にモデル化。シグナル T+0 → 執行 T+1 等
- RLM-06: ターンオーバー制約を最適化目的関数に追加

#### v1 implementation notes
- RLM-01 の検出: Candidate の architecture_outline に取引コストの明示がなければ自動 flag。Evidence Plan にコストデータがなくても flag。
- RLM-02 の検出: Evidence Plan の対象銘柄ユニバースの平均出来高と、Candidate の想定取引規模を照合。想定取引規模が未記載の場合は medium で flag（情報不足として）。
- 取引コストの「現実的な範囲」は市場・資産クラスによって異なる。v1 では日本株・米国株の代表的な値をデフォルトとして保持。

---

### Category 6: `regime_dependency` — レジーム依存

#### Why it matters
投資戦略のパフォーマンスは市場レジーム（高ボラ/低ボラ、上昇/下降トレンド、金利環境等）に強く依存する。特定レジームでのみ機能する戦略は、レジーム転換時に壊滅的な損失をもたらしうる。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| RGM-01 | 単一レジーム依存 | 候補のバックテスト期間が単一の市場レジームのみをカバー | 2010-2020の低金利・低ボラ環境のみでテスト |
| RGM-02 | レジーム転換の未考慮 | レジーム転換時の挙動が検証されていない | トレンドフォロー戦略でレンジ相場の検証がない |
| RGM-03 | 構造変化リスク | 戦略が依拠する市場構造が変化する可能性を無視 | HFT戦略で取引所のマイクロ構造変更リスクを無視 |
| RGM-04 | マクロ環境依存の未明示 | 金利・為替・インフレ等のマクロ条件への依存が明示されていない | キャリートレード戦略で金利差の縮小シナリオを検証していない |
| RGM-05 | クライシスアルファの誤認 | 平常時のパフォーマンスとクライシス時のパフォーマンスを分離評価していない | ドローダウン期間のパフォーマンスを分離していない |

#### Severity logic

| 条件 | Severity |
|------|----------|
| RGM-01 でバックテスト期間がレジーム転換を1回も含まない | critical |
| RGM-02 でレジーム転換テスト（regime_split）が Validation Plan にない | high |
| RGM-03 で構造変化が過去5年以内に実際に発生したドメイン | high |
| RGM-04 で候補がマクロ条件に明らかに依存しているが依存が明示されていない | high |
| RGM-01 でバックテスト期間が2回以上のレジーム転換を含む | low |

#### Disqualifying logic
- RGM-01 でバックテスト期間が5年未満かつレジーム転換を含まない → `disqualifying: true`
- RGM-02 かつ候補の risk_preference が very_low/low → `disqualifying: true`

#### Mitigation guidance
- RGM-01: バックテスト期間を複数レジームをカバーするよう延長。最低でも1回のレジーム転換を含む
- RGM-02: regime_split テストを Validation Plan に追加。高ボラ/低ボラ、上昇/下降、危機期間での分離評価
- RGM-04: マクロ感度分析を追加。金利 ±100bps、為替 ±10% 等のシナリオ

#### v1 implementation notes
- Domain Framing (Step 2) の regime_dependencies と照合。regime_dependencies が空の場合、Audit はこのカテゴリで最低1つの issue を必ず flag する（空の regime_dependencies は Step 2 の不備を示す）。
- レジームの定義は v1 ではシンプルな4分類: bull / bear / high_vol / low_vol。より精密なレジーム分類は v1.5。

---

### Category 7: `complexity` — 過剰複雑性

#### Why it matters
複雑なシステムは検証が困難で、障害点が多く、保守コストが高い。投資リサーチでは「シンプルなモデルが複雑なモデルに匹敵するか上回る」事例が多数報告されている。複雑性そのものがリスク。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| CMP-01 | 不要な複雑性 | baseline（シンプル版）との性能差が示されていないのに複雑なアプローチを採用 | 線形モデルで十分な可能性があるのにGBMを使用 |
| CMP-02 | コンポーネント過多 | architecture_outline のステップ数が過大 | 10段階以上のパイプライン。各段階がパラメータを持つ |
| CMP-03 | 外部依存過多 | 外部API、データベンダー、サードパーティライブラリへの依存が多い | 5つ以上の外部サービスに依存 |
| CMP-04 | 検証の組合せ爆発 | コンポーネントの組合せにより検証すべきケースが爆発 | 3つの戦略を組み合わせる場合、相互作用の検証が必要 |
| CMP-05 | 保守性の欠如 | 候補が暗黙知に依存し、設計者以外が保守困難 | パラメータの意味や選択根拠が文書化されていない |

#### Severity logic

| 条件 | Severity |
|------|----------|
| CMP-01 で baseline との比較が存在せず、validation_burden: high | high |
| CMP-02 で architecture_outline > 8ステップ | medium、> 12 で high |
| CMP-03 で外部依存 > 5 | medium、> 8 で high |
| CMP-04 で候補が3つ以上の独立コンポーネントの組合せ | high |

#### Disqualifying logic
- CMP-01 かつ OVF-04 が同時に存在（不要な複雑性 + baseline比較なし）→ 単独では disqualifying ではないが、combined severity を high に引き上げ
- 通常は disqualifying にはならない。ただし CMP-04 で検証の実行可能性が明らかにない場合 → `disqualifying: true`

#### Mitigation guidance
- CMP-01: baseline 候補との厳密な比較を Validation Plan に追加
- CMP-02: パイプラインの段階削減。または段階ごとの独立テスト
- CMP-04: 段階的検証。まず個別コンポーネント、次に組合せ

#### v1 implementation notes
- complexity の評価は定性的にならざるを得ない。v1 では architecture_outline のステップ数と外部依存数を定量指標として使用。
- baseline 候補の存在が CMP-01 の検出に必須。Step 4 で baseline 必須としたのはこのため。

---

### Category 8: `observability` — 監視不能性

#### Why it matters
稼働中のシステムが「壊れていること」に気づけなければ、パフォーマンスの劣化が放置される。投資システムでは監視の欠如が直接的な金銭的損失につながる。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| OBS-01 | パフォーマンス監視の欠如 | 稼働後のパフォーマンストラッキング方法が未定義 | リアルタイムのP&Lモニタリングがない |
| OBS-02 | 異常検知の欠如 | 想定外の挙動を検出する仕組みがない | シグナルの急変、ポジションの異常集中を検出できない |
| OBS-03 | データ品質監視の欠如 | 入力データの品質劣化を検出できない | データフィードの遅延・欠損を検出する仕組みがない |
| OBS-04 | 停止条件の未定義 | 「このシステムを止めるべき条件」が定義されていない | ドローダウンが閾値を超えた場合の自動停止ルールがない |

#### Severity logic

| 条件 | Severity |
|------|----------|
| OBS-04（停止条件未定義）かつ automation_preference が semi_automated 以上 | high |
| OBS-01 かつ候補が実運用を想定 | medium |
| OBS-02〜03 かつ候補が外部データに強く依存 | medium |
| advice_only / research_assist の場合 | low（実運用ではないため） |

#### Disqualifying logic
- 通常は disqualifying にならない。
- ただし automation_preference: full_if_safe かつ OBS-04 が存在 → `disqualifying: true`（停止条件なしの全自動運用は不可）

#### Mitigation guidance
- OBS-04: 最大ドローダウン閾値、シグナル異常検知ルール、データ品質チェックを定義
- OBS-01: key metrics のダッシュボード設計を next_steps に追加

#### v1 implementation notes
- v1 は計画段階のプロダクトのため、observability の issue は主に「計画に含まれているか」の確認。実装レベルの監視設計は v1.5。
- User Intent の automation_preference に応じて severity を調整。advice_only ならほぼ全て low。full_if_safe なら high に引き上げ。

---

### Category 9: `cost_assumption` — コスト仮定の甘さ

#### Why it matters
投資システムのコストはデータ取得・インフラ・取引の3層で発生する。これらのコスト仮定が甘いと、理論上有効な戦略が実務的に赤字になる。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| CST-01 | データコストの未計上 | 有料データの使用を前提としているがコストが未計算 | Bloomberg Terminal 年間2万ドルが未計上 |
| CST-02 | インフラコストの未計上 | 計算資源、ストレージ、通信コストが未考慮 | GPU クラスタでの ML モデル学習コスト |
| CST-03 | 取引コストの未計上 | RLM-01 と重複するが、ここではコスト総額の観点 | 年間取引コストが期待リターンの何%を占めるか未評価 |
| CST-04 | スケーリングコストの未考慮 | 運用規模拡大時のコスト増加が未検討 | 小規模では有効だが、運用額増加で市場インパクトコストが急増 |

#### Severity logic

| 条件 | Severity |
|------|----------|
| CST-03 で取引コストが期待リターンの50%以上を侵食する可能性 | critical |
| CST-01 で年間データコスト > 候補の想定利益 | high |
| CST-01〜02 でコストが未計算（金額不明） | medium |
| CST-04 で運用規模拡大の計画がない場合 | low |

#### Disqualifying logic
- CST-03 で取引コストが期待リターンを上回る蓋然性が高い → `disqualifying: true`
- 通常は disqualifying にはならないが、realism カテゴリとの複合で判定

#### Mitigation guidance
- CST-01/02: コスト明細の作成を next_steps に追加
- CST-03: 取引コスト感度分析を Validation Plan に追加
- CST-04: 運用規模ごとのコストカーブを推定

#### v1 implementation notes
- cost_assumption は realism と一部重複する。区別: realism は「取引の実現可能性」、cost_assumption は「経済的な採算性」。
- v1 では定量的なコスト計算は行わない。コストの「考慮の有無」のみを Audit で確認。

---

### Category 10: `recommendation_risk` — 推奨リスク

#### Why it matters
他の9カテゴリは候補自体の問題を検出する。このカテゴリは「この候補を推奨した場合にどのようなリスクが生じるか」を評価するメタレベルの監査。

#### Issue patterns

| Pattern ID | Pattern Name | 検出条件 | 典型例 |
|-----------|-------------|---------|--------|
| RCR-01 | 過信誘発リスク | 推奨がユーザーに過度の確信を与え、追加検証をスキップさせる恐れ | confidence: medium なのに候補の説明が「高い有効性」を示唆 |
| RCR-02 | 部分最適リスク | 候補が局所最適であり、より広い選択肢の探索を阻害する | exploratory 候補がなく、既知手法の変形のみ検討 |
| RCR-03 | 不可逆性リスク | 推奨に基づいて実行した場合、撤回が困難な行動を誘発 | 大規模なデータ契約、インフラ投資が前提条件 |
| RCR-04 | 条件見落としリスク | critical_conditions がユーザーに見落とされる構造 | 条件が多すぎる（5個以上）、または条件文が抽象的 |
| RCR-05 | 棄却候補の再浮上リスク | 棄却された候補がユーザーの心理的バイアスで復活する | 棄却理由が弱く、ユーザーが「でもこっちの方が面白い」と判断 |

#### Severity logic

| 条件 | Severity |
|------|----------|
| RCR-01 で confidence_label: low なのに候補記述が楽観的 | high |
| RCR-03 で不可逆コスト > ユーザーの stated budget の50% | high |
| RCR-04 で critical_conditions > 5 | medium |
| RCR-02 で candidate_type の多様性が不足 | medium |
| RCR-05 で棄却理由が disqualifying issue 1件のみ | medium |

#### Disqualifying logic
- 通常は disqualifying にならない。このカテゴリは候補自体の問題ではなく、推奨行為のリスクを評価するものであり、候補の棄却ではなく推奨文の conditions 追加で対応する。
- ただし RCR-01 が severity: critical（推奨が明らかに誤解を生む構造）→ 候補の disqualify ではなく、推奨文の書き換えを強制

#### Mitigation guidance
- RCR-01: confidence_explanation を強化。「これは計画段階の評価であり、実データ検証前である」を明記
- RCR-04: critical_conditions が5個を超える場合、上位3つを強調表示。残りは折りたたみ
- RCR-05: 棄却理由を3文以上に拡充（Output Package Spec の要件と連動）

#### v1 implementation notes
- recommendation_risk は他の9カテゴリの Audit 完了後に実行する最終パス。
- RCR-01 の検出: confidence_label と候補の summary / expected_strengths の語調を照合。confidence: low なのに summary に「高い」「強い」「有効な」等の強い形容詞が含まれる場合に flag。
- RCR-04 の検出: Recommendation Object の critical_conditions の件数をカウント。

---

## 8. False Confidence を防ぐための監査ルール

Audit Rubric 全体を貫く最重要原則は **false confidence の排除** である。以下のルールは全カテゴリに横断的に適用する。

### Rule FC-01: Issue 0件の候補に対するメタ検証

投資リサーチドメインで Audit issue が0件の候補は極めて非現実的。issue 0件の候補が出力された場合:
- Audit プロセス自体の品質を疑う
- 最低限、以下の3カテゴリを再走査: `assumption`, `leakage_risk`, `realism`
- 再走査後も0件の場合、`recommendation_risk` カテゴリで RCR-01（過信誘発リスク）を severity: medium で追加

### Rule FC-02: Confidence 上方修正の禁止

confidence_label は以下の機械的ルールでのみ決定される。いかなる定性的判断による上方修正も禁止。

```
confidence_label 判定ロジック:

IF any(disqualifying issue) → 候補は rejected（confidence は N/A）
IF evidence_coverage < 50% → low
IF critical issues (mitigated) ≥ 2 → low
IF high issues ≥ 3 → low
IF evidence_coverage < 80% AND high issues ≥ 1 → low
IF evidence_coverage ≥ 80% AND high issues = 0 AND critical issues = 0 → medium
IF evidence_coverage = 100% AND all issues ≤ medium AND plan_completeness = complete → medium
→ high は上記のいずれにも該当しない場合のみ（v1 ではほぼ到達不可能）
```

### Rule FC-03: 「総合的に判断」の禁止

ranking_logic に「総合的に判断した」「バランスが良い」「全体的に優れている」等の非構造化表現を含めることを禁止。各比較軸での個別判定結果を列挙する形式を強制。

### Rule FC-04: 計画段階の限界の明示

v1 は計画段階のプロダクト。以下の Warning を全 Audit 出力に付加:

> 「この Audit は計画段階の設計評価です。実データによるバックテスト・検証結果に基づく評価ではありません。実検証後に severity の変動が想定されます。」

### Rule FC-05: Surviving assumptions の強制表示

Audit を passed / passed_with_warnings で通過した候補について、`surviving_assumptions`（通過後も残存する前提）を必須出力。これが Recommendation の critical_conditions に直接マッピングされる。surviving_assumptions が空の場合、FC-01 と同様のメタ検証を実行。

### Rule FC-06: 楽観的 Sharpe の自動警告

サンプル内 Sharpe（想定または計画値）が以下の閾値を超える場合、自動的に warning を付加:

| Sharpe | 警告レベル | メッセージ |
|--------|-----------|----------|
| > 1.5 | medium | 「サンプル内 Sharpe 1.5 超は実運用での持続性に注意。取引コスト・スリッページ控除後の値を確認すること」 |
| > 2.0 | high | 「サンプル内 Sharpe 2.0 超は過学習またはリーケージの可能性を強く示唆。追加検証を要する」 |
| > 3.0 | critical | 「サンプル内 Sharpe 3.0 超は実運用で持続した事例が極めて稀。リーケージ、過学習、またはデータエラーを疑うこと」 |

---

## 9. v1 で最低限必要な Rubric

以下は v1 で実装必須のパターン。これらがなければ Audit は最低限の品質を満たさない。

### Tier 1: 必須（これなしでは出荷不可）

| Category | 必須 Pattern | 理由 |
|----------|-------------|------|
| `assumption` | ASM-01, ASM-02, ASM-04 | 暗黙前提の検出はプロダクトの最低要件 |
| `evidence_gap` | EVD-01, EVD-05 | 必須証拠の欠如とサンプル外欠如は検証の根幹 |
| `leakage_risk` | LKG-01, LKG-02, LKG-03 | 3大リーケージの検出なしに投資リサーチ Audit は成立しない |
| `overfitting_risk` | OVF-01, OVF-06 | パラメータ過多と非現実的 Sharpe は最頻出の過学習兆候 |
| `realism` | RLM-01, RLM-02 | 取引コストと流動性の無視は最も基本的な実務性チェック |
| `regime_dependency` | RGM-01 | 単一レジーム依存は最低限検出必須 |
| FC rules | FC-01, FC-02, FC-04 | false confidence 防止の最低要件 |

### Tier 2: 強く推奨（v1 に含めるべきだが、Tier 1 を優先）

| Category | Pattern | 理由 |
|----------|---------|------|
| `assumption` | ASM-03, ASM-05, ASM-07 | 流動性仮定、因果誤認、学術援用は頻出 |
| `evidence_gap` | EVD-02, EVD-04 | 時間的不足とバイアス未検証 |
| `leakage_risk` | LKG-06, LKG-07 | 報告ラグとポイントインタイム |
| `overfitting_risk` | OVF-02, OVF-03, OVF-04 | 期間恣意性、多重検定、baseline 比較 |
| `realism` | RLM-03, RLM-06 | スリッページとリバランスコスト |
| `regime_dependency` | RGM-02, RGM-04 | レジーム転換とマクロ依存 |
| `recommendation_risk` | RCR-01, RCR-04 | 過信誘発と条件見落とし |
| FC rules | FC-03, FC-05, FC-06 | 非構造化表現禁止、surviving assumptions、Sharpe 警告 |

### Tier 3: v1 に含められれば望ましい

| Category | Pattern |
|----------|---------|
| `complexity` | CMP-01, CMP-02 |
| `observability` | OBS-04 |
| `cost_assumption` | CST-03 |
| `recommendation_risk` | RCR-03, RCR-05 |

---

## 10. v1 ではまだ扱わない Rubric

| 除外対象 | 理由 | 導入予定 |
|---------|------|---------|
| 実バックテスト結果に基づく Audit | v1 は計画段階。結果ベースの severity 判定は v1.5 | v1.5 |
| ライブパフォーマンスのドリフト検出 | 実運用フィードバックが必要 | v1.5 |
| 規制適合性の Audit | 法的助言の領域。プロダクトスコープ外 | 含めない |
| ユーザーの能力・経験に基づく実行可能性 Audit | ユーザー評価は倫理的・実務的に困難 | 検討中 |
| 市場マイクロ構造の詳細 Audit（tick 単位） | 粒度が細かすぎる。v1 の計画レベルには不要 | v2 |
| 対抗戦略（adversarial agent）の分析 | 他の市場参加者が同一戦略を採用した場合のアルファ侵食。重要だが v1 には重すぎる | v1.5 |
| ESG / 倫理的投資制約の Audit | ドメイン固有の制約として重要だが v1 の最小スコープ外 | v1.5 |
| クロスアセット相関リスクの Audit | ポートフォリオ全体の視点。v1 は単一戦略候補の評価 | v2 |
| テールリスクの定量的 Audit | 極端イベントの定量モデリング。重要だが計画段階では定性評価に留める | v1.5 |
| Audit 自体の品質のメタ Audit（Audit の Audit） | 有用だが v1 では FC-01 の簡易版のみ。体系的メタ Audit は v1.5 | v1.5 |

---

## Appendix A: Audit Object との Schema マッピング

internal_schema.md の Audit Object に本 Rubric がどう接続するか:

```json
{
  "candidate_id": "string",
  "audit_status": "passed | passed_with_warnings | rejected",
  "issues": [
    {
      "issue_id": "string",          // Pattern ID を使用（例: "LKG-01"）
      "severity": "low | medium | high | critical",
      "category": "assumption | evidence_gap | leakage_risk | overfitting_risk | realism | regime_dependency | complexity | observability | cost_assumption | recommendation_risk",
      "title": "string",             // Pattern Name を使用
      "explanation": "string",       // 2文以上。何が問題か → なぜこの severity か
      "mitigation": "string | null", // Mitigation guidance から。null は mitigation なし
      "disqualifying": false         // Disqualifying logic で判定
    }
  ],
  "rejection_reason": "null | string",       // disqualifying issue の集約。3文以上
  "surviving_assumptions": ["string"],       // FC-05 で強制出力
  "residual_risks": ["string"]              // passed 後も残存するリスク
}
```

### audit_status の判定ロジック

```
IF any(issue.disqualifying == true):
  audit_status = "rejected"
  rejection_reason = disqualifying issues の集約テキスト

ELIF count(issue.severity == "high") >= 3:
  audit_status = "passed_with_warnings"

ELIF any(issue.severity == "critical" AND issue.mitigation != null):
  audit_status = "passed_with_warnings"

ELSE:
  audit_status = "passed"
```

---

## Appendix B: Audit 実行順序

Audit は以下の順序で実行する。順序に意味がある（前段の結果が後段の入力になる場合がある）。

```
Phase 1: データ完全性
  → evidence_gap
  → leakage_risk

Phase 2: 手法的妥当性
  → assumption
  → overfitting_risk
  → regime_dependency

Phase 3: 実務的妥当性
  → realism
  → cost_assumption
  → complexity
  → observability

Phase 4: メタ評価
  → recommendation_risk
  → FC rules（横断的）
```

Phase 1 で critical / disqualifying が見つかった場合でも、Phase 2-4 は実行する。理由: 棄却候補にも全 issue を記録することで、Rejection Report の品質を担保する。

---

## Appendix C: 複合判定ルール

単一カテゴリでは disqualifying にならないが、複合すると深刻になるパターン。

| 複合パターン | 構成 | 複合 severity | 棄却判定 |
|-------------|------|-------------|---------|
| 「見せかけの好成績」 | OVF-06 (high Sharpe) + LKG-01/02/03 (leakage) | critical | `disqualifying: true` |
| 「検証不能な複雑性」 | CMP-01 (不要な複雑性) + EVD-01 (必須証拠欠如) | critical | `disqualifying: true` |
| 「コスト死」 | RLM-01 (取引コスト過小) + CST-03 (取引コスト未計上) + 低期待リターン | critical | `disqualifying: true` |
| 「レジーム盲点」 | RGM-01 (単一レジーム) + ASM-02 (定常性仮定) | severity を1段階引き上げ | high→critical で `disqualifying: true` |
| 「過学習パッケージ」 | OVF-01 (パラメータ過多) + OVF-03 (多重検定未補正) + EVD-05 (サンプル外欠如) | critical | `disqualifying: true` |

複合判定は Phase 4 の FC rules 内で実行。単一カテゴリの Audit 完了後にクロスチェック。

---

## Appendix D: Audit 出力の品質基準

Audit 出力自体の品質を維持するための基準。

| 基準 | 要件 | 違反時の処理 |
|------|------|------------|
| issue の explanation は2文以上 | 1文以下の explanation は品質不足 | 再生成を要求 |
| disqualifying issue の explanation は3文以上 | 棄却判定の根拠は特に詳細に | 再生成を要求 |
| 全候補で issue 0件はありえない | FC-01 に基づく | メタ検証を実行 |
| rejection_reason は3文以上 | 何が問題 → なぜ致命的 → 修正可能性 | 再生成を要求 |
| surviving_assumptions は空不可（passed 候補） | FC-05 に基づく | メタ検証を実行 |
| mitigation が汎用的すぎない | 「もっと検証すべき」レベルの mitigation は不可。具体的なデータ・テスト・閾値を含む | 再生成を要求 |
