# OPEN_LOOPS.md

**Role**: Full list of unresolved loops. Optimized for AI execution and closure.
**Last updated**: 2026-03-25 (Session 7 — DeepSeek rerun triggered; results not persisted)

---

## AI Control Summary

| Category | Loops |
|----------|-------|
| Highest priority | OL-017 (P1 — partial run done, 6 cases remain), OL-016 (P1 — customer validation), OL-022 (P1 — API key fix required) |
| Human-required | OL-016, OL-022 (API key recharge/rotation), legal review (see `docs/state/risk.md` R-003) |
| External-blocked | OL-016 (requires real interviews) |
| Direction-risk | OL-016 (PMF unknown — all product direction is unvalidated until resolved) |

---

## Open Loops

---

### OL-022
**Title**: Eval provider / key — DeepSeek rerun triggered; results not yet persisted to main
**Domain**: Engineering / Ops
**Priority**: P1
**Status**: in_progress — PR #28 merged 2026-03-25; first DeepSeek rerun triggered; result NOT committed to main
**Owner**: human (Haruki)
**What happened (2026-03-25)**:
- Original blocker: Anthropic API credit exhausted → migrated eval to DeepSeek (`https://api.deepseek.com/anthropic`, `deepseek-chat`, `ANTHROPIC_API_KEY` wired from `DEEPSEEK_API_KEY` secret). PR #28 merged.
- User triggered `eval-run.yml` on main. Workflow reported complete. No new result file appeared on main (confirmed by `git fetch --all`).
- Root cause: UNKNOWN. Possible: (A) `DEEPSEEK_API_KEY` secret value is invalid/expired; (B) DeepSeek API rejected request; (C) `git push origin HEAD` failed; (D) workflow ran on wrong branch.
**Next Action**: Human must: (1) open GitHub → Actions → `eval-run.yml` → latest run → inspect step logs; (2) confirm `DEEPSEEK_API_KEY` secret is set with a valid active key; (3) re-trigger `eval-run.yml` on `main` branch.
**Unknowns**: Whether `DEEPSEEK_API_KEY` secret is valid; whether DeepSeek API responded; whether push step succeeded
**Related Files**: `.github/workflows/eval-run.yml`, `scripts/eval_runner.py`, `evals/results/`
**Close Condition**: `eval-run.yml` produces a result file committed to main with status `ok` for the 6 remaining cases (DF-02, DF-03, DF-05, CG-02, CG-04, VP-02)

---

### OL-016
**Title**: Mom Test / customer validation
**Domain**: Marketing / Product
**Priority**: P1
**Status**: open
**Owner**: human
**Blocker**: No candidate list, no interview sessions scheduled
**Next Action**: Human creates target interview list; agent drafts outreach copy for review
**Unknowns**: ICP not validated; no user signal; messaging fit unknown
**Related Files**: `docs/state/marketing.md`, `docs/state/product.md`
**Close Condition**: ≥ 3 Mom Test interviews completed; findings recorded in `docs/marketing/logs/`
**Do Not**: Conduct outreach or publish content without human approval

---

### OL-017
**Title**: LLM output quality — eval run 01 partial (6/12 cases; 6 blocked by API key)
**Domain**: Product / Engineering
**Priority**: P1
**Status**: in_progress — partial run complete; 6 cases remaining
**Owner**: agent (scoring) / human (API key fix to unblock remaining 6)
**Blocker**: OL-022 (ANTHROPIC_API_KEY credit exhaustion) blocks remaining 6 cases
**Update (2026-03-25)**: DeepSeek rerun triggered post-merge. No new results committed. Cause: UNKNOWN (see OL-022). No new cases scored.
**Next Action**: Human resolves OL-022 (confirms DeepSeek secret + re-triggers workflow); agent scores 6 remaining cases and closes OL-017 with full 12/12 coverage
**Observed (Run 01, 2026-03-25 — 6 cases, in-context generation, claude-sonnet-4-6)**:
- DomainFramer: 2/5 cases run (DF-01, DF-04). Avg 4.6. Verdict: acceptable.
- CandidateGenerator: 2/4 cases run (CG-01, CG-03). Avg 5.0. Verdict: acceptable.
- ValidationPlanner: 2/3 cases run (VP-01, VP-03). Avg 4.9. Verdict: acceptable.
- No `not_ready` or `internal_only` verdict triggered.
- Recommendation: **A (conditional)** — acceptable for limited testing on FACTOR archetype inputs. ALT_DATA and STAT_ARB must not be exposed until DF-05 and CG-02 are tested.
**Unknown (unrun cases)**:
- DF-05 (ALT_DATA hallucination risk) — highest-risk unrun case
- CG-02 (STAT_ARB forbidden behavior adherence)
- VP-02 (ML_SIGNAL sensitivity test generation)
- DF-02, DF-03, CG-04 — lower risk but coverage incomplete
**Related Files**: `docs/evals/llm_quality_eval.md`, `evals/llm_quality_cases.json`, `evals/results/run_2026-03-25.jsonl`, `evals/results/scores_2026-03-25.csv`, `docs/evals/llm_quality_run_01.md`, `docs/state/engineering.md`
**Close Condition**: All 12 cases scored with Observed label; per-module averages in `docs/state/engineering.md`; recommendation confirmed or revised based on full coverage

