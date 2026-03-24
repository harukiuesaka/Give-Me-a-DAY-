# docs/state/agent_governance.md

**Domain**: Agent Governance
**Last updated**: 2026-03-24
**Truth precedence rank**: 3

---

## Domain Purpose

Define agent roles, write permissions, human approval boundaries, forbidden actions, and escalation paths.
This file governs all AI agent behavior in this repository.

For top-level rules, see `SYSTEM_PRINCIPLES.md` (rank 1).

---

## Current Confirmed State

**Evidence label**: Observed (from `docs/agents/ownership.md`, `docs/agents/guardrails.md`)

### Agent Roster

#### Agent 1: Dev / Build Agent
| Property | Value |
|----------|-------|
| Read scope | `backend/src/`, `frontend/src/`, `backend/tests/`, `scripts/` |
| Write scope | `scripts/ai/`, `backend/src/` (small fixes only), `docs/changes/` — via PR only |
| Permitted | Build error fix PR, test failure fix PR, script improvement PR, build check execution |
| Forbidden | Direct main push, auto-merge, large refactors without approval, new external libraries without approval |
| Success condition | Frontend build green, backend pytest green, PR human-reviewable |

#### Agent 2: Docs / Knowledge Agent
| Property | Value |
|----------|-------|
| Read scope | `docs/` all, `backend/src/`, `frontend/src/`, `CURRENT_STATE.md`, `OPEN_LOOPS.md` |
| Write scope | `docs/state/`, `docs/architecture/`, `docs/reports/`, `docs/changes/`, `CURRENT_STATE.md`, `OPEN_LOOPS.md`, `SESSION_HANDOFF.md` — via PR only |
| Permitted | Architecture docs update PR, daily report generation, drift candidate listing, state file updates |
| Forbidden | Direct main push, application code changes, blending facts with inference in docs |
| Success condition | Docs consistent with implementation, daily report generated, drift candidates in OPEN_LOOPS.md |

#### Agent 3: Growth / CMO Agent
| Property | Value |
|----------|-------|
| Read scope | `docs/marketing/logs/`, `docs/marketing/weekly_kpi/`, `docs/reports/daily/` |
| Write scope | `docs/marketing/logs/`, `docs/marketing/weekly_kpi/`, `docs/state/marketing.md` — via PR only |
| Permitted | Activity log aggregation, KPI weekly summary, marketing health classification |
| Forbidden | Causation claims without data, direct main push, any external posting without human approval |
| Success condition | Marketing health classified (`none`/`weak signal`/`concern`), daily report marketing section populated |

---

## Current Unknowns

| Unknown | Notes |
|---------|-------|
| Agent 1 last run | No confirmed Dev Agent run in current session records |
| Agent 3 activation | Growth agent not yet activated; marketing external channels not launched |

---

## Absolute Prohibitions (All Agents)

| Prohibition | Reason |
|------------|--------|
| `main` direct push | Human must hold merge judgment |
| Auto-merge | PRs require human review |
| New paid service signup | Billing decisions are human-only |
| API key for new service | Secret management is human-only |
| Secrets exposed or hardcoded | Security policy |
| Production environment unauthorized change | Human confirmation required |
| Privilege escalation / IAM change | Human approval mandatory |
| Data deletion (DB or files) | Irreversible; human confirmation required |

---

## Pre-Execution Checklist (All Agents)

Before executing any action, verify:
1. Can this be submitted as a branch/PR? If not, do not execute.
2. Is this a single PR-sized change? If too large, split.
3. Are facts and inferences distinguished? Use Observed / Inferred / Unknown labels.
4. Are unknowns marked as UNKNOWN, not filled with guesses?
5. Can a human review the resulting diff?

---

## Escalation Path

If an agent encounters ambiguity on a human-required decision:
1. Stop the action
2. Document the decision point in the relevant state file or PR description
3. Label it `Human Approval Needed`
4. Wait for human input before proceeding

---

## Related Open Loops

None currently open in agent governance domain.

## Read Next

- `SYSTEM_PRINCIPLES.md` — top-level authority and non-negotiables
- `docs/agents/guardrails.md` — full guardrail list
- `docs/agents/ownership.md` — agent ownership details
