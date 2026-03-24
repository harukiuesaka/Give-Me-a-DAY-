# ops/RUNBOOK.md — Give Me a DAY Ops Runbook

**Scope**: Activating and operating the daily report generation loop.
**Current PR baseline**: PR #17+ on main.

---

## Prerequisites

| Item | Required? | Source |
|------|-----------|--------|
| Anthropic API key (`ANTHROPIC_API_KEY`) | **REQUIRED** | https://console.anthropic.com/settings/keys |
| OpenRouter API key (`OPENROUTER_API_KEY`) | optional (primary LLM) | https://openrouter.ai/keys |
| GitHub PAT with `repo` scope (`GITHUB_TOKEN`) | optional (git push) | https://github.com/settings/tokens |
| Supabase project URL + service_role key | optional (run logging) | see §4 |
| FRED API key | optional (macro data) | https://fred.stlouisfed.org/docs/api/api_key.html |

**Supabase note**: Free tier allows 2 active projects. If 3 inactive projects exist, delete 1 first.

---

## 1. One-time local setup

```bash
git clone https://github.com/haruki121731-del/Give-Me-a-DAY-.git
cd Give-Me-a-DAY-
cp .env.ops.example .env.ops
# Fill in your keys in .env.ops
nano .env.ops
source .env.ops
```

---

## 2. Activation sequence (run in order)

### Step 1 — Preflight check

```bash
source .env.ops
bash ops/run.sh --check-only
```

**Expected output:**
```
╔══════════════════════════════════════════╗
║   Give Me a DAY — Ops Run               ║
╚══════════════════════════════════════════╝
  ✅ ANTHROPIC_API_KEY  (LLM fallback / backend)
  ✅ scripts/ai/run_build_checks.sh
  ✅ scripts/ai/detect_architecture_drift.sh
  ✅ scripts/ai/detect_marketing_health.sh
  ✅ scripts/ai/generate_daily_report.sh
  ✅ ops/scripts/write_run_state.py

  Preflight: ✅ all checks passed
── CHECK ONLY — done ──────────────────────────────────────
```

**If preflight fails**: see §5 Failure Cases.

---

### Step 2 — Dry-run (no LLM call, no git push)

```bash
bash ops/run.sh --dry-run
```

**Expected output (condensed):**
```
── DATA COLLECTION ─────────────────────────────────────────
  build check...          ✅ done (or ⚠️ non-fatal)
  architecture drift...   ✅ done
  marketing health...     ✅ done
── REPORT GENERATION ──────────────────────────────────────
  [DRY RUN] skipping LLM — writing data-only report
── ARTIFACT VALIDATION ────────────────────────────────────
  ✅ [C2] file exists
  ✅ [C3] size: NNN bytes
  ✅ [C4] not JSON payload
  ✅ [C5] no ERROR: prefix
  ✅ [C6] N section headers found
── SUPABASE WRITE ──────────────────────────────────────────
  SKIPPED (--dry-run)
── GIT COMMIT + PUSH ───────────────────────────────────────
  SKIPPED (--dry-run)
── RUN SUMMARY ─────────────────────────────────────────────
  ✅ Run contract satisfied
```

Dry-run **must pass artifact validation** before proceeding to Step 3.

---

### Step 3 — Live run with skip-commit (verify LLM works)

```bash
bash ops/run.sh --skip-commit
```

**Expected output (additional lines vs dry-run):**
```
── REPORT GENERATION ──────────────────────────────────────
  LLM: Anthropic present
4. Calling LLM...
   ✅ Anthropic API OK
5. Report written: docs/reports/daily/YYYY-MM-DD.md
── ARTIFACT VALIDATION ────────────────────────────────────
  ✅ [C2–C6] all passed
── GIT COMMIT + PUSH ───────────────────────────────────────
  SKIPPED (--skip-commit)
── RUN SUMMARY ─────────────────────────────────────────────
  ✅ Run contract satisfied
```

Inspect the generated report:
```bash
cat docs/reports/daily/$(date +%Y-%m-%d).md
```

---

### Step 4 — Full run (LLM + Supabase + git push)

```bash
bash ops/run.sh
```

**Expected output (additional lines):**
```
── SUPABASE WRITE ──────────────────────────────────────────
  ✅ Supabase write OK
── GIT COMMIT + PUSH ───────────────────────────────────────
  ✅ pushed to main
── RUN SUMMARY ─────────────────────────────────────────────
  ✅ Run contract satisfied
  ✅ ops/run.sh completed (exit 0)
```

