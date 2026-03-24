# docs/state/ops.md

**Domain**: Operations
**Last updated**: 2026-03-24
**Truth precedence rank**: 3

---

## Domain Purpose

Track the state of the daily automation pipeline: report generation, CI, cron, secrets, and operational failure modes.

---

## Current Confirmed State

**Evidence label**: Mixed — see per-item labels below. Not all items are uniformly Observed.

### Daily report pipeline
| Component | Status | Evidence |
|-----------|--------|----------|
| `ops/run.sh` | ✅ Working | GitHub Actions Run #3 exit 0 confirmed |
| Artifact validation C2–C6 | ✅ Working | Validated with injected fake reports + live run |
| Provider fallback: OpenRouter first | ✅ Working | Run #3: OpenRouter used, 1781 bytes, 7 section headers |
| Anthropic direct fallback | ⚠️ Configured only (Inferred) | Not triggered in Run #3 (OpenRouter succeeded); actual fallback untested |
| Data template fallback | ✅ Implemented | Code exists; not triggered in Run #3 |
| Supabase write (run_logs) | ✅ Working | Run #3: HTTP 409 graceful (duplicate, non-fatal) |
| Git push to main | ✅ Working | Run #3: report pushed to main |

### Run contract (ops/run.sh)
A run is SUCCESS (exit 0) iff:
- C1: Preflight passed (env vars + required files)
- C2: Report file exists at `docs/reports/daily/YYYY-MM-DD.md`
- C3: Report size ≥ 200 bytes
- C4: Report does not start with `{`
- C5: Report first line does not start with `ERROR:`
- C6: Report contains ≥ 2 `## ` section headers

Exit codes: 0=success, 1=preflight, 2=generate failed, 3=validation failed, 4=unexpected error

### GitHub Actions cron
- Schedule: `0 0 * * *` UTC — Observed: defined in `.github/workflows/daily-report.yml`
- Trigger: daily + `workflow_dispatch`
- Natural trigger status: **Unknown** — last 10 checked `daily-report.yml` runs showed only `push` / `pull_request` events; no `schedule`-triggered run confirmed yet (see OL-019)

### OpenHands issue resolver
- Workflow: `.github/workflows/openhands.yml`
- Trigger: `issues: labeled (fix-me)` or `@openhands-agent` comment
- Model: `claude-3-haiku-20240307`
- Status: ✅ E2E confirmed — Issue #21 → PR #22 → merged (Session 4)
- Execution time: ~10 seconds (no pip installs; stdlib only)

### Secrets (confirmed in Run #3)
- `FRED_API_KEY`: present
- `SUPABASE_URL`: present
- `SUPABASE_KEY`: present
- `GITHUB_TOKEN`: present
- `ANTHROPIC_API_KEY`: present (confirmed working Session 4)
- `PAT_TOKEN`: present (confirmed for OpenHands PR creation)
- `PAT_USERNAME`: present

---

## Current Unknowns

| Unknown | Notes |
|---------|-------|
| Railway cron natural trigger | Configured (`bash ops/run.sh`), but no confirmed natural (non-manual) trigger yet |
| Report quality trend | Only 1 live report exists (2026-03-24); trend unknown |
| Supabase run_logs row count | 1 confirmed write; ongoing accumulation not monitored |
| ANTHROPIC_API_KEY billing tier | `claude-haiku-4-5-20251001` returned 400 on prior key; root cause unresolved; current key works with `claude-3-haiku-20240307` |

---

## Related Open Loops

- OL-019: Railway cron natural trigger confirmation

---

## Operational Failure Modes

| Failure | Behavior | Recovery |
|---------|---------|---------|
| OpenRouter 402/429 | Fallback to Anthropic direct | Automatic |
| Anthropic direct failure | Fallback to data-only template | Automatic (always valid markdown) |
| Supabase HTTP 409 | WARNING, non-fatal, run continues | Automatic (PR #20) |
| ERR trap in optional sections | `trap - ERR` set before Supabase + git push blocks | Automatic (PR #20) |
| SIGTERM in GitHub runner | No pip installs in openhands.yml eliminates 150s install time | Fixed (Session 4) |

## Read Next

- `ops/run.sh` — orchestration script
- `ops/RUNBOOK.md` — operator-grade runbook
- `.github/workflows/daily-report.yml` — cron workflow definition
