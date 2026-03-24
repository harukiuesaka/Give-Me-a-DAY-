# module_map.md

**最終更新**: 2026-03-24
**用途**: モジュールごとの責任・入出力・依存関係の早見表。architecture drift 検知の基準として使う。

---

## Backend モジュールマップ

| モジュール | 責任 | 主な入力 | 主な出力 | 依存 |
|-----------|------|---------|---------|------|
| `src/pipeline/goal_intake.py` | ユーザーゴールの構造化 | raw goal text | `GoalSpec` | domain/models |
| `src/pipeline/domain_framer.py` | ドメイン特定・フレーミング | `GoalSpec` | `DomainFrame` | llm/client |
| `src/pipeline/research_spec_compiler.py` | リサーチ仕様の生成 | `DomainFrame` | `ResearchSpec` | llm/client |
| `src/pipeline/candidate_generator.py` | 候補システム方向の生成 | `ResearchSpec` | `CandidateSet` | llm/client |
| `src/pipeline/evidence_planner.py` | エビデンス要件の定義 | `CandidateSet` | `EvidencePlan` | domain/models |
| `src/pipeline/validation_planner.py` | 検証計画の生成 | `EvidencePlan` | `ValidationPlan` | domain/models |
| `src/execution/data_acquisition.py` | データ取得（FRED等） | `EvidencePlan` | raw data | external APIs |
| `src/execution/backtest_engine.py` | バックテスト実行 | strategy + data | `BacktestResult` | - |
| `src/execution/statistical_tests.py` | 統計検定 | `BacktestResult` | `StatTestResult` | - |
| `src/execution/comparison_engine.py` | 候補比較 | `CandidateSet` + results | `ComparisonReport` | - |
| `src/judgment/audit_engine.py` | 候補の棄却ロジック | `ComparisonReport` | `AuditResult` | - |
| `src/pipeline/recommendation_engine.py` | 最終推薦生成 | `AuditResult` | `Recommendation` | llm/client |
| `src/pipeline/presentation_builder.py` | 出力パッケージ生成 | `Recommendation` | `PresentationPackage` | - |
| `src/companion/` | Companion AI (T1-T7 / CON-01-06) | pipeline events | questions/contradictions | llm/client |
| `src/llm/client.py` | LLM API呼び出し | prompt | response | anthropic SDK |
| `src/llm/fallbacks.py` | LLMフォールバック制御 | error type | fallback response | llm/client |
| `src/api/routes.py` | FastAPI endpoints (10本) | HTTP request | HTTP response | pipeline/* |
| `src/persistence/store.py` | in-memory state store | run events | stored state | - |
| `src/reporting/` | レポート生成（スタブ） | - | - | 未実装 |

---

## Frontend モジュールマップ

| ファイル | 責任 | 遷移先 |
|---------|------|-------|
| `src/pages/InputPage.tsx` | 3ステージ入力フロー | `/loading` |
| `src/pages/LoadingPage.tsx` | 12ステップポーリング | `/presentation` |
| `src/pages/PresentationPage.tsx` | 候補カード2枚表示 | `/approval` |
| `src/pages/ApprovalPage.tsx` | 理解度確認 + 承認 | `/status` |
| `src/pages/StatusPage.tsx` | Paper Run ステータス | (ループ) |
| `src/api/client.ts` | バックエンドAPI呼び出し | - |
| `src/types/schema.ts` | 型定義 | - |

---

## Ops / Scripts マップ

| ファイル | 責任 | 呼び出し元 |
|---------|------|----------|
| `ops/run.sh` | 全体オーケストレーション | Railway cron / 手動 |
| `scripts/ai/run_build_checks.sh` | frontend build + pytest 実行 | ops/run.sh |
| `scripts/ai/detect_architecture_drift.sh` | docs vs 実装の差分検出 | ops/run.sh |
| `scripts/ai/detect_marketing_health.sh` | marketing logs の健全性確認 | ops/run.sh |
| `scripts/ai/generate_daily_report.sh` | LLM → daily report 生成 | ops/run.sh |
| `scripts/ai/collect_issue_context.py` | GitHub issues の要約収集 | generate_daily_report.sh |
| `ops/scripts/write_run_state.py` | Supabase run_logs への書き込み | ops/run.sh |

---

## 既知の drift 候補ポイント

1. `src/reporting/` — スタブのみ。実装が進んだ場合は current_system.md と module_map.md を更新すること
2. `src/persistence/store.py` — in-memory。Supabase移行が発生した場合は依存関係が変わる
3. `src/llm/fallbacks.py` — フォールバック戦略が ops 側と二重管理にならないよう注意
4. frontend localStorage — `ACTIVE_PAPER_RUN_ID_KEY` がバックエンド状態と乖離するリスクあり

