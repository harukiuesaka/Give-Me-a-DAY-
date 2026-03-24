# docs/state/risk.md

**Domain**: Risk
**Last updated**: 2026-03-24
**Truth precedence rank**: 3

---

## Domain Purpose

Enumerate current risks across product, engineering, operations, and agent execution.
Track trigger conditions, impact, owner, and whether human approval is mandatory.

---

## Current Confirmed State

**Evidence label**: Observed (from repo structure, ops logs, product spec)

### Risk Register

| ID | Risk | Domain | Level | Trigger | Impact | Owner | Human Approval Required |
|----|------|--------|-------|---------|--------|-------|------------------------|
| R-001 | No live users / no PMF signal | Product | High | Ongoing | Product direction is unvalidated | human | Yes (product pivot decisions) |
| R-002 | LLM API dependency for pipeline quality | Engineering | High | LLM degradation or outage | Full pipeline quality degrades | agent monitor | No (fallback exists) |
| R-003 | Real-money operation without legal review | Product | Critical | Any real-money feature request | Legal exposure | human | Yes — mandatory |
| R-004 | Railway cron silent failure | Ops | Medium | Natural trigger not yet observed | Daily reports stop generating | agent detect | No (agent can detect and alert) |
| R-005 | Secrets exposed in PR or commit | Security | Critical | Any accidental hardcode | Credential compromise | human | Yes — mandatory |
| R-006 | v1 scope creep into generic automation | Product | Medium | Feature requests that broaden wedge | Weakens investment validation focus | human | Yes (product direction decisions) |
| R-007 | Architecture drift undetected | Engineering | Medium | `detect_architecture_drift.sh` flagging drift | Implementation diverges from spec | agent detect | No (agent can open loop) |
| R-008 | ANTHROPIC_API_KEY billing issue recurrence | Ops | Medium | API returns 400 credit error | OpenHands and report generation fail | human | Yes (billing decisions) |
| R-009 | CI regression on unreviewed PR | Engineering | Medium | PR merged without passing CI | Breaking change reaches main | PR gate | No (CI blocks merge) |
| R-010 | Marketing signal = zero forever | Marketing | High | No external activity | No user feedback, no PMF data | human | Yes (channel launch decisions) |

---

## Current Unknowns

| Unknown | Notes |
|---------|-------|
| Supabase free tier headroom | 1 write confirmed; ongoing capacity not monitored |
| OpenRouter billing rate | FRED data + LLM per run cost not calculated |
| Legal status of investment product | No legal review has occurred |

---

## Related Open Loops

- OL-016: Mom Test / customer validation — R-001, R-010
- OL-019: Railway cron confirmation — R-004

---

## Mitigation Boundaries

| Risk | Current Mitigation | Boundary |
|------|-------------------|----------|
| R-002 | Three-tier fallback (OpenRouter → Anthropic → template) | Template always produces valid output |
| R-003 | v1 is Paper Run only; no real-money code implemented | Do not implement real-money features without legal review |
| R-004 | `detect_marketing_health.sh` in daily report pipeline | Agent can detect; human decides response |
| R-005 | `.env.example` only; secrets via GitHub Secrets | Never commit real secrets |
| R-007 | `detect_architecture_drift.sh` runs daily | Opens loop in `OPEN_LOOPS.md`; human reviews |

## Read Next

- `SYSTEM_PRINCIPLES.md` — non-negotiables and human approval boundaries
- `docs/state/ops.md` — operational failure modes
- `docs/state/product.md` — product risk context
