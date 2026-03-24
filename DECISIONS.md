# DECISIONS.md

**Role**: Top-level directional decisions only. High-cost reversibility. Major operating and product judgments.
**Truth precedence rank**: 2
**Last updated**: 2026-03-24

Do not add low-level implementation details here.
For domain state, see `docs/state/`. For open items, see `OPEN_LOOPS.md`.

---

## Format
```
| ID | Decision | Reason | Evidence | Risk | Date |
```

---

## Active Decisions

| ID | Decision | Reason | Evidence | Risk | Date |
|----|---------|--------|---------|------|------|
| D-001 | 2-week goal locked to "minimum loop establishment" | Prioritize readable daily build/drift/marketing over full automation | Execution plan v2 §0 | Scope expansion pressure | 2026-03-24 |
| D-002 | OpenHands deferred until repo truth layer established | AI output scatters without grounded repo state | Execution plan v2 §2-2 | Low delay risk (docs needed first) | 2026-03-24 |
| D-003 | No direct main push. All changes via branch/PR | Keep main clean; human holds merge judgment | Rule §1 | Slower development speed; acceptable | 2026-03-24 |
| D-004 | AI never generates, stores, or copies secret values | Security policy. Eliminates leak risk | Rule §7 | Config delays possible | 2026-03-24 |
| D-005 | v1 Paper Run only — no real-money execution | Legal risk mitigation. Real money requires full legal review before implementation | `docs/product/v1_boundary.md` | Product scope is narrow; acceptable | 2026-03-24 |
| D-006 | State architecture refactored to AI-readable domain files | Repo must serve as stable operating context for AI agents | State Architecture Spec v1 | Transition cost; one-time | 2026-03-24 |

---

## Rejected Options

| Rejected | Reason | Date |
|---------|--------|------|
| OpenHands full deployment from Day 1 | Repo truth layer not ready; accuracy degrades without grounded docs | 2026-03-24 |
| Railway persistent agent runtime | Railway cron is for short-lived tasks; not suited for persistent runtime | 2026-03-24 |
| Generic workflow automation as product wedge | Weakens investment validation focus; contradicts CLAUDE.md | 2026-03-24 |
