# CURRENT_STATE.md

**Role**: Parent index. Short overview by domain. Pointer map to detail files.
**Truth precedence rank**: (inherits from `docs/state/*.md` — rank 3)
**Last updated**: 2026-03-25 (Session 6 — DeepSeek eval migration)

For rules and mission: → `SYSTEM_PRINCIPLES.md`
For decisions: → `DECISIONS.md`

---

## System Status Overview

| Domain | State | Detail |
|--------|-------|--------|
| Product | v1 spec complete, backend implemented, no live users | → `docs/state/product.md` |
| Engineering | Rounds 1–6.12 complete, CI green; eval run 01 partial (6/12 Observed, acceptable); eval path migrated to DeepSeek (`deepseek-chat`); rerun pending PR merge | → `docs/state/engineering.md` |
| Ops | ops/run.sh confirmed Run #3; Railway cron natural trigger unconfirmed | → `docs/state/ops.md` |
| Marketing | Internal only, all external channels zero | → `docs/state/marketing.md` |
| Agent Governance | 3 agents defined, guardrails active | → `docs/state/agent_governance.md` |
| Risk | R-001 (no live users), R-003 (legal), R-010 (zero marketing) are top risks | → `docs/state/risk.md` |

---

## Top Blockers / Critical Changes

| # | Item | Owner | State file |
|---|------|-------|------------|
| 1 | OL-022: merge PR #28 + trigger eval-run.yml with DeepSeek | **human (Haruki)** | OL-022 |
| 2 | No live users — PMF entirely unvalidated | human | `docs/state/product.md` |
| 3 | Railway cron: configured, natural trigger unconfirmed | agent detect | `docs/state/ops.md` |
| 4 | Marketing: zero external activity | human | `docs/state/marketing.md` |
| 5 | Legal review: investment product, no review done | human | `docs/state/risk.md` |

---

## Open Loops Summary

All loops: → `OPEN_LOOPS.md`

Currently open:

| ID | Title | Priority | Owner |
|----|-------|----------|-------|
| OL-022 | ANTHROPIC_API_KEY credit exhausted — eval blocked | P1 | **human (Haruki)** |
| OL-017 | LLM eval run 01 partial — 6/12 done, 6 remaining | P1 | agent/human |
| OL-016 | Mom Test / customer validation | P1 | human |
| OL-019 | Railway cron natural trigger confirmation | P2 | agent |

---

## Recent Changes (Session 6 — DeepSeek eval migration)

- `scripts/eval_runner.py`: provider config now env-var driven (`LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`); defaults to DeepSeek via Anthropic-compatible API; `provider` field added to all result records
- `.github/workflows/eval-run.yml`: uses `secrets.deepseekllm` as `LLM_API_KEY`; revert instructions in comments
- `docs/state/engineering.md`: provider history table added; eval provider config section added
- `evals/results/README.md`: `provider` field documented; score continuity warning added
- `docs/ops/ol022_recovery_runbook.md`: updated to reflect DeepSeek resolution path + revert instructions
- `docs/ops/eval_rerun_checklist.md`: preflight updated (no Anthropic key needed)
- OL-022 status updated: migration applied, pending merge + first DeepSeek run
- **Product runtime unchanged**: `backend/src/llm/client.py` still uses `claude-sonnet-4-20250514` (Anthropic-hosted)

## Recent Changes (Session 6 — eval run 01)

- PR #25 (eval package), PR #26/#27 (eval runner) merged to main
- OL-021 closed: eval package delivered and first run executed
- Eval run 01 executed: 6/12 cases scored in-context (claude-sonnet-4-6); 6 cases blocked by ANTHROPIC_API_KEY exhaustion
- Results: DomainFramer 4.6, CandidateGenerator 5.0, ValidationPlanner 4.9 — all **acceptable**
- Recommendation: **A (conditional)** — limited testing permitted on FACTOR archetype inputs
- OL-022 opened: ANTHROPIC_API_KEY credit exhaustion (human action required)
- OL-017 narrowed: partial Observed results recorded; still open for remaining 6 cases
- New files: `evals/results/run_2026-03-25.jsonl`, `evals/results/scores_2026-03-25.csv`, `docs/evals/llm_quality_run_01.md`
- `docs/state/engineering.md` updated with eval run 01 results section

## Recent Changes (Session 5 — eval package)

- PR #23 (state architecture) and PR #24 (grounding audit) merged to main
- OL-020 closed
- LLM eval package added: `docs/evals/llm_quality_eval.md`, `evals/llm_quality_cases.json`, `evals/results/README.md`
- OL-017 upgraded P2 → P1: eval target, rubric, test set, procedure now defined
- OL-021 opened: eval PR merge + first run
- `feat/eval-layer` PR open

## Recent Changes (Session 5 — grounding audit)

- Grounding audit pass: state files corrected for evidence discipline
- `engineering.md`: model name corrected to `claude-sonnet-4-20250514`; Inferred/Observed labels added per-item
- `ops.md`: cron natural trigger relabeled Unknown; Anthropic fallback relabeled Inferred
- OL-018 closed: CI run 23493826997 confirmed green (Frontend Build ✅ + Backend Tests ✅)
- OL-019 narrowed: 10 checked daily-report runs show no schedule event; still open

## Recent Changes (Session 4)

- PR #22 merged: OPEN_LOOPS.md OL-015 added (OpenHands E2E test)
- `openhands.yml` production-cleaned (diagnostic step removed)
- OpenHands issue→PR loop E2E confirmed working
- ANTHROPIC_API_KEY confirmed working with `claude-3-haiku-20240307`

---

## Read Order for AI Context Reconstruction

1. `SYSTEM_PRINCIPLES.md` — rules and mission
2. `CURRENT_STATE.md` — this file (overview)
3. `docs/state/{product,engineering,ops}.md` — domain detail
4. `OPEN_LOOPS.md` — unresolved items
5. `DECISIONS.md` — directional decisions
6. `docs/reports/daily/` latest — daily control
7. `SESSION_HANDOFF.md` — immediate startup context
