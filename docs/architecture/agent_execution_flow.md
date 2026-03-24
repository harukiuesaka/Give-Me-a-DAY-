# agent_execution_flow.md

**最終更新**: 2026-03-24
**用途**: AI エージェントが毎日どのような順序で実行されるかを示すフロー。Railway cron + ops/run.sh の動作仕様。

---

## Daily Execution Flow

```
[Railway cron] 0 0 * * * (UTC = JST 09:00)
    │
    ▼
[ops/run.sh] — オーケストレーター
    │
    ├─[1] PREFLIGHT
    │   ├── env vars 確認 (ANTHROPIC_API_KEY 必須)
    │   └── required scripts の存在確認
    │
    ├─[2] DATA COLLECTION (並列ではなく順次)
    │   ├── run_build_checks.sh  → /tmp/gmd_build.md
    │   ├── detect_architecture_drift.sh → /tmp/gmd_drift.md
    │   └── detect_marketing_health.sh → /tmp/gmd_marketing.md
    │
    ├─[3] REPORT GENERATION
    │   └── generate_daily_report.sh
    │       ├── /tmp/gmd_*.md を読む
    │       ├── OPEN_LOOPS.md を読む
    │       ├── LLM 呼び出し (OpenRouter → Anthropic fallback → data template)
    │       └── docs/reports/daily/YYYY-MM-DD.md を書く
    │
    ├─[4] ARTIFACT VALIDATION (C2–C6)
    │   ├── ファイル存在確認
    │   ├── サイズ ≥ 200 bytes
    │   ├── JSON エラーペイロードでないこと
    │   ├── ERROR: で始まらないこと
    │   └── ## セクションが ≥ 2 あること
    │
    ├─[5] SUPABASE WRITE (optional)
    │   └── write_run_state.py → run_logs テーブルに INSERT
    │
    ├─[6] GIT COMMIT + PUSH (optional)
    │   └── docs/reports/daily/YYYY-MM-DD.md を main に push
    │
    └─[7] SUMMARY → exit 0 (success) or exit 1/2/3 (failure)
```

---

## エージェント責任分担

| エージェント役割 | 実体 | トリガー | 書き込み先 |
|---------------|------|---------|----------|
| Dev / Build Agent | `run_build_checks.sh` | ops/run.sh (daily) | `/tmp/gmd_build.md`, `_last_build_check.md` |
| Docs / Knowledge Agent | `generate_daily_report.sh` | ops/run.sh (daily) | `docs/reports/daily/YYYY-MM-DD.md` |
| Growth / CMO Agent | `detect_marketing_health.sh` | ops/run.sh (daily) | `/tmp/gmd_marketing.md`, `_last_marketing_check.md` |
| Drift Monitor | `detect_architecture_drift.sh` | ops/run.sh (daily) | `/tmp/gmd_drift.md`, `_last_drift_check.md` |
| Run State Writer | `write_run_state.py` | ops/run.sh (post-generation) | Supabase `run_logs` |

---

## 手動トリガー

```bash
# preflight 確認のみ
bash ops/run.sh --check-only

# LLM なし・git push なし（artifact validation まで確認）
bash ops/run.sh --dry-run

# LLM あり・git push なし（LLM 動作確認）
bash ops/run.sh --skip-commit

# フル実行
bash ops/run.sh
```

---

## 将来: OpenHands Issue→PR フロー（Day 10 以降）

```
[GitHub Issue] + label: fix-me
    │
    ▼
[OpenHands GitHub Action]
    ├── issue を読む
    ├── repo を clone
    ├── 修正 branch を作る
    └── PR を提出 → Haruki がレビュー・merge
```

OpenHands は branch/PR/report まで。main merge は Haruki が持つ。
