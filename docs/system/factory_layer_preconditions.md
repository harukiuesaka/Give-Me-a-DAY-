# factory_layer_preconditions.md

**Purpose**: Track the four explicit preconditions that must be met before factory-layer architecture design is appropriate for this repo.
**Source**: `docs/system/REPO_FIT_ASSESSMENT.md` (2026-03-25) — Section 7.
**Last updated**: 2026-03-25
**Owner**: Agent (tracking) / Haruki (decision)

Do not begin factory-layer architecture work until all four conditions reach status: **met**.

---

## Precondition Summary

| ID | Condition | Status | Owner |
|----|-----------|--------|-------|
| C1 | OL-016 closed — ≥3 Mom Test interviews completed, findings recorded | **unmet** | Haruki |
| C2 | OL-017 closed — all 12 eval cases scored, stable LLM quality baseline | **partially met** | Agent/Haruki |
| C3 | D-001 "minimum loop establishment" goal confirmed achieved and explicitly re-scoped | **unmet** | Haruki + Agent |
| C4 | Factory files designed in isolated namespace without touching product scope | **unmet** | Agent (design, when C1–C3 met) |

---

## C1 — Customer Validation (OL-016)

### Why it matters
The factory layer is meta-infrastructure for shipping and marketing a product. Building that infrastructure before any customer validation signal inverts the correct order. CLAUDE.md's product thesis — "convert AI intelligence into real-world successful outcomes" — requires knowing what "successful outcomes" means to actual users first. A factory layer that automates GTM for an unvalidated product automates shipping the wrong thing faster.

Additionally: Risk 1 in REPO_FIT_ASSESSMENT.md identifies GTM automation as the primary identity-drift vector. Understanding real customer language and priorities is a prerequisite for scoping the factory's GTM module narrowly enough that it doesn't drift into "build anything and market anything."

### What evidence satisfies this condition
- **Minimum**: ≥3 Mom Test interviews completed with target respondents (see `docs/research/mom_test_run_plan.md` for respondent profile)
- Interview notes recorded in `docs/research/mom_test_logs/` per the note-taking template
- Synthesis document written at `docs/research/mom_test_synthesis_01.md`
- At least one of: (a) confirmed pain point matching core product value, (b) confirmed rejection with reason recorded, or (c) discovered adjacent need documented
- Evidence label: Observed (not Inferred — requires actual conversation records)

### Current status: UNMET
No interviews scheduled. No candidate list exists. OL-016 is open with no start date.

### Concrete next action
Haruki creates a target respondent list of ≥10 candidates matching the respondent profile in `docs/research/mom_test_run_plan.md`. Agent drafts outreach copy on request. Haruki initiates contact.

---

## C2 — LLM Quality Baseline (OL-017)

### Why it matters
The factory layer's eval/QA module must assess whether product features meet quality standards before shipping. That assessment requires a stable baseline: what does "acceptable LLM output" look like for this product? Eval run 01 established partial evidence (6/12 cases, all acceptable), but the 6 unrun cases include the highest-risk archetypes: ALT_DATA (DF-05) and STAT_ARB (CG-02). Until these are scored, the quality baseline is incomplete and the QA criterion for "factory-shippable" cannot be defined.

Additionally: Risk 3 in REPO_FIT_ASSESSMENT.md flags eval scope confusion as a medium-severity collision risk. A complete, stable product eval baseline is a prerequisite for cleanly separating it from factory-layer build QA.

### What evidence satisfies this condition
- All 12 cases in `evals/llm_quality_cases.json` scored (status: ok)
- Results recorded in `evals/results/` with Observed label
- Per-module averages updated in `docs/state/engineering.md`
- Recommendation confirmed or revised based on full 12/12 coverage (not just 6/12)
- At least one full `eval-run.yml` workflow_dispatch run producing 12/12 ok results

### Current status: PARTIALLY MET
6/12 cases scored (Observed). Verdict on run cases: acceptable (avg 4.6–5.0). 6 cases blocked (DF-02, DF-03, DF-05, CG-02, CG-04, VP-02). Highest-risk cases (DF-05, CG-02, VP-02) not yet run.

