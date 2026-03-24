# OPEN_LOOPS.md

**Role**: Full list of unresolved loops. Optimized for AI execution and closure.
**Last updated**: 2026-03-24 (Session 5 — eval package)

---

## AI Control Summary

| Category | Loops |
|----------|-------|
| Highest priority | OL-017 (P1 — eval package merged, first run now executable), OL-016 (P1 — customer validation) |
| Human-required | OL-016, OL-021 (merge), legal review (see `docs/state/risk.md` R-003) |
| External-blocked | OL-016 (requires real interviews) |
| Direction-risk | OL-016 (PMF unknown — all product direction is unvalidated until resolved) |

---

## Open Loops

---

### OL-021
**Title**: LLM eval package — open PR, awaiting merge + first run
**Domain**: Engineering / Product
**Priority**: P1
**Status**: in_progress
**Owner**: agent (setup) / human (merge + first run trigger)
**Blocker**: PR merge pending
**Next Action**: Human merges `feat/eval-layer` PR; agent runs first eval pass using `docs/evals/llm_quality_eval.md` procedure; records results in `evals/results/`
**Unknowns**: DomainFramer and CandidateGenerator actual scores; whether any module is in `not_ready` state; ValidationPlanner falsifiability quality
**Related Files**: `docs/evals/llm_quality_eval.md`, `evals/llm_quality_cases.json`, `evals/results/README.md`, `docs/state/engineering.md`
**Close Condition**: First eval run complete; per-module scores recorded in `evals/results/scores_YYYY-MM-DD.csv`; `docs/state/engineering.md` updated with Observed labels

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
**Title**: LLM output quality — first eval run (eval package now exists)
**Domain**: Product / Engineering
**Priority**: P1
**Status**: open — eval framework defined, first run not yet executed
**Owner**: agent
**Blocker**: OL-021 (eval PR merge) must complete first
**Next Action**: After OL-021 merged, agent executes first eval run per `docs/evals/llm_quality_eval.md` procedure; records raw outputs in `evals/results/run_YYYY-MM-DD.jsonl` and scores in `evals/results/scores_YYYY-MM-DD.csv`
**Unknowns**: DomainFramer D3 (falsifiability) score; CandidateGenerator D5 (diversity) score; ValidationPlanner D3 (failure conditions) score; hallucination rate on ALT_DATA and ML_SIGNAL archetypes
**What is now defined (Observed as of 2026-03-24)**:
- Eval target: DomainFramer, CandidateGenerator, ValidationPlanner
- Rubric: 6 dimensions (D1–D6), 1–5 scale
- Test set: 12 cases across 3 modules in `evals/llm_quality_cases.json`
- Procedure: manual-first; records in `evals/results/`
- Thresholds: not_ready / internal_only / acceptable / ready defined
**Related Files**: `docs/evals/llm_quality_eval.md`, `evals/llm_quality_cases.json`, `evals/results/README.md`, `docs/state/engineering.md`
**Close Condition**: First eval run complete; all 12 cases scored; per-module averages recorded with Observed label in `docs/state/engineering.md`

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
