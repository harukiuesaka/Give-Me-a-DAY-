# SESSION_HANDOFF.md

**Role**: Startup file for next AI session. Latest only.
**Last updated**: 2026-03-25 (Session 7 — DeepSeek rerun triggered; results not persisted)

---

**Mode**: Eval / Ops — DeepSeek migration on main; rerun ran but results not committed

**Branch**: `main` (PR #28 merged — DeepSeek migration + eval corrections)

**Current state**:
- PR #28 merged. `eval-run.yml` now uses `ANTHROPIC_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}` + `LLM_BASE_URL: https://api.deepseek.com/anthropic`.
- First DeepSeek rerun triggered. **No new result file committed to main.** Root cause UNKNOWN.
- Repo eval state: 6/12 ok, 6/12 api_error (original Run 01 data; unscored: DF-02, DF-03, DF-05, CG-02, CG-04, VP-02).
- OL-022 status: in_progress (blocker changed: now `DEEPSEEK_API_KEY` secret validity + push confirmation).

**Now — human actions required**:
1. **Diagnose**: Open GitHub → Actions → `eval-run.yml` → latest run → read step logs. Identify which step failed: "Run eval" (api_error?) or "Commit results" (push failed?).
2. **Confirm secret**: Check GitHub repository secrets → `DEEPSEEK_API_KEY` is set and has a valid active DeepSeek API key value.
3. **Re-trigger**: `eval-run.yml` workflow_dispatch on `main` branch.
4. After results committed: tell agent "eval rerun committed" → agent scores 6 cases, closes OL-017, updates state.

**Eval baseline (Observed, 2026-03-25 — 6/12 cases, Run 01)**:
- DomainFramer (DF-01, DF-04): avg 4.6 — acceptable
- CandidateGenerator (CG-01, CG-03): avg 5.0 — acceptable
- ValidationPlanner (VP-01, VP-03): avg 4.9 — acceptable
- **Recommendation A (conditional)**: Limited human testing permitted on FACTOR archetype goals
- **DO NOT expose ALT_DATA or STAT_ARB goal types** until DF-05 + CG-02 are scored

**Read First**:
1. `SYSTEM_PRINCIPLES.md`
2. `CURRENT_STATE.md`
3. `OPEN_LOOPS.md` — note OL-022 (in_progress) and OL-017 (partial)
4. `docs/system/factory_layer_preconditions.md` — C2 partially met, C1/C3/C4 unmet

**Unknown**: DF-05, CG-02, VP-02, DF-02, DF-03, CG-04 scores. Why DeepSeek rerun results not persisted. Railway cron natural trigger (OL-019).

**Human Required**:
- **OL-022**: Inspect Actions log + confirm `DEEPSEEK_API_KEY` secret + re-trigger eval
- **OL-016**: Mom Test — no interviews scheduled, no candidate list exists
- Any external outreach
