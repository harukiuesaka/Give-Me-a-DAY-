# current_system.md

**最終更新**: 2026-03-24  
**ラウンド**: Round 6.12 完了済み  
**作成者**: Claude (Observed from repo)

---

## 現在の主要構成

```
Give-Me-a-DAY-/
├── backend/          # FastAPI + Python 3.11+
├── frontend/         # React 18 + Vite + TypeScript
├── docs/             # Product / system truth layer
├── scripts/          # Dev launcher + AI scripts (新設)
└── ops/              # Agent prompts + schemas (新設)
```

---

## Backend 役割

**技術**: FastAPI 0.104+ / Pydantic v2 / Python 3.11+  
**エントリポイント**: `backend/src/main.py`  
**起動コマンド**: `uvicorn src.main:app --reload --port 8000`  
**テストコマンド**: `pytest -q` (Python 3.11+ 必須)

### モジュール構成

| モジュール | 役割 |
|-----------|------|
| `src/pipeline/` | 12ステップパイプライン（GoalIntake → PresentationBuilder） |
| `src/execution/` | BacktestEngine / DataAcquisition / StatisticalTests / ComparisonEngine / PaperRunEngine |
| `src/judgment/` | AuditEngine（候補の棄却ロジック） |
| `src/companion/` | Companion AI v1（T1〜T7トリガー / CON-01〜CON-06矛盾検出） |
| `src/persistence/` | in-memory store / audit log |
| `src/llm/` | Anthropic Claude API クライアント（フォールバック付き） |
| `src/api/` | FastAPI routes（10エンドポイント + preflight 2本） |
| `src/domain/` | ドメインモデル定義 |
| `src/reporting/` | スタブ（`__init__.py` のみ） |

### 12ステップパイプライン（確認済み）

```
[1] GoalIntake → [2] DomainFramer → [3] ResearchSpecCompiler
→ [4] CandidateGenerator → [5] EvidencePlanner → [6] ValidationPlanner
→ [7] DataAcquisition → [8] BacktestEngine → [9] StatisticalTests
→ [10] ComparisonEngine → [11] AuditEngine → [12] RecommendationEngine
→ PresentationBuilder (出力生成)
```

### Runtime 動作

`main.py` 起動時に `paper-run-lifecycle-runner` スレッドが起動し、  
`RuntimeController.reconcile_active_paper_runs()` を定期実行する。

---

## Frontend 役割

**技術**: React 18 / TypeScript / Vite / TailwindCSS  
**エントリポイント**: `frontend/src/main.tsx`  
**ビルドコマンド**: `npm run build` (tsc && vite build)  
**開発コマンド**: `npm run dev`

### ページ構成

| ページ | ルート | 役割 |
|-------|-------|------|
| `InputPage.tsx` | `/` | 3ステージフロー（input → clarification → review） |
| `LoadingPage.tsx` | `/loading` | 12ステップポーリング |
| `PresentationPage.tsx` | `/presentation` | 候補カード2枚表示 |
| `ApprovalPage.tsx` | `/approval` | 理解度チェック + 3チェックボックス承認 |
| `StatusPage.tsx` | `/status` | Paper Run ステータス / ライフサイクルイベント / 再承認フロー |

### 特記事項
- `window.localStorage` を使用（`ACTIVE_PAPER_RUN_ID_KEY`）
- `frontend/dist/` が存在 → 過去に build 成功実績あり

---

## docs 役割

**product truth layer** として機能する最高優先度ドキュメント群。

| パス | 内容 |
|-----|------|
| `docs/product/product_definition.md` | プロダクト定義 |
| `docs/product/v1_boundary.md` | v1 スコープ境界 |
| `docs/system/core_loop.md` | 12ステップ Core Loop 仕様 |
| `docs/system/internal_schema.md` | 内部データ構造 |
| `docs/system/execution_layer.md` | Validation 実行 / Paper Run |
| `docs/output/v1_output_spec.md` | 出力仕様 |
| `docs/architecture/` | *(今回新設)* システム構成ドキュメント |
| `docs/reports/` | *(今回新設)* daily / weekly report 格納先 |
| `docs/marketing/` | *(今回新設)* 施策ログ / KPI週報 |

---

## scripts 役割

| スクリプト | 役割 | 状態 |
|-----------|------|------|
| `scripts/setup.sh` | backend install / frontend install / .env 作成 / data directories 作成 | 実装済み |
| `scripts/run_dev.sh` | backend uvicorn + frontend vite を同時起動 | 実装済み |
| `scripts/ai/run_build_checks.sh` | frontend build + backend pytest を実行して markdown summary を出力 | PR #7 で追加 |
| `scripts/ai/generate_daily_report.sh` | daily report 生成 | 未作成 |
| `scripts/ai/detect_architecture_drift.sh` | docs vs 実装の drift 候補抽出 | 未作成 |
| `scripts/ai/detect_marketing_health.sh` | marketing logs からの健全性サマリー | 未作成 |

---

## 確認済みコマンド

```bash
# Backend
pip install -e ".[dev]"      # 依存インストール
uvicorn src.main:app --reload --port 8000  # 起動
pytest -q                    # テスト (Python 3.11+ 必須)

# Frontend
npm install                  # 依存インストール
npm run build                # tsc && vite build
npm run dev                  # 開発サーバー起動

# CI (GitHub Actions)
# .github/workflows/pr-build.yml が PR 時に frontend build + backend pytest を実行
```

---

## Architecture Drift 監視ポイント

以下の点が今後 drift の候補になりやすい。

| ポイント | 理由 |
|---------|------|
| `src/reporting/` モジュール | `__init__.py` のみのスタブ。実装されたら docs 更新が必要 |
| `src/judgment/audit_patterns/` | 同上 |
| `src/execution/paper_run/` | 同上 |
| `companion/` の trigger 数 | T7 まで定義済み。追加時に core_loop.md と整合確認が必要 |
| `frontend/src/pages/` | StatusPage に月次レポート UI が未追加 |

---

## UNKNOWN / 未確認

- `backend/src/api/routes.py` の全10エンドポイント詳細（Observed: 10本の存在のみ確認）
- `frontend/src/api/client.ts` の backend 呼び出しパターン
- `scripts/setup.sh` の data directories 実体（実行未確認）
