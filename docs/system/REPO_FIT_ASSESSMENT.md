# REPO_FIT_ASSESSMENT.md

**Purpose**: Assess whether this repo can and should host a PRD-driven autonomous factory layer.
**Date**: 2026-03-25
**Author**: Agent (Session 6)
**Input files read**: CLAUDE.md, CURRENT_STATE.md, SESSION_HANDOFF.md, OPEN_LOOPS.md, DECISIONS.md, docs/system/core_loop.md, docs/system/internal_schema.md, docs/state/product.md, docs/state/engineering.md, docs/state/ops.md, docs/implementation_status.md

---

## 1. What is the repo's current primary purpose?

Give Me a DAY is a **validation-first product for investment strategy research**. Its primary purpose is to convert a user's investment goal into a validated, conditionally recommended strategy direction, then operate it as a Paper Run.

The 12-step internal pipeline is the core:
```
Goal → Frame → Spec → Candidates → Evidence → Validation → Audit → Recommend → Present → Approve → Operate → Re-evaluate
```

The product's defining value is not code generation, not productivity tooling, and not workflow automation. It is: **comparison, rejection, and conditional recommendation under explicit uncertainty**. CLAUDE.md is explicit that drifting toward generic workflow automation — even if commercially broader — weakens the wedge.

The repo currently serves two layered purposes:
1. **Product implementation**: the 12-step pipeline, frontend, execution layer, LLM layer, approval gate, Paper Run runtime
2. **Operational control layer**: daily reports, CI, state architecture, truth layer, eval framework — built to make AI-assisted development reliable and auditable

---

## 2. What major systems already exist?

| System | Status | Location |
|--------|--------|----------|
| 12-step backend pipeline | Implemented, Rounds 1–6.12 complete | `backend/src/pipeline/`, `backend/src/execution/` |
| LLM layer (client + prompts + fallbacks) | Implemented | `backend/src/llm/` |
| React frontend (5 pages) | Implemented | `frontend/src/pages/` |
| Companion AI (T1–T7, CON-01–CON-06) | Implemented (Inferred) | `backend/src/` |
| Daily report pipeline | Working (1 confirmed live run) | `ops/run.sh`, `.github/workflows/daily-report.yml` |
| CI (pr-build.yml) | Green on last verified HEAD | `.github/workflows/pr-build.yml` |
| OpenHands issue→PR loop | E2E confirmed | `.github/workflows/openhands.yml` |
| LLM eval framework | Partial (6/12 cases run) | `evals/`, `docs/evals/`, `scripts/eval_runner.py` |
| State/truth architecture | Operational | `SYSTEM_PRINCIPLES.md`, `DECISIONS.md`, `CURRENT_STATE.md`, `OPEN_LOOPS.md`, `docs/state/*.md` |
| eval-run.yml workflow | Implemented (API key blocked) | `.github/workflows/eval-run.yml` |

The repo has a significant operational layer already. It is not a bare product repo — it has reporting, CI, agent governance, and eval infrastructure.

---

## 3. What is still unresolved?

Ordered by severity:

| Item | Status | Impact |
|------|--------|--------|
| ANTHROPIC_API_KEY credit exhausted (OL-022) | Blocked (human action required) | Blocks remaining 6 eval cases |
| Customer validation — zero interviews (OL-016) | Not started | PMF entirely unknown |
| LLM eval 6/12 cases pending (OL-017) | Partial | ALT_DATA/STAT_ARB quality unverified |
| Railway cron natural trigger (OL-019) | Unconfirmed | Daily reporting reliability unknown |
| No confirmed production deployment | Unknown | Zero live users |
| Backend tests not re-verified post-Round 6.12 changes | Inferred only | Regression risk |
| Legal review for investment product (R-003) | Not done | Regulatory exposure if any user-facing operation |

The repo is pre-PMF and pre-user. Its most critical open loop (OL-016) is a people problem, not a system problem.

---

## 4. Where would a PRD-driven factory layer naturally sit?

A PRD-driven factory layer — one that coordinates dev, eval/QA, and GTM/marketing when a fixed PRD exists — would attach to the repo's existing operational infrastructure rather than its product code.

Natural attachment points, if the layer were added:

