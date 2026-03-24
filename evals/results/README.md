# evals/results/

This directory stores all LLM quality evaluation run outputs.

**Managed by**: agent (writes) + human (reviews)
**Do not commit**: raw API keys, personally identifiable information, or large binary files.

---

## File Naming Convention

| File | Contents |
|------|----------|
| `run_YYYY-MM-DD.jsonl` | Raw LLM outputs, one JSON line per case |
| `scores_YYYY-MM-DD.csv` | Dimension scores per case for that run |
| `summary_YYYY-MM-DD.md` | Human-readable summary of that run's findings |

---

## `run_YYYY-MM-DD.jsonl` format

One JSON object per line. Each object:

```json
{
  "run_date": "2026-03-24",
  "case_id": "DF-01",
  "module": "DomainFramer",
  "scenario_label": "normal — standard factor strategy",
  "model": "claude-sonnet-4-20250514",
  "temperature": 0.3,
  "prompt_version": "1.0",
  "raw_output": { ... }
}
```

`raw_output` is the direct LLM response, parsed as JSON if `call_json` was used, else the raw string.

---

## `scores_YYYY-MM-DD.csv` format

```
run_date,case_id,module,D1_structural,D2_instruction,D3_falsifiability,D4_relevance,D5_diversity,D6_nonhallucination,average,verdict,notes
2026-03-24,DF-01,DomainFramer,5,4,3,4,N/A,4,4.0,acceptable,"D3: one claim vague but operationalizable"
```

- `N/A` for dimensions not applicable to the module (D5 is CandidateGenerator-only)
- `verdict`: `not_ready` | `internal_only` | `acceptable` | `ready`
- `notes`: free text, ≤ 200 chars

---

## Verdicts mapping (from eval rubric)

| Verdict | Condition |
|---------|-----------|
| `not_ready` | Any D1 = fail, OR any dimension ≤ 2 |
| `internal_only` | All dimensions ≥ 3, average 2.5–3.9 |
| `acceptable` | All dimensions ≥ 3, average ≥ 4.0 |
| `ready` | All dimensions ≥ 4, average ≥ 4.5 |

---

## First run expectations

**Expected**: at least 1 `not_ready` or `internal_only` verdict per module.
**Goal of first run**: locate worst failure modes, not confirm quality.
**After first run**: update `docs/state/engineering.md` with Observed evidence labels and scores.

---

## No results yet

No eval runs have been executed as of 2026-03-24.
First run is the next step after this eval package is merged.
See `docs/evals/llm_quality_eval.md` for full procedure.
