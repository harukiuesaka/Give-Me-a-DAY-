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
| LLM quality on ALT_DATA/STAT_ARB archetypes | Eval run 01 covered FACTOR + rejection constraint + blocking gap only (6/12 cases). DF-05 (ALT_DATA hallucination), CG-02, VP-02 not yet run due to API key credit exhaustion |
| LLM quality on haiku model | All 6 run cases used claude-sonnet-4-6. haiku runs blocked by API key. haiku/sonnet quality gap is Unknown |
| Supabase schema for run_state | `run_state_schema.sql` exists; live migration status unknown |

---

## Related Open Loops

- OL-017: LLM quality — 6/12 cases run (Observed); 6 cases pending API key fix

---

## Risks

| Risk | Level | Notes |
|------|-------|-------|
| Backend test regression | Medium | Last verified 2026-03-18; changes since then not re-verified |
| No production deployment | High | Product has no live users |
| LLM API cost at scale | Medium | `claude-sonnet-4-20250514` per-call cost in full pipeline runs |

---

## LLM Quality Eval — Provider History

| Date | Provider | Model | Cases | Trigger |
|------|----------|-------|-------|---------|
| 2026-03-25 | deepseek (in-context) | claude-sonnet-4-6 | 6/12 ok | Manual (API key blocked) |
| next run | deepseek | deepseek-chat | 12/12 (expected) | workflow_dispatch |

**Score continuity note**: Run 01 (in-context, claude-sonnet-4-6) and future runs (deepseek-chat via Anthropic-compatible API) are different providers. Scores should not be compared directly across provider boundaries without noting the provider field in the JSONL record.

## LLM Quality Eval — Run 01 Results (Observed: 2026-03-25)

**Coverage**: 6/12 cases. Provider: deepseek (in-context), model: claude-sonnet-4-6. Remaining 6 unrun — eval pipeline now migrated to DeepSeek (`deepseek-chat`); next run uses `DEEPSEEK_API_KEY` GitHub Secret.

| Module | Cases Run | Avg Score | Verdict |
|--------|-----------|-----------|---------|
| DomainFramer | 2/5 (DF-01, DF-04) | 4.6 | acceptable |
| CandidateGenerator | 2/4 (CG-01, CG-03) | 5.0 | acceptable |
| ValidationPlanner | 2/3 (VP-01, VP-03) | 4.9 | acceptable |

**Strongest output**: VP-01 — all failure_conditions contain numeric thresholds. D3=5.
**Weakest dimension observed**: D3 on DF-04 (vague input) = 3, justified by absent input specificity.
**No `not_ready` or `internal_only` verdict triggered on any run case.**

Full results: `evals/results/run_2026-03-25.jsonl`, `evals/results/scores_2026-03-25.csv`, `docs/evals/llm_quality_run_01.md`

**Unresolved**: DF-05 (ALT_DATA hallucination risk), CG-02 (STAT_ARB forbidden behavior), VP-02 (ML_SIGNAL sensitivity test). Do not expose ALT_DATA or STAT_ARB goals to users until these are scored.

## Eval Provider Config (current)

| Param | Value | Override via |
|-------|-------|-------------|
| Provider | deepseek | `LLM_PROVIDER` env var |
| Base URL | https://api.deepseek.com/anthropic | `LLM_BASE_URL` env var |
| Model | deepseek-chat | `LLM_MODEL` env var |
| API key env var | `ANTHROPIC_API_KEY` (Anthropic SDK naming; wired from `DEEPSEEK_API_KEY` GitHub Secret) | workflow env block |
| Revert to Anthropic | Set `LLM_BASE_URL=` (empty), `LLM_MODEL=claude-3-haiku-20240307`, `ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}` | Workflow env block |

**Product runtime model is unchanged**: `backend/src/llm/client.py` still uses `claude-sonnet-4-20250514` (Anthropic-hosted). Only the eval path changed.

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