| Concern | Proposed location | Collision level |
|---------|-------------------|-----------------|
| PRD document (trigger input) | `docs/prd/` (new) | Low |
| Dev coordination (branch/PR creation) | `.github/workflows/` (new workflows) | Medium |
| Eval/QA coordination | `scripts/` + `evals/` (extend existing) | Medium |
| GTM artifact generation | `docs/marketing/` (new) | Low |
| Factory state tracking | `docs/state/factory.md` (new) | Medium |
| Orchestration script | `ops/factory_run.sh` (new) | High — ops/ is already fragile |

The layer does NOT naturally fit inside `backend/` or `frontend/` — those are product code, not build infrastructure. It does NOT naturally fit inside `docs/system/` — those define the product's internal loop, not the build process.

The conceptually cleanest separation would be a `factory/` directory at repo root containing: PRD schema, coordination workflows, and state tracking. This keeps factory concerns isolated from product concerns.

---

## 5. What must NOT be changed?

These are hard constraints on any factory layer design:

| Item | Why protected |
|------|--------------|
| CLAUDE.md product identity | Defines what the repo is and is not. Broadening language here is explicitly rejected. |
| 12-step core loop (docs/system/core_loop.md) | Defines the product pipeline. Factory coordination must not modify product behavior. |
| Internal schema (docs/system/internal_schema.md) | All product objects defined here. Factory layer must not add objects to this schema. |
| v1 boundary (docs/product/v1_boundary.md) | Explicitly excludes "one-click production orchestration" and "universal deployment infrastructure" — both are adjacent to factory-layer capabilities. |
| D-003 (no direct main push) | All changes via PR. Factory automation must not bypass this. |
| D-004 (no secret values generated/stored) | Factory layer must not handle secrets differently than current policy. |
| State truth hierarchy (SYSTEM_PRINCIPLES.md) | Trust precedence: SYSTEM_PRINCIPLES > DECISIONS > state files > daily reports > SESSION_HANDOFF. Factory layer introduces new state — it must slot into this hierarchy explicitly or it creates conflicting truth. |
| Product non-negotiables in CLAUDE.md | No recommendation without critique, no candidate without assumptions, etc. Factory QA must enforce these, not dilute them. |

---

## 6. What are the top 5 collision risks?

### Risk 1: Identity drift via GTM automation
**Description**: A GTM coordination layer generates marketing artifacts, outreach copy, and external messaging based on a PRD. This is adjacent to — and could easily drift into — the "generic workflow automation" pattern that CLAUDE.md explicitly rejects. If the factory layer's GTM module gets scoped broadly, it repositions the repo as a "build anything and market anything" tool.

**Severity**: High. CLAUDE.md has explicit pushback rules for exactly this pattern. The risk is not theoretical — it is the primary attractor state for any "horizontal AI factory" concept.

**Condition for mitigation**: GTM module must be scoped to "generate marketing artifacts specific to a validated recommendation package." Not "generate marketing for any product." The PRD input must remain investment-validation-domain-specific, or the boundary disappears.

---

### Risk 2: Premature automation before PMF
**Description**: The factory layer assumes there is a stable, validated product worth automating the build and GTM of. Current state: zero live users, zero customer interviews, zero PMF signal (OL-016). Building factory automation before any customer validation inverts the correct order — it automates shipping before confirming what to ship.

**Severity**: High. D-001 explicitly locked the 2-week goal to "minimum loop establishment," not automation expansion. The factory layer is the opposite of minimum.

**Condition for mitigation**: Factory layer must be conditional on OL-016 closing (≥3 Mom Test interviews, findings recorded). No factory design work should land in the repo before this gate.

---

### Risk 3: Eval scope confusion
**Description**: The repo already has an eval framework (OL-017, docs/evals/, eval_runner.py) that evaluates **product LLM quality** — whether DomainFramer, CandidateGenerator, and ValidationPlanner produce usable outputs. A factory layer's "eval/QA" module evaluates **build pipeline quality** — whether the dev process produces shippable features. These are different eval concerns. If they share infrastructure, they will be confused in practice by AI agents working in the repo.

**Severity**: Medium. The eval framework is nascent (6/12 cases, one run). Polluting it with build-pipeline QA concerns at this stage creates technical debt and agent confusion.

**Condition for mitigation**: Factory eval/QA must be strictly namespaced. Separate directory, separate state file, separate rubric. Must explicitly reference product eval as a dependency (factory QA depends on product eval being green) — not a peer.

---

### Risk 4: Ops infrastructure multiplication before baseline confirmed
**Description**: `ops/run.sh` + Railway cron is already fragile — the natural trigger is unconfirmed (OL-019), and the ANTHROPIC_API_KEY is currently exhausted. Adding factory orchestration on top of an unreliable ops baseline multiplies failure modes. A factory_run.sh that depends on ops/run.sh working and eval_runner.py working and GitHub Actions working will fail opaquely when any layer breaks.