---

### OL-019
**Title**: Railway cron natural trigger confirmation
**Domain**: Ops
**Priority**: P2
**Status**: open
**Owner**: agent (detect) / human (respond)
**Blocker**: Waiting for UTC 00:00 natural trigger on Railway
**Next Action**: Agent checks Railway logs after next UTC 00:00; records exit code and trigger event type in `docs/state/ops.md`
**Unknowns**: Whether Railway cron fires `bash ops/run.sh` correctly; whether exit code is 0 on Railway environment; whether generated report is pushed to repo
**Observed so far**: Last 10 checked `daily-report.yml` GitHub Actions runs show only `push` / `pull_request` event types — no `schedule`-triggered run confirmed. Railway cron configured as `bash ops/run.sh` (not GitHub Actions).
**Related Files**: `docs/state/ops.md`, `ops/run.sh`, Railway dashboard
**Close Condition**: At least 1 natural Railway cron run confirmed with exit code 0 and report file in `docs/reports/daily/`; result recorded with Observed label

---

## Closed Loops (archive)

| ID | Title | Closed | Reason |
|----|-------|--------|--------|
| OL-001 | `pr-build.yml` not created | 2026-03-24 | PR #7 |
| OL-002 | `docs/architecture/current_system.md` missing | 2026-03-24 | PR #8 |
| OL-003 | `docs/agents/ownership.md` / `guardrails.md` missing | 2026-03-24 | PR #9 |
| OL-004 | `docs/reports/daily/_template.md` missing | 2026-03-24 | PR #10 |
| OL-005 | docs/ folder structure missing | 2026-03-24 | PR #6 |
| OL-006 | `scripts/ai/` missing | 2026-03-24 | PRs #6, #11, #12, #13 |
| OL-007 | main 2 commits ahead of origin | 2026-03-24 | PRs #15–#17 |
| OL-008 | 4 unstaged files | 2026-03-24 | Merged into OL-014 |
| OL-009 | LLM live test not run | 2026-03-24 | GitHub Actions Run #3: OpenRouter confirmed |
| OL-010 | OpenHands GitHub Action not configured | 2026-03-24 | Haruki setup complete |
| OL-011 | GitHub Secrets unverified | 2026-03-24 | Run #3: all secrets confirmed |
| OL-012 | Railway cron not configured | 2026-03-24 | Railway cron set to `bash ops/run.sh` |
| OL-013 | Supabase free tier cap | 2026-03-24 | Inactive project deleted; active project confirmed |
| OL-014 | Unpushed commits / unstaged changes on main | 2026-03-24 | PRs #15, #16 |
| OL-015 | OpenHands E2E test | 2026-03-24 | PR #22 merged (Session 4) |
| OL-018 | CI green confirmation on latest HEAD | 2026-03-24 | CI run 23493826997: Frontend Build ✅ + Backend Tests ✅ on feat/state-architecture-v1 tip bdb668fa5 (same app code as main) |
| OL-020 | State architecture + grounding audit (two open PRs) | 2026-03-24 | PR #23 (state arch) + PR #24 (grounding audit) both merged to main |
| OL-021 | LLM eval package — open PR, awaiting merge + first run | 2026-03-25 | PR #25 (eval package), PR #26/#27 (eval runner) merged; first run executed (6/12 Observed); OL-017 continues for remaining 6 |
