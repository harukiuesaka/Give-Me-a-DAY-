# OPEN_LOOPS.md

**最終更新**: 2026-03-24 (Session 3 完了後)

---

## フォーマット
```
| ID | カテゴリ | 内容 | 優先度 | 担当 | 追加日 |
```

---

## 現在のオープンループ

| ID | カテゴリ | 内容 | 優先度 | 担当 | 追加日 |
|----|---------|------|-------|------|-------|
| OL-009 | Test | LLM ライブテスト未実施（有効な ANTHROPIC_API_KEY が必要）。ops/run.sh --skip-commit で確認可能 | High | Human | 2026-03-24 |
| OL-011 | Infra | GitHub Secrets に `ANTHROPIC_API_KEY` / `FRED_API_KEY` 設定要確認。CI full green 未確認 | Medium | Human | 2026-03-24 |
| OL-012 | Infra | Railway project 未設定。`ops/run.sh` を cron 実行するには Railway Variables + cron 設定が必要 | Medium | Human | 2026-03-24 |
| OL-013 | Infra | Supabase: free tier cap で restore 不可（3 inactive projects、2 project 上限）。1 件削除または tier 変更が必要 | Medium | Human | 2026-03-24 |

---

## クローズ済み

| ID | 内容 | クローズ日 | 理由 |
|----|------|---------|------|
| OL-001 | `.github/workflows/pr-build.yml` 未作成 | 2026-03-24 | PR #7 merge 済み |
| OL-002 | `docs/architecture/current_system.md` 未作成 | 2026-03-24 | PR #8 merge 済み |
| OL-003 | `docs/agents/ownership.md` / `guardrails.md` 未作成 | 2026-03-24 | PR #9 merge 済み |
| OL-004 | `docs/reports/daily/_template.md` 未作成 | 2026-03-24 | PR #10 merge 済み |
| OL-005 | docs/ フォルダ構造なし | 2026-03-24 | PR #6 merge 済み |
| OL-006 | `scripts/ai/` なし | 2026-03-24 | PR #6, #11, #12, #13 で追加 |
| OL-007 | origin/main より 2 commits 先行 | 2026-03-24 | PR #15–#17 で解消 |
| OL-008 | 未ステージ変更 4 ファイル | 2026-03-24 | OL-014 として統合 |
| OL-010 | OpenHands GitHub Action 未設定 | — | Day 10 タスクとして延期（スコープ外） |
| OL-014 | main に未 push コミット・未ステージ変更 | 2026-03-24 | PR #15, #16 で全解消 |
