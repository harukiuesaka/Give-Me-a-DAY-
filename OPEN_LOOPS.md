# OPEN_LOOPS.md

**Role**: Full list of unresolved loops. Optimized for AI execution and closure.
**Last updated**: 2026-03-24 (Session 5 — grounding audit)

---

## AI Control Summary

| Category | Loops |
|----------|-------|
| Highest priority | OL-020 (P0 — state architecture + audit PRs), OL-016 (P1 — customer validation) |
| Human-required | OL-016, OL-020 (both PRs to merge), legal review (see `docs/state/risk.md` R-003) |
| External-blocked | OL-016 (requires real interviews) |
| Direction-risk | OL-016 (PMF unknown — all product direction is unvalidated until resolved) |

---

## Open Loops

---

### OL-020
**Title**: State architecture + grounding audit (two open PRs)
**Domain**: Engineering / Docs
**Priority**: P0
**Status**: in_progress
**Owner**: agent / human (merge)
**Blocker**: None — both PRs open, awaiting human merge
**Next Action**: Human reviews and merges `feat/state-architecture-v1` (PR #23), then `fix/state-grounding-audit`
**Unknowns**: None blocking — all files created and audited per spec
**Related Files**: `SYSTEM_PRINCIPLES.md`, `docs/state/`, `CURRENT_STATE.md`, `OPEN_LOOPS.md`, `SESSION_HANDOFF.md`
**Close Condition**: Both PRs merged to main; all spec files present, role-correct, and evidence-labeled

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
**Title**: LLM output quality verification (real pipeline runs)
**Domain**: Product / Engineering
**Priority**: P2
**Status**: open
**Owner**: agent
**Blocker**: No production deployment; no real user inputs to test against
**Next Action**: Agent runs pipeline with representative real-world investment goals; records output quality in `docs/state/engineering.md`
**Unknowns**: DomainFramer and CandidateGenerator output quality on real inputs; LLM hallucination rate; fallback trigger rate
**Related Files**: `docs/state/engineering.md`, `backend/src/pipeline/domain_framer.py`, `backend/src/pipeline/candidate_generator.py`
**Close Condition**: ≥ 3 representative goals processed end-to-end; quality assessment recorded with Observed evidence label

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
