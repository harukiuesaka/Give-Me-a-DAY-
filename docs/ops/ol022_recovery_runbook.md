# OL-022 Recovery Runbook

**Blocker**: ~~ANTHROPIC_API_KEY credit exhaustion~~ → **Resolved by eval provider migration to DeepSeek**
**Priority**: P1 — blocks OL-017, which blocks C2, which blocks factory layer gate
**Owner**: Haruki (trigger eval-run.yml after merging PR with DeepSeek migration)
**Last updated**: 2026-03-25 (updated: eval path migrated to DeepSeek; ANTHROPIC_API_KEY no longer required for eval)

---

## STATUS UPDATE — Provider Migration Applied

The eval pipeline has been migrated from Anthropic-hosted Claude to DeepSeek via the Anthropic-compatible API. The `ANTHROPIC_API_KEY` is **no longer used by `eval-run.yml`**. The workflow now uses `secrets.deepseekllm` as `LLM_API_KEY`.

**OL-022 is resolved when**: PR #28 is merged to main AND `eval-run.yml` is triggered and produces ≥1 ok result using DeepSeek.

The sections below are preserved for historical record and as a revert reference.

---

## 1. Root Cause Summary (historical)

The `ANTHROPIC_API_KEY` stored in GitHub repository Secrets referenced the `for openhands` key in the `Give Me a DAY` Anthropic workspace. As of 2026-03-25, this key had zero credit balance.

Confirmed evidence: `eval-run.yml` GitHub Actions run triggered 2026-03-25 returned HTTP 400 on all 12 eval cases with the message: `Error code: 400 - credit balance too low`.

**Resolution chosen**: Migrate eval path to DeepSeek (cost-effective; `deepseekllm` secret already exists in GitHub Secrets). The `ANTHROPIC_API_KEY` is no longer needed for eval. The product runtime model (`claude-sonnet-4-20250514` in `backend/src/llm/client.py`) is **not changed**.

No other GitHub Actions workflow that calls Anthropic directly is currently used except `eval-run.yml`. The daily report workflow (`daily-report.yml`) uses OpenRouter as primary and Anthropic direct as fallback — OpenRouter is the confirmed working path, so daily reports are unaffected.

---

## 2. Exact Human Action Required (current — DeepSeek path)

**One action only**:

### Verify `deepseekllm` secret exists and is active

1. Go to: [github.com/haruki121731-del/Give-Me-a-DAY-/settings/secrets/actions](https://github.com/haruki121731-del/Give-Me-a-DAY-/settings/secrets/actions)
2. Confirm `deepseekllm` is listed. If it exists, no update is needed — the workflow already maps it to `LLM_API_KEY`.
3. Merge PR #28 (contains `eval-run.yml` and `eval_runner.py` changes).
4. Trigger `eval-run.yml` via workflow_dispatch on `main`.

If `deepseekllm` secret is missing or expired: create a new DeepSeek API key at [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create. Set it as the `deepseekllm` secret value in GitHub Secrets.

**Do not** share the key value in chat, issues, or commit messages. D-004: AI never generates, stores, or copies secret values.

---

## 2b. Revert Path (back to Anthropic-hosted Claude)

If DeepSeek connectivity fails and Anthropic key is recharged, revert by editing `.github/workflows/eval-run.yml` "Run eval" step env block:
```yaml
# Anthropic-hosted revert:
LLM_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
LLM_BASE_URL: ""          # empty string = Anthropic default
LLM_MODEL: "claude-3-haiku-20240307"
LLM_PROVIDER: "anthropic"
```
No change to `eval_runner.py` needed — the env-var config makes it provider-agnostic.

---

## 3. Exact GitHub Locations

| Location | What to check | Required for |
|----------|--------------|-------------|
| GitHub repo → Settings → Secrets → Actions → `deepseekllm` | Confirm exists and is active | eval-run.yml LLM_API_KEY |
| PR #28 | Must be merged to main before triggering | eval-run.yml + eval_runner.py changes |

The `ANTHROPIC_API_KEY` secret is no longer required by `eval-run.yml`. It remains in Secrets for the daily report workflow's Anthropic fallback path — do not delete it.

---

## 4. Post-Update Verification Steps

Before triggering the full eval run, verify the key is working:

**Quick verification** (optional but recommended — saves 15 minutes if the fix didn't work):

Go to GitHub → Actions → `LLM Quality Eval Run` → Run workflow. Alternatively, verify locally if you have CLI access:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"ping"}]}'
```

A successful response contains `"type": "message"`. A failed response contains `"error"` with a credit or auth message.

If verification passes → proceed to Section 5 (trigger workflow).

---

## 5. Exact Workflow to Trigger

1. Go to [github.com/haruki121731-del/Give-Me-a-DAY-/actions/workflows/eval-run.yml](https://github.com/haruki121731-del/Give-Me-a-DAY-/actions/workflows/eval-run.yml)
2. Click **Run workflow** (top right of workflow list)
3. Select branch: **main** (the eval runner and cases are on main)
4. Click **Run workflow** to confirm

The workflow runs on `ubuntu-latest`, installs `anthropic pydantic pydantic-settings`, and calls `scripts/eval_runner.py`.

**Expected runtime**: 2–5 minutes for 12 cases (1 second sleep between cases + API call time for `claude-3-haiku-20240307`).

**Note on same-day rerun**: If triggered on 2026-03-25, `run_2026-03-25.jsonl` already exists with 6 ok records. The updated `eval_runner.py` will detect this and write to `run_2026-03-25_rerunHHMM.jsonl` instead, preserving the original file. If triggered on a later date, it will write `run_YYYY-MM-DD.jsonl` normally.

---

## 6. Expected Success Signals

In the GitHub Actions run log (Actions → run → job → each step):

**"Run eval" step output should show:**
```
=== LLM Eval Run — 2026-03-25 ===
Model: claude-3-haiku-20240307, Temp: 0.3
Cases: 12
Output: .../evals/results/run_2026-03-25_rerunHHMM.jsonl   ← if same day
...
--- DomainFramer ---
  [DF-01] normal — standard factor strategy ... OK (NNNN chars)
  [DF-02] ... OK (NNNN chars)
  ...
