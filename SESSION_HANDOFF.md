# SESSION_HANDOFF.md

**最終更新**: 2026-03-24 (Session 2 — 完全完了)

---

## 完了済み PR（全 merge 済み）

| PR | Day | 内容 |
|----|-----|------|
| #6  | 1   | docs/ フォルダ構造 + OPEN_LOOPS / DECISIONS / SESSION_HANDOFF |
| #7  | 5   | `.github/workflows/pr-build.yml` + `scripts/ai/run_build_checks.sh` |
| #8  | 2   | `docs/architecture/current_system.md` 初版 |
| #9  | 3   | `docs/agents/ownership.md` + `guardrails.md` |
| #10 | 4   | `docs/reports/daily/_template.md` + `ops/prompts/owner_report.md` |
| #11 | 6   | `scripts/ai/detect_architecture_drift.sh` |
| #12 | 7+8 | marketing templates + `detect_marketing_health.sh` |
| #13 | 9   | `scripts/ai/generate_daily_report.sh` (OpenRouter) + `ops/prompts/docs_agent.md` |
| #14 | 13  | `ops/schemas/run_state_schema.sql` + `ops/scripts/write_run_state.py` |

---

## 残タスク（Human のみ）

| ID | 内容 | 難易度 |
|----|------|-------|
| OL-011 | GitHub Secrets に `ANTHROPIC_API_KEY` / `FRED_API_KEY` / `OPENROUTER_API_KEY` を設定 | 低 |
| OL-012 | Railway project 作成 → `generate_daily_report.sh` を朝 cron に設定 | 中 |
| OL-013 | Supabase project 作成 → `run_state_schema.sql` を適用 → env vars 設定 | 中 |
| OL-014 | main の未 push コミット 2 件 + 未ステージ変更 4 ファイルを処理 | 低 |

---

## Day 14（通し運転）の実行手順

OL-011〜013 が完了したら以下を実行する:

```bash
# ローカルで通し運転
export OPENROUTER_API_KEY=sk-or-v1-...
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJ...

bash scripts/ai/generate_daily_report.sh
# → docs/reports/daily/YYYY-MM-DD.md が生成される

python3 ops/scripts/write_run_state.py \
  --run-id "$(date +%Y-%m-%d)_daily_report" \
  --agent-type "daily_report" \
  --status "success"
# → Supabase run_logs に記録される
```

---

## 次のセッション起動プロンプト

```
SESSION_HANDOFF.md と OPEN_LOOPS.md を読んでください。
Day 1〜9, 13 は完了済み。次の目的: [Day 10 OpenHands / Day 12 Railway / Day 14 通し運転]

運用ルール:
- 1ターン1目的 / 推測を事実として書かない / 不明点は UNKNOWN
- git lock のため変更は GitHub API 経由で実行
- main 直変更・課金・削除は人間確認
- 毎回 [STATE][MODE][PLAN][OUTPUT][SESSION_HANDOFF] 形式
```
