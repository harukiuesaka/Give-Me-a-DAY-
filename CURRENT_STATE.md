# CURRENT_STATE.md

**最終更新**: 2026-03-24 (Session 3)
**Session 3 PR**: #17 (refactor/ops-contract-v2)

---

## Architecture: Responsibility Boundaries (post PR #17)

```
ops/run.sh  ←── single orchestration owner
├── [1] PREFLIGHT       env vars + required files
├── [2] COLLECT         run sub-scripts → /tmp/gmd_*.md
├── [3] GENERATE        call generate_daily_report.sh (LLM → file only)
├── [4] VALIDATE        enforce contract C2–C6 on artifact
├── [5] PERSIST         write_run_state.py → Supabase (optional)
├── [6] COMMIT          git add + commit + push (optional)
└── [7] SUMMARY         print outcome

generate_daily_report.sh  ←── generation only
├── reads /tmp/gmd_*.md (written by ops/run.sh)
├── reads OPEN_LOOPS.md
├── calls LLM (OpenRouter → Anthropic fallback → data template)
├── writes docs/reports/daily/YYYY-MM-DD.md
└── writes /tmp/gmd_meta/{build,drift,marketing}_status

write_run_state.py  ←── persistence only
└── inserts into Supabase run_logs (called by ops/run.sh)
```

---

## Run Contract (ops/run.sh)

A run is **SUCCESS (exit 0)** iff:
- [C1] Preflight passed
- [C2] Report file exists at `docs/reports/daily/YYYY-MM-DD.md`
- [C3] Report size ≥ 200 bytes
- [C4] Report does not start with `{` (JSON error payload rejected)
- [C5] Report first line does not start with `ERROR:`
- [C6] Report contains ≥ 2 `## ` section headers

Optional steps (Supabase write, git push) do not affect the contract.

Exit codes: 0=success, 1=preflight, 2=generate failed, 3=validation failed, 4=unexpected error

---

## Provider Fallback Policy (generate_daily_report.sh)

| Order | Provider | Trigger for fallback |
|-------|----------|---------------------|
| 1 | OpenRouter | Response missing `choices` key (402, 429, 5xx, curl error) |
| 2 | Anthropic direct | Response missing `type: message` (401, 429, 5xx, curl error) |
| 3 | Data-only template | Both fail — always produces valid markdown, never writes JSON/ERROR: |

---

## Verified (this session)

| Test | Method | Result |
|---|---|---|
| `--check-only` no key → exit 1 | live run in /tmp/gmd-inspect | ✅ |
| `--dry-run` → exit 0, C2–C6 pass | live run, 2197 bytes, 7 headers | ✅ |
| JSON payload artifact → exit 3 C4 | injected fake report | ✅ |
| Too-small artifact → exit 3 C3 | injected 56-byte file | ✅ |
| `bash -n` all scripts | syntax check | ✅ |

---

## Verified (previous sessions)

| Component | Status |
|---|---|
| CI `.github/workflows/pr-build.yml` (PR #7) | ✅ verified in GitHub Actions |
| `detect_architecture_drift.sh` (PR #11) | ✅ verified in clean clone |
| `detect_marketing_health.sh` (PR #12) | ✅ verified in clean clone |

---

## Present-only (not verified end-to-end)

- LLM live call (needs valid ANTHROPIC_API_KEY or OpenRouter with credits)
- Full run with git push (needs GITHUB_TOKEN + LLM key in same env)
- Supabase write (blocked by free tier cap)
- Railway cron (not yet configured)

---

## HUMAN_REQUIRED Blockers (in priority order)

1. **LLM key**: Set `ANTHROPIC_API_KEY` in Railway env  
   → Then run: `bash ops/run.sh --skip-commit` to verify LLM works

2. **Supabase**: Delete 1 of 3 inactive projects at https://supabase.com/dashboard  
   → Restore 1 → apply `ops/schemas/run_state_schema.sql` → add `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`

3. **Railway**: Configure `bash ops/run.sh` as cron  
   → See `ops/RUNBOOK.md §3` for exact steps

---

## Merged PRs (all)

| PR | Description | Status |
|----|-------------|--------|
| #6 | initial docs structure | ✅ |
| #7 | CI workflow | ✅ |
| #8–#10 | docs: architecture, agents, templates | ✅ |
| #11 | detect_architecture_drift.sh | ✅ |
| #12 | detect_marketing_health.sh | ✅ |
| #13 | generate_daily_report.sh (initial) | ✅ |
| #14 | write_run_state.py + run_state_schema.sql | ✅ |
| #15 | ops bug fixes (8 bugs) | ✅ |
| #16 | CURRENT_STATE.md + SESSION_HANDOFF.md | ✅ |
| #17 | ops contract refactor + artifact validation C2–C6 | ✅ |