**2026-03-25 update**: DeepSeek migration deployed (PR #28). First DeepSeek rerun triggered. Results NOT persisted to main — root cause UNKNOWN (see OL-022 for detail and next actions). C2 remains PARTIALLY MET.

### Concrete next action
Haruki inspects Actions workflow log for last `eval-run.yml` run → identifies failure cause → confirms `DEEPSEEK_API_KEY` secret is valid → re-triggers `eval-run.yml` on main. Agent scores results and updates engineering.md.

---

## C3 — D-001 Minimum Loop Re-scope

### Why it matters
DECISIONS.md D-001 locked the 2-week goal to "minimum loop establishment" — prioritizing readable daily build/drift/marketing over full automation. A factory layer is the opposite of minimum. Before designing it, D-001 must be explicitly reviewed: is the minimum loop actually established? If not, factory-layer work would consume capacity that the decision log explicitly directed toward baseline stability.

This is also a governance question: adding a factory layer requires re-scoping what this repo is optimizing for. That re-scope should be an explicit, recorded decision (a new entry in DECISIONS.md), not an implicit consequence of starting factory-layer work.

### What evidence satisfies this condition
- Explicit written review of D-001 in DECISIONS.md: either "minimum loop confirmed achieved" with evidence, or "D-001 remains active — factory layer deferred"
- If confirmed achieved: a new DECISIONS.md entry (D-007 or later) explicitly re-scoping the optimization target to include factory layer readiness
- Evidence standard: Observed — requires Haruki's explicit written judgment, not agent inference

Minimum loop is considered established when all of:
1. CI green on main (confirmed, Observed)
2. Daily report pipeline firing reliably (OL-019 must close first)
3. OL-017 closed (eval baseline complete)
4. At least one customer validation signal (C1 minimum)

### Current status: UNMET
D-001 has not been explicitly reviewed. OL-019 (Railway cron natural trigger) remains unconfirmed. OL-017 is partially met. C1 is unmet. The minimum loop is not yet demonstrably established.

### Concrete next action
After C2 (OL-017 closes) and OL-019 confirms natural trigger: Agent writes a D-001 review summary for Haruki's decision. Haruki records verdict in DECISIONS.md.

---

## C4 — Factory Namespace Isolation (Design Gate)

### Why it matters
Risk 5 in REPO_FIT_ASSESSMENT.md identifies state truth contamination as a medium-high risk. The current truth hierarchy (SYSTEM_PRINCIPLES rank 1 → DECISIONS rank 2 → state files rank 3 → daily reports rank 4 → SESSION_HANDOFF rank 5) is deliberately narrow. Factory-layer operational state — PRD versions, sprint status, GTM campaign state — has no assigned rank in this hierarchy. Without explicit positioning and namespace isolation before any factory files are created, AI agents in the repo will have conflicting truth sources.

Additionally: product code in `backend/`, `frontend/`, and `docs/system/` must not be modified to accommodate factory concerns. Isolation must be verifiable by directory structure, not just by intention.

### What evidence satisfies this condition
- Factory layer design document specifying: directory namespace (`factory/` or similar), truth precedence rank assignment (must be lower than product state files, rank 3), and explicit list of files that must not be touched
- Design reviewed and approved by Haruki before any factory files are created
- Factory state file schema defined without overlap with existing state file domains (product, engineering, ops, marketing, agent_governance, risk)

### Current status: UNMET
No factory namespace defined. No truth precedence assignment made. This condition can only be designed after C1–C3 are met — designing the namespace before knowing the product's validated direction would produce a namespace optimized for the wrong product scope.

### Concrete next action
After C1, C2, C3 are met: Agent writes factory layer architecture spec as a candidate for review. Haruki approves or rejects. If approved, namespace is created before any factory files are written.

---

## Readiness Gate

The factory layer architecture design session should not begin until this file records all four conditions as **met**. Haruki should treat this file as the official gate document. Agent should treat any request to begin factory-layer architecture design as requiring a check of this file first.

If any condition is marked **unmet** when architecture design is requested, the agent must surface the unmet condition and recommended next action before proceeding.