**Severity**: Medium. Not a blocker, but a reliability risk. The current ops layer has one confirmed live run. That is not a stable foundation for factory orchestration.

**Condition for mitigation**: OL-019 (Railway cron) and OL-022 (API key) must close before factory orchestration is designed. Factory must have explicit dependency graph on existing ops health.

---

### Risk 5: State truth contamination
**Description**: The current truth architecture (SYSTEM_PRINCIPLES rank 1 → DECISIONS rank 2 → state files rank 3 → daily reports rank 4 → SESSION_HANDOFF rank 5) is deliberately narrow. A factory layer introduces new operational state: PRD versions, factory run history, dev sprint status, GTM campaign state. If this state is not explicitly positioned in the truth hierarchy, AI agents will have conflicting truth sources — product state files say one thing, factory state says another.

**Severity**: Medium-high. The state architecture was built specifically to prevent this. Adding a new state domain without assigning its truth precedence rank creates exactly the problem the architecture was designed to avoid.

**Condition for mitigation**: Factory state must be assigned a truth precedence rank lower than product state files (rank 3) and explicitly documented in SYSTEM_PRINCIPLES.md before the layer is created.

---

## 7. Final judgment: should this repo add such a layer now, later, or not at all?

**Judgment: Later — with four explicit preconditions.**

### Why not "now"

Three reasons this is wrong to build now:

1. **The P1 open loops are people problems, not system problems.** OL-016 (customer validation) and OL-022 (API key) are the highest-priority items. A factory layer solves neither. It adds complexity while the product is still pre-user and the eval baseline is incomplete.

2. **v1_boundary.md explicitly excludes the factory's closest analogues.** "One-click production orchestration" and "universal deployment infrastructure" are both listed as out of scope for v1. A PRD-driven factory that coordinates dev, eval, and GTM is in that excluded space. Adding it now requires re-scoping v1 — and that requires a clear reason beyond "it would be useful someday."

3. **The current risk distribution does not support it.** The top risks are: no live users, unverified LLM quality on 6 archetypes, legal exposure, zero marketing. A factory layer addresses none of these risks and introduces three new ones (identity drift, premature automation, ops multiplication).

### Why not "never"

The factory concept is coherent with the product's deeper thesis. CLAUDE.md states: "The deeper product thesis is to convert AI intelligence into real-world successful outcomes, then improve future outcomes by learning from validation and runtime feedback." A PRD-driven factory layer that coordinates dev, eval, and GTM based on a validated product direction is a natural extension of this thesis — at v2 or later, after the investment validation wedge is proven.

### Conditions for "later"

The factory layer should be re-evaluated when all four of these conditions are met:

| Condition | Current status | Owner |
|-----------|---------------|-------|
| C1: OL-016 closed — ≥3 Mom Test interviews completed, findings recorded | Not started | Haruki |
| C2: OL-017 closed — all 12 eval cases scored, stable LLM quality baseline | 6/12, partial | Agent/Haruki |
| C3: D-001 "minimum loop establishment" goal confirmed achieved and explicitly re-scoped | Not reviewed | Haruki + Agent |
| C4: PRD format designed without touching product scope — factory files in isolated namespace | Not started | Agent (design) |

If all four conditions are met, the next step should be architecture design — specifically a factory layer spec that defines: PRD schema, trigger mechanism, module boundaries (dev / eval / GTM), state namespace, truth precedence assignment, and guardrails against identity drift.

### What should happen next

Not factory layer work. The correct next actions from here:

1. **Haruki**: Resolve OL-022 (API key). Then trigger eval-run.yml to close OL-017.
2. **Haruki**: Start OL-016 (Mom Test interviews). This is the highest-impact remaining open loop.
3. **Agent**: Once OL-017 closes (12/12 eval cases), write a post-eval recommendation update.
4. **Agent + Haruki**: After ≥3 interviews, write the first customer validation findings doc.

Factory layer design is not yet the bottleneck. PMF validation is.

---

**Evidence discipline note**: All judgments in this document are based on Observed or directly Inferred evidence from the files read. No speculative product claims made. Uncertainty about unread files (e.g., docs/product/v1_boundary.md full text, docs/system/execution_layer.md) noted but not blocking — the conclusions are robust to the files read.