=== Summary ===
OK: 12/12
Parse errors: 0
API errors: 0
Other errors: 0
```

**"Show results" step output should show:**
```
=== evals/results/ after run ===
[files listed, including new run file]
=== Latest run file ===
Records: 12
  DF-01: ok
  DF-02: ok
  ...
  VP-03: ok
```

**"Commit results" step output should show:**
```
[main XXXXXXX] chore: eval run results 2026-03-25T...Z
```

**In the repo** (after commit):
- `evals/results/run_2026-03-25_rerunHHMM.jsonl` (or `run_YYYY-MM-DD.jsonl` if new date) — 12 lines, all `"status": "ok"`

---

## 7. Expected Failure Signals

### Failure type A: Same error (credit still low)
```
API_ERROR: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', ...credit balance...}}
```
**Action**: Key was not recharged or rotation not saved correctly. Check Anthropic console billing. Check GitHub Secret was saved (not just edited).

### Failure type B: Auth error (wrong key format or key not active)
```
API_ERROR: Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', ...}}
```
**Action**: New key was copied incorrectly or has a leading/trailing space. Go to GitHub Secrets, delete value and re-paste.

### Failure type C: Model not available
```
API_ERROR: Error code: 404 - model not found
```
**Action**: `claude-3-haiku-20240307` not accessible on this key's plan. Check Anthropic console → API access. Try requesting access or switch `MODEL` in `eval_runner.py` to `claude-haiku-4-5-20251001` (note: this was the model that returned 400 in Session 4 — verify access before using).

### Failure type D: Partial results (some ok, some api_error)
```
OK: 8/12
API errors: 4
```
**Action**: Rate limiting or intermittent failure. Wait 10 minutes and re-trigger. Results file will have a new name (`_rerunHHMM`) and will not overwrite prior partial results.

### Failure type E: Parse errors (api ok but output malformed)
```
OK: 0/12
Parse errors: 12
```
**Action**: LLM responses not in expected JSON format. Check `raw_output` in the JSONL file. This is a prompt issue, not an API key issue. File under OL-017 findings, do not re-trigger.

### Failure type F: Commit step fails / no new file in repo
Check: did `git push origin HEAD` succeed? Verify that `PAT_TOKEN` secret is still valid (used for checkout and push in this workflow). If push fails with auth error, `PAT_TOKEN` may have expired.

---

## 8. Rollback / Retry Path

**The workflow is safe to re-trigger multiple times.** Each re-trigger on the same day creates a new `run_YYYY-MM-DD_rerunHHMM.jsonl` file without overwriting previous results.

**If a run produces unexpected output**: Do not delete the results file. Label it in `evals/results/` with a `README_rerun.md` note explaining why it is anomalous. Agent can assist with this.

**If PAT_TOKEN has expired**: The eval can still run (the "Run eval" and "Show results" steps succeed) but the "Commit results" step will fail. In this case:
1. The run file will not be committed automatically.
2. Haruki must either update `PAT_TOKEN` in GitHub Secrets, or manually download the run artifact from Actions and commit it.

**There is no state to roll back.** The JSONL files are append-safe by convention (new files per run). The existing `run_2026-03-25.jsonl` with 6 ok records is preserved by the same-day collision detection added to `eval_runner.py`.

---

## 9. How This Affects OL-017, C2, and C3

| Loop / Condition | Current status | After OL-022 resolves and eval reruns successfully |
|-----------------|---------------|--------------------------------------------------|
| OL-022 | open (this blocker) | **closed** — API key working, eval unblocked |
| OL-017 | partially met (6/12 cases) | **closeable** — agent scores new cases, updates engineering.md, closes loop |
| C2 (LLM quality baseline) | partially met | **met** — all 12 cases scored with Observed label |
| OL-019 (Railway cron) | unconfirmed | Unaffected — separate concern |
| C3 (D-001 review) | unmet | Prerequisite removed — C3 now depends only on OL-016 and OL-019 |
| C1 (customer validation) | unmet | Unaffected — separate concern |

After a clean 12/12 rerun:
- Agent must: score 6 new cases, update `evals/results/scores_YYYY-MM-DD.csv`, update `docs/state/engineering.md` with full Observed baseline, close OL-017 in OPEN_LOOPS.md
- Factory layer precondition C2 status changes from "partially met" → "met"

---

## 10. Definition of Resolved for OL-022

OL-022 is **resolved** when all of the following are true:

1. `eval-run.yml` workflow dispatch produces at least 1 `ok` result (not `api_error`) for `claude-3-haiku-20240307` in the `Run eval` step
2. Results file committed to `evals/results/` in the repo (visible in commit history)
3. No `credit balance too low` error in the Actions log

OL-022 is **not** resolved by:
- Adding credits without verifying the run
- A partial run where some cases still return api_error (that is OL-017, not OL-022)
- A successful local curl test without a workflow run (workflow execution is the canonical check)
