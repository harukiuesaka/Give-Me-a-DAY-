# docs/state/engineering.md

**Domain**: Engineering
**Last updated**: 2026-03-24
**Truth precedence rank**: 3

---

## Domain Purpose

Maintain the current engineering implementation state: what is built, where it lives, what is working, and what is unresolved.

---

## Current Confirmed State

**Evidence label**: See per-row labels below. Not all items are uniformly Observed.

### Stack
| Layer | Technology | Entry Point | Evidence |
|-------|-----------|-------------|----------|
| Backend | FastAPI 0.104+ / Python 3.11+ / Pydantic v2 | `backend/src/main.py` | Observed (files verified) |
| Frontend | React 18 / TypeScript / Vite / TailwindCSS | `frontend/src/main.tsx` | Observed (files verified) |
| LLM | Anthropic Claude API (`claude-sonnet-4-20250514`) | `backend/src/llm/client.py` | Observed (read `backend/src/llm/client.py` 2026-03-24: `self.model = "claude-sonnet-4-20250514"`) |
| Persistence | In-memory store + Supabase run_logs | `backend/src/persistence/` | Observed (files exist; Supabase write confirmed Run #3) |
| CI | GitHub Actions `pr-build.yml` | `.github/workflows/pr-build.yml` | Observed (CI run 23493826997 green on feat/state-architecture-v1 tip bdb668fa5) |

### Backend pipeline
```
[1] GoalIntake → [2] DomainFramer → [3] ResearchSpecCompiler
→ [4] CandidateGenerator → [5] EvidencePlanner → [6] ValidationPlanner
→ [7] DataAcquisition → [8] BacktestEngine → [9] StatisticalTests
→ [10] ComparisonEngine → [11] AuditEngine → [12] RecommendationEngine
→ PresentationBuilder
```
All 12 steps implemented through Round 6.12. (Observed: files exist. Inferred: no re-run of full test suite after Round 6.12 changes.)

### Confirmed working (with evidence labels)
| Item | Evidence label | Source |
|------|---------------|--------|
| Backend pytest passing | Inferred | Last explicitly verified 2026-03-18; no re-run confirmed since |
| Frontend build dist/ exists | Inferred | Past successful build; not re-triggered on latest HEAD |
| CI `pr-build.yml` triggers on PR | Observed | Run 23493826997: Frontend Build ✅ Backend Tests ✅ |
| LLM model: `claude-sonnet-4-20250514` | Observed | Read `backend/src/llm/client.py` directly 2026-03-24 |
| Companion AI v1 T1–T7 / CON-01–CON-06 | Inferred | Implemented per docs; not independently re-tested post-merge |

### Code-truth locations
| Component | Location |
|-----------|----------|
| Domain models | `backend/src/domain/models.py` |
| Pipeline modules | `backend/src/pipeline/` |
| Execution modules | `backend/src/execution/` |
| Judgment / Audit | `backend/src/judgment/` |
| LLM client + prompts | `backend/src/llm/` |
| Frontend pages | `frontend/src/pages/` |
| Tests | `backend/tests/` |

---

## Current Unknowns

| Unknown | Notes |
|---------|-------|
| Live deployment | No production server confirmed. Railway used for ops cron only |
| Backend tests on current HEAD | `implementation_status.md` last updated 2026-03-18; changes merged post-Round 6.12 not re-verified |
| Frontend tests | No frontend test suite confirmed |
| Real LLM calls in pipeline | Tests use mocks/fallbacks; live LLM quality not validated end-to-end |
| Supabase schema for run_state | `run_state_schema.sql` exists; live migration status unknown |

---

## Related Open Loops

- OL-017: LLM output quality verification — real runs not yet tested

---

## Risks

| Risk | Level | Notes |
|------|-------|-------|
| Backend test regression | Medium | Last verified 2026-03-18; changes since then not re-verified |
| No production deployment | High | Product has no live users |
| LLM API cost at scale | Medium | `claude-sonnet-4-20250514` per-call cost in full pipeline runs |

---

## Architecture Constraints

- Main branch is protected: all changes via PR
- No direct main push by AI agents
- One PR = one judgment unit
- Secrets never hardcoded

## Read Next

- `docs/architecture/current_system.md` — detailed architecture overview
- `docs/architecture/module_map.md` — module responsibility map
- `docs/implementation_status.md` — full round-by-round status
