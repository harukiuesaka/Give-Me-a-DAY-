# Eval Persistence Incident 01

**Date**: 2026-03-25
**Severity**: High — 12/12 eval cases produced no usable output; OL-017 and C2 remain blocked
**Status**: Root cause confirmed. Fix applied (PR, this commit).
**OL ref**: OL-022

---

## Incident Summary

The `eval-run.yml` GitHub Actions workflow ran successfully at the workflow level but produced zero usable LLM eval results. All 12 cases received `api_error`. The DeepSeek migration that was designed to unblock this was committed to the feature branch but missed the PR merge window by 1 second and never reached `main`.

---

## Observed Behavior

| Step | Observation |
|------|-------------|
| Checkout | SHA `b3f61975` (pre-DeepSeek version of eval-run.yml) |
| Run eval | All 12 cases: `API_ERROR: credit balance too low` |
| Result file written | `run_2026-03-25.jsonl` — 12 api_error records (confirmed by `create mode 100644` in commit log) |
| Commit step | Committed as `715d5f6 chore: eval run results 2026-03-25` |
| Push | `b3f6197..715d5f6 main -> main` — **succeeded** |
| Subsequent modification | Commit `9bc6f99` (in-context agent scoring) overwrote the file with 6 ok + 6 api_error |
| DeepSeek migration on main | **ABSENT** — commits pushed 1 second after PR merged |

**Workflow run ID**: `23519099907`
**Run timestamp**: `2026-03-25T00:36:03Z` (09:36 JST)
**Run branch**: `main` at SHA `b3f61975`
**Run conclusion**: `success` (workflow level — masked by `|| true`)

---

## Root Cause

**Primary**: `secrets.ANTHROPIC_API_KEY` credit exhausted. The Anthropic API returned HTTP 400 on every call with `'Your credit balance is too low to access the Anthropic API.'` This affected all 12 eval cases. The error was correctly written to the result file; however zero usable LLM outputs were produced.

**Secondary (contributing)**: The DeepSeek migration that resolves the primary cause was committed to `feat/eval-run-01-results` branch starting at `11:06:55 +0900` — **one second after** the PR was merged at `11:06:54 +0900`. Commits `a211939`, `7c014b7`, `84872c2` are on the feature branch and have never been on `main`. The eval workflow continued to use the exhausted Anthropic key on every subsequent run.

---

## Evidence from Logs

From GitHub Actions run `23519099907`:

```
[DF-01] normal — standard factor strategy ...
API_ERROR: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error',
'message': 'Your credit balance is too low to access the Anthropic API.'}, 'request_id': 'req_011CZNrxc22zM5smUuzYXC8Z'}
```

This pattern repeated for all 12 cases (DF-01 through DF-05, CG-01 through CG-04, VP-01 through VP-03).

```
OK: 0/12
API errors: 12
Written: .../evals/results/run_2026-03-25.jsonl
```

Commit step result:
```
[main 715d5f6] chore: eval run results 2026-03-25
1 file changed, 12 insertions(+)
create mode 100644 evals/results/run_2026-03-25.jsonl

b3f6197..715d5f6  main -> main
```

Git verification — DeepSeek commits not on main:
```
$ git merge-base --is-ancestor 84872c2 HEAD
→ NO — NOT on main

$ git log --oneline origin/feat/eval-run-01-results ^origin/main
84872c2 fix: correct DeepSeek Anthropic-compatible base URL + use ANTHROPIC_API_KEY naming
7c014b7 fix(eval): migrate eval provider from Anthropic to DeepSeek
a211939 fix(eval): OL-022 recovery readiness — runbook, checklist, rerun safety
```

---

## Why Results Were Not Usable

1. **Anthropic API credit exhausted** → all 12 API calls failed → all 12 records `status: api_error`
2. **DeepSeek migration never reached main** → no way to retry with working credentials
3. **Result file was subsequently overwritten** by in-context agent scoring (commit `9bc6f99`), creating a hybrid file: 6 rows from in-context scoring (status `ok`), 6 rows from the workflow run (status `api_error`). The current file is not a clean workflow output.
4. **No same-day rerun protection** in the version of `eval_runner.py` that ran — a retry on the same day would overwrite the only run file without warning.

---

## Fix Applied

This commit applies the 3 unmerged DeepSeek migration commits directly to `main` (cherry-pick was not used due to state file conflicts — direct file copy from `84872c2` used instead):

| File | Change |
|------|--------|
| `scripts/eval_runner.py` | Provider config block added; `LLM_BASE_URL` defaults to `https://api.deepseek.com/anthropic`; `ANTHROPIC_API_KEY` as primary key var; same-day rerun protection; `provider` field in result records |
| `.github/workflows/eval-run.yml` | `ANTHROPIC_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}`; `LLM_BASE_URL: "https://api.deepseek.com/anthropic"`; `LLM_MODEL: deepseek-chat`; `LLM_PROVIDER: deepseek`; "Show results" step added; `git push origin HEAD` (explicit); commit message includes UTC time |
| `docs/ops/ol022_recovery_runbook.md` | Created — runbook for OL-022 resolution and revert path |
| `docs/ops/eval_rerun_checklist.md` | Created — operator checklist for eval rerun |
| `docs/state/engineering.md` | Provider history table + corrected URL column |
| `evals/results/README.md` | Provider field added to schema; score continuity warning |

**The fix does NOT change the current `evals/results/run_2026-03-25.jsonl`.** The 6 in-context ok results are preserved. The next workflow run will use same-day rerun protection and write to `run_2026-03-25_rerunHHMM.jsonl`.

---

## Residual Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `DEEPSEEK_API_KEY` secret not set in GitHub Secrets | High | Operator must confirm before triggering rerun (see checklist) |
| DeepSeek API key invalid/expired | High | Same — check checklist preflight |
| `run_2026-03-25.jsonl` is a hybrid file (in-context + workflow) | Medium | Acknowledged. The next clean workflow run will write a separate `_rerun` file. Future score comparisons should note provider and run method. See `docs/state/engineering.md` provider history table. |
| Same sequence (commit after merge) could recur on future PRs | Low | Operator awareness. Any PR containing eval config changes should be triggered only after merge is confirmed stable. |
| Anthropic API credit could be re-exhausted | Low | DeepSeek migration is the active path. Revert path is documented in runbook §2b. |

---

## Operator Verification Steps

Before triggering the next eval rerun, confirm all of the following:

1. **Secret exists**: GitHub repo → Settings → Secrets and variables → Actions → confirm `DEEPSEEK_API_KEY` is listed
2. **Secret is valid**: The `DEEPSEEK_API_KEY` secret must contain a valid, active DeepSeek API key (not expired, not over quota). Verify at [platform.deepseek.com](https://platform.deepseek.com) → API Keys
3. **Workflow on correct branch**: Trigger `eval-run.yml` via `workflow_dispatch` on `main` branch (not any feature branch)
4. **After run**: Check Actions → `eval-run.yml` → latest run → "Show results" step — confirms provider and per-case status without downloading JSONL
5. **File committed**: Check that a `run_2026-03-25_rerunHHMM.jsonl` file was committed to `evals/results/` on main
6. **Report to agent**: Tell agent "eval rerun committed at HH:MM" → agent scores cases, closes OL-017, updates state

**Success signal**: "Show results" step prints `Provider: deepseek  Model: deepseek-chat` and at least some cases show `ok`.

**Failure signal**: All cases show `api_error` → check the exact error in "Run eval" step output → likely DeepSeek auth failure.
