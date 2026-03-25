# SESSION_HANDOFF.md

**Role**: Startup file for next AI session. Latest only.
**Last updated**: 2026-03-25 (Session 6 — DeepSeek eval migration applied)

---

**Mode**: Engineering / Eval — Run 01 results ready for PR merge

**Branch**: `feat/eval-run-01-results` (PR open — eval run 01 results + state updates)

**Now**:
1. **Human: merge `feat/eval-run-01-results` PR #28** — contains eval run 01 results, DeepSeek migration, preconditions tracker, blocker plan, Mom Test run plan, and OL-022 recovery docs
2. **Human: confirm `deepseekllm` secret exists** in GitHub Secrets (Settings → Secrets and variables → Actions)
3. **Human: trigger `eval-run.yml`** on main via workflow_dispatch — uses DeepSeek now (no Anthropic key needed)
4. **Human: tell agent "eval rerun complete"** — agent scores new cases, closes OL-017, updates C2 status
5. **Human (parallel): start OL-016** — read `docs/research/mom_test_run_plan.md`, build respondent list, request outreach copy from agent

**Eval Run 01 Results (Observed, 2026-03-25 — 6/12 cases)**:
- DomainFramer (DF-01, DF-04): avg 4.6 — acceptable
- CandidateGenerator (CG-01, CG-03): avg 5.0 — acceptable
- ValidationPlanner (VP-01, VP-03): avg 4.9 — acceptable
- **Recommendation A (conditional)**: Limited human testing permitted on FACTOR archetype goals
- **DO NOT expose ALT_DATA or STAT_ARB goal types** until DF-05 + CG-02 are scored

**Success**: PR merged; OL-022 resolved; `eval-run.yml` triggered and produces 12/12 ok results

**Read First**:
1. `SYSTEM_PRINCIPLES.md`
2. `CURRENT_STATE.md`
3. `OPEN_LOOPS.md` — OL-022 (API key blocker), OL-017 (partial), OL-016 (Mom Test)
4. `docs/ops/ol022_recovery_runbook.md` — OL-022 resolution steps
5. `docs/ops/eval_rerun_checklist.md` — operator checklist for eval rerun
6. `docs/system/factory_layer_preconditions.md` — C1–C4 gate status

**Unknown**: DF-05 (ALT_DATA hallucination), CG-02 (STAT_ARB forbidden behavior), VP-02 (ML_SIGNAL sensitivity test), DF-02, DF-03, CG-04 scores. Railway cron natural trigger unconfirmed (OL-019).

**Human Required**:
- **OL-022**: API key recharge or rotation (blocks 6 eval cases)
- PR merge for `feat/eval-run-01-results`
- Any external outreach (OL-016)
