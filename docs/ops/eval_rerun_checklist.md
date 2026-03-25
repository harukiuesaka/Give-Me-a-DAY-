# eval_rerun_checklist.md

**Purpose**: Operator checklist for re-triggering the LLM quality eval run after OL-022 is resolved.
**Audience**: Haruki
**Last updated**: 2026-03-25
**Full runbook**: `docs/ops/ol022_recovery_runbook.md`

---

## Preflight checklist

Before triggering the run, confirm:

- [ ] PR #28 (`feat/eval-run-01-results`) has been merged to main — contains the DeepSeek migration for `eval_runner.py` and `eval-run.yml`
- [ ] `DEEPSEEK_API_KEY` secret exists in GitHub Secrets (Settings → Secrets and variables → Actions)
- [ ] Branch to trigger is **main** (workflow reads `DEEPSEEK_API_KEY` from main branch workflow file)

Note: `ANTHROPIC_API_KEY` is **no longer required** for eval runs. The eval path now uses `DEEPSEEK_API_KEY` → `LLM_API_KEY` → DeepSeek API. If any item is unchecked, do not trigger the run yet.

---

## Exact rerun steps

1. Go to: `https://github.com/haruki121731-del/Give-Me-a-DAY-/actions/workflows/eval-run.yml`
2. Click **Run workflow**
3. Branch: **main**
4. Click **Run workflow** (confirm)
5. Wait 2–5 minutes

---

## What to inspect in Actions

After the run completes, click into the run and check each step:

**Step: "Run eval"**
Look for:
```
OK: 12/12
API errors: 0
```
If you see `API errors: N > 0`, check the error detail printed below the summary. The first api_error is printed in full.

**Step: "Show results"**
Look for:
```
Records: 12
  DF-01: ok
  DF-02: ok
  ...
  VP-03: ok
```
Every case should show `ok`. If any show `api_error`, OL-022 is not fully resolved.

**Step: "Commit results"**
Look for:
```
[main XXXXXXX] chore: eval run results 2026-03-25T...Z
```
If you see `"No new results to commit"`: the run file was not written — check the "Run eval" step for errors.
If you see a git push error: `PAT_TOKEN` may have expired (see runbook §7, Failure type F).

---

## Where results should appear in the repo

After a successful run + commit:

| File | What it contains |
|------|-----------------|
| `evals/results/run_YYYY-MM-DD.jsonl` | Raw outputs, 12 lines, all `"status": "ok"` |
| *(if same-day rerun)* `evals/results/run_2026-03-25_rerunHHMM.jsonl` | Same, with timestamp suffix |

The commit will appear in the `main` branch history as `chore: eval run results YYYY-MM-DDTHH:MM:SSZ`.

After verifying these files exist in the repo: tell the agent. Agent will score the new cases, update `evals/results/scores_YYYY-MM-DD.csv`, and close OL-017.

---

## What to do if the rerun partially fails

| Scenario | Action |
|----------|--------|
| Some cases `api_error`, some `ok` | Re-trigger. New results file gets `_rerunHHMM` suffix — original preserved. |
| All cases `api_error` (credit still low) | Return to runbook §2. Credits may not have applied immediately. Wait 5 minutes and retry. |
| Run file not committed (commit step failed) | Check `PAT_TOKEN` in GitHub Secrets. If expired, update it. If the file exists in Actions artifacts, download and commit manually. |
| Parse errors on some cases | Do NOT re-trigger. This is a prompt/model quality issue, not an API key issue. Record the parse errors in OPEN_LOOPS.md and notify agent. |
| Workflow doesn't appear / can't trigger | Confirm `eval-run.yml` is on `main` branch. Go to Actions tab and confirm the workflow is listed. If not, PR #28 may not be merged yet. |

---

## When OL-017 can be considered advanced vs closed

**Advanced** (partial progress, not closed):
- Run produces 7–11 ok results (improvement over 6/12 baseline)
- Agent scores new cases, updates engineering.md with partial Observed data
- OL-017 status stays "in_progress"

**Closed** (full closure):
- Run produces 12/12 ok results
- Agent scores all 6 new cases
- Per-module averages updated in `docs/state/engineering.md` with Observed label
- Recommendation confirmed or revised (A/B/C) based on full 12/12 coverage
- OPEN_LOOPS.md updated: OL-017 moved to Closed Loops archive
- `docs/system/factory_layer_preconditions.md` C2 updated from "partially met" → "met"

After telling the agent that the run is complete, the agent handles all scoring and state updates.