---

## 3. Railway cron setup

1. [Railway dashboard](https://railway.app) → New Project → Empty Service
2. Settings → Deploy:
   - **Start Command**: `bash ops/run.sh`
   - **Cron Schedule**: `0 0 * * *` (UTC 00:00 = JST 09:00)
3. Settings → Variables → add all from `.env.ops.example` (required + optional)
4. Manually trigger one run → check logs for `✅ ops/run.sh completed (exit 0)`

**Note on git push from Railway**: `GITHUB_TOKEN` must be a [fine-grained PAT](https://github.com/settings/tokens) with `Contents: Read and Write` on this repo. Classic PAT with `repo` scope also works.

---

## 4. Supabase setup

1. Dashboard → [SQL Editor](https://supabase.com/dashboard) → paste contents of `ops/schemas/run_state_schema.sql` → Run
2. Verify: Table Editor → `run_logs` table exists with correct columns
3. Settings → API:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** (secret key, starts with `eyJ...`) → `SUPABASE_SERVICE_ROLE_KEY`
4. Test write:
   ```bash
   python3 ops/scripts/write_run_state.py \
     --run-id "test_$(date +%s)" \
     --agent-type "daily_report" \
     --status "success" \
     --dry-run
   # Then run again without --dry-run to test live
   ```
5. Verify in Supabase Table Editor: row should appear in `run_logs`

---

## 5. Failure cases and exact fixes

### Preflight: `❌ MISSING: OPENROUTER_API_KEY or ANTHROPIC_API_KEY`

```bash
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY
bash ops/run.sh --check-only
```

---

### Artifact validation: `[C3] report too small`

Cause: LLM failed and data fallback produced fewer than 200 bytes.
Fix: Check LLM key is valid. Run `--dry-run` to confirm data collection works, then `--skip-commit` to test LLM.

---

### Artifact validation: `[C4] report starts with '{'`

Cause: generate_daily_report.sh wrote a JSON error payload to the file.
This should never happen with the current fallback chain.
If it does: check the generate script is the correct version (post-PR #17).

---

### LLM: `⚠️ OpenRouter failed: Insufficient credits`

Fix: Top up credits at https://openrouter.ai/settings/credits
Auto-fallback: if `ANTHROPIC_API_KEY` is set, the run will use it automatically.

---

### LLM: `⚠️ Anthropic API failed`

Check:
- Key is valid: `curl https://api.anthropic.com/v1/messages -H "x-api-key: ${ANTHROPIC_API_KEY}" -H "anthropic-version: 2023-06-01" -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"ping"}]}'`
- Should return `{"type":"message",...}` not `{"error"...}`

---

### Supabase: `ERROR: HTTP 401`

Cause: Using anon key instead of service_role key.
Fix: `SUPABASE_SERVICE_ROLE_KEY` must be the `service_role` key (longer JWT), not the `anon` key.

---

### Supabase: `ERROR: HTTP 404`

Cause: `run_logs` table does not exist.
Fix: Apply `ops/schemas/run_state_schema.sql` via Supabase SQL Editor.

---

### Git push: `⚠️ git push failed`

Non-fatal — report is written locally.
Manual push: `git push origin main`
If in Railway: verify `GITHUB_TOKEN` has `Contents: Write` permission.

---

### Railway: run exits non-zero

Check Railway logs. Common causes:
- `exit 1`: preflight failed → check all env vars are set in Railway Variables
- `exit 3`: artifact validation failed → check LLM key works, run `--skip-commit` locally

---

## 6. Success definition

A daily run is **complete** when:

1. `docs/reports/daily/YYYY-MM-DD.md` exists in the repo (or locally if git push skipped)
2. It contains `## Build`, `## Drift` (or similar), `## Marketing` sections
3. `ops/run.sh` exited 0

Minimum viable: Step 3 (LLM works locally) before Railway automation.

---

## 7. Smoke test commands (copy-paste)

```bash
# 1. Preflight only
bash ops/run.sh --check-only
echo "Exit: $?"   # expect: 0

# 2. Dry run (no LLM, must pass artifact validation)
bash ops/run.sh --dry-run
echo "Exit: $?"   # expect: 0

# 3. Live LLM, no push
bash ops/run.sh --skip-commit
echo "Exit: $?"   # expect: 0
cat docs/reports/daily/$(date +%Y-%m-%d).md | head -20

# 4. Full run
bash ops/run.sh
echo "Exit: $?"   # expect: 0
```
