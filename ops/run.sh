#!/usr/bin/env bash
# ops/run.sh — THE single orchestration entry point for Give Me a DAY ops.
#
# Responsibilities (in order):
#   1. Preflight     — env vars + required files
#   2. Collect       — run sub-scripts, write /tmp/gmd_*.md
#   3. Generate      — call generate_daily_report.sh (LLM → report file)
#   4. Validate      — enforce run contract on the artifact
#   5. Persist       — write run state to Supabase (optional)
#   6. Commit        — git add + commit + push (optional)
#   7. Summary       — print outcome
#
# Usage:
#   bash ops/run.sh                    # full run
#   bash ops/run.sh --dry-run          # no LLM, no Supabase, no git push
#   bash ops/run.sh --check-only       # preflight only, exit 0 if clean
#   bash ops/run.sh --skip-commit      # run + Supabase, skip git push
#
# Env (required — at least one):
#   OPENROUTER_API_KEY           LLM via OpenRouter
#   ANTHROPIC_API_KEY            LLM via Anthropic direct API
#
# Env (optional):
#   SUPABASE_URL                 Enables run state logging to Supabase
#   SUPABASE_SERVICE_ROLE_KEY    Required if SUPABASE_URL is set
#   GITHUB_TOKEN                 Enables git commit + push of report
#   FRED_API_KEY                 Enables macro data collection
#
# Run contract — a run is SUCCESS (exit 0) iff ALL of:
#   [C1] Preflight passed
#   [C2] Report file exists at docs/reports/daily/YYYY-MM-DD.md
#   [C3] Report size >= 200 bytes
#   [C4] Report does not start with '{' (JSON error payload)
#   [C5] Report first line does not start with 'ERROR:'
#   [C6] Report contains >= 2 markdown '## ' section headers
# Optional steps (Supabase write, git push) do not affect the contract.
# A non-zero exit from an optional step is logged as WARNING, not failure.
#
# Exit codes:
#   0  run contract satisfied
#   1  preflight failed (missing required env or files)
#   2  generate_daily_report.sh returned non-zero
#   3  artifact validation failed (contract C2–C6 violated)
#   4  unexpected error (ERR trap)

set -euo pipefail
trap 'echo ""; echo "❌ ops/run.sh: unexpected error at line ${LINENO}"; exit 4' ERR

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE=$(date -u +"%Y-%m-%d")
REPORT_PATH="${REPO_ROOT}/docs/reports/daily/${DATE}.md"
DRY_RUN=false
CHECK_ONLY=false
SKIP_COMMIT=false

for arg in "$@"; do
  case $arg in
    --dry-run)     DRY_RUN=true ;;
    --check-only)  CHECK_ONLY=true ;;
    --skip-commit) SKIP_COMMIT=true ;;
  esac
done

echo "╔══════════════════════════════════════════╗"
echo "║   Give Me a DAY — Ops Run               ║"
echo "╚══════════════════════════════════════════╝"
echo "repo:  ${REPO_ROOT}"
echo "date:  $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "mode:  dry_run=${DRY_RUN}  check_only=${CHECK_ONLY}  skip_commit=${SKIP_COMMIT}"
echo ""

# ══════════════════════════════════════════════════════════════════════
# STEP 1: PREFLIGHT
# ══════════════════════════════════════════════════════════════════════
echo "── PREFLIGHT ──────────────────────────────────────────────"
PREFLIGHT_OK=true

check_env() {
  local var="$1" label="$2" required="${3:-false}"
  if [ -n "${!var:-}" ]; then
    echo "  ✅ ${var} (${label})"
  elif [ "${required}" = "true" ]; then
    echo "  ❌ MISSING: ${var} — ${label}"
    PREFLIGHT_OK=false
  else
    echo "  ⚠️  ${var} — optional: ${label} — disabled"
  fi
}

# LLM key: at least one required
if [ -n "${OPENROUTER_API_KEY:-}" ] || [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  [ -n "${OPENROUTER_API_KEY:-}" ] && echo "  ✅ OPENROUTER_API_KEY (LLM primary)"
  [ -n "${ANTHROPIC_API_KEY:-}" ]  && echo "  ✅ ANTHROPIC_API_KEY  (LLM fallback / backend)"
else
  echo "  ❌ MISSING: OPENROUTER_API_KEY or ANTHROPIC_API_KEY (at least one required)"
  PREFLIGHT_OK=false
fi

check_env "SUPABASE_URL"              "run state logging — write to Supabase"   false
check_env "SUPABASE_SERVICE_ROLE_KEY" "run state logging — Supabase auth"       false
check_env "GITHUB_TOKEN"              "git push report back to repo"            false
check_env "FRED_API_KEY"              "FRED macro data collection"              false

# Required script files
REQUIRED_SCRIPTS=(
  "scripts/ai/run_build_checks.sh"
  "scripts/ai/detect_architecture_drift.sh"
  "scripts/ai/detect_marketing_health.sh"
  "scripts/ai/generate_daily_report.sh"
  "ops/scripts/write_run_state.py"
)
for f in "${REQUIRED_SCRIPTS[@]}"; do
  if [ -f "${REPO_ROOT}/${f}" ]; then
    echo "  ✅ ${f}"
  else
    echo "  ❌ MISSING FILE: ${f}"
    PREFLIGHT_OK=false
  fi
done

if [ "${PREFLIGHT_OK}" = false ]; then
  echo ""
  echo "❌ Preflight failed. See above."
  echo "   Reference: .env.ops.example"
  exit 1
fi

echo ""
echo "  Preflight: ✅ all checks passed"

if [ "${CHECK_ONLY}" = true ]; then
  echo ""
  echo "── CHECK ONLY — done ──────────────────────────────────────"
  exit 0
fi

# ══════════════════════════════════════════════════════════════════════
# STEP 2: DATA COLLECTION
# (sub-scripts write to /tmp/gmd_*.md + docs/reports/daily/_last_*.md)
# ══════════════════════════════════════════════════════════════════════
echo ""
echo "── DATA COLLECTION ────────────────────────────────────────"

collect() {
  local script_name="$1"
  local out_file="$2"
  local label="$3"
  echo "  ${label}..."
  # Non-zero exit from sub-scripts is a WARNING, not a failure.
  # The report will contain whatever data was collected.
  set +e
  bash "${REPO_ROOT}/scripts/ai/${script_name}" > "${out_file}" 2>&1
  local exit_code=$?
  set -e
  if [ $exit_code -eq 0 ]; then
    echo "    ✅ done"
  else
    echo "    ⚠️ returned exit ${exit_code} (non-fatal — data captured)"
    echo "    last 3 lines:" && tail -3 "${out_file}" | sed 's/^/      /'
  fi
}

collect "run_build_checks.sh"          "/tmp/gmd_build.md"     "build check"
collect "detect_architecture_drift.sh" "/tmp/gmd_drift.md"     "architecture drift"
collect "detect_marketing_health.sh"   "/tmp/gmd_marketing.md" "marketing health"

# ══════════════════════════════════════════════════════════════════════
# STEP 3: REPORT GENERATION (LLM → file)
# Responsibility: generate_daily_report.sh
# Outputs: REPORT_PATH + /tmp/gmd_meta/{build,drift,marketing}_status
# ══════════════════════════════════════════════════════════════════════
echo ""
echo "── REPORT GENERATION ──────────────────────────────────────"

GENERATE_ARGS=""
[ "${DRY_RUN}" = true ] && GENERATE_ARGS="${GENERATE_ARGS} --dry-run"

if ! bash "${REPO_ROOT}/scripts/ai/generate_daily_report.sh" ${GENERATE_ARGS}; then
  echo ""
  echo "❌ generate_daily_report.sh returned non-zero."
  exit 2
fi

# ══════════════════════════════════════════════════════════════════════
# STEP 4: ARTIFACT VALIDATION (run contract C2–C6)
# A run is only successful if the artifact passes all checks below.
# Validation happens BEFORE any downstream action (Supabase, git).
# ══════════════════════════════════════════════════════════════════════
echo ""
echo "── ARTIFACT VALIDATION ────────────────────────────────────"

VALIDATION_FAIL=""
MIN_BYTES=200

# C2: file must exist
if [ ! -f "${REPORT_PATH}" ]; then
  VALIDATION_FAIL="[C2] report file not found: ${REPORT_PATH}"
fi

if [ -z "${VALIDATION_FAIL}" ]; then
  ARTIFACT_SIZE=$(wc -c < "${REPORT_PATH}" | tr -d ' ')

  # C3: minimum size
  if [ "${ARTIFACT_SIZE}" -lt "${MIN_BYTES}" ]; then
    VALIDATION_FAIL="[C3] report too small: ${ARTIFACT_SIZE} bytes (minimum ${MIN_BYTES})"
  fi
fi

if [ -z "${VALIDATION_FAIL}" ]; then
  FIRST_CHAR=$(head -c1 "${REPORT_PATH}" 2>/dev/null || echo "")
  # C4: not a JSON error payload
  if [ "${FIRST_CHAR}" = "{" ]; then
    VALIDATION_FAIL="[C4] report starts with '{' — likely a JSON error payload"
  fi
fi

if [ -z "${VALIDATION_FAIL}" ]; then
  FIRST_LINE=$(head -1 "${REPORT_PATH}" 2>/dev/null || echo "")
  # C5: not an ERROR: prefix
  case "${FIRST_LINE}" in
    ERROR:*) VALIDATION_FAIL="[C5] report first line starts with 'ERROR:'" ;;
  esac
fi

if [ -z "${VALIDATION_FAIL}" ]; then
  SECTION_COUNT=$(grep -c "^## " "${REPORT_PATH}" 2>/dev/null || echo 0)
  # C6: minimum section headers
  if [ "${SECTION_COUNT}" -lt 2 ]; then
    VALIDATION_FAIL="[C6] too few ## sections: ${SECTION_COUNT} (minimum 2)"
  fi
fi

if [ -n "${VALIDATION_FAIL}" ]; then
  echo "  ❌ VALIDATION FAILED: ${VALIDATION_FAIL}"
  echo "  Report path: ${REPORT_PATH}"
  echo "  First 10 lines:"
  head -10 "${REPORT_PATH}" 2>/dev/null | sed 's/^/    /' || echo "    (unreadable)"
  echo ""
  echo "❌ Run contract violated. Aborting — no Supabase write, no git push."
  exit 3
fi

echo "  ✅ [C2] file exists: ${REPORT_PATH}"
echo "  ✅ [C3] size: ${ARTIFACT_SIZE} bytes"
echo "  ✅ [C4] not JSON payload"
echo "  ✅ [C5] no ERROR: prefix"
echo "  ✅ [C6] ${SECTION_COUNT} section headers found"
echo ""
echo "  First 5 lines of report:"
head -5 "${REPORT_PATH}" | sed 's/^/    /'

# ══════════════════════════════════════════════════════════════════════
# STEP 5: SUPABASE WRITE (optional)
# Skipped in --dry-run. Non-zero is WARNING, not failure.
# ══════════════════════════════════════════════════════════════════════
echo ""
echo "── SUPABASE WRITE ─────────────────────────────────────────"

if [ "${DRY_RUN}" = true ]; then
  echo "  SKIPPED (--dry-run)"
elif [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  echo "  SKIPPED (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set)"
else
  BUILD_TOKEN=$(cat /tmp/gmd_meta/build_status     2>/dev/null || echo "unknown")
  DRIFT_TOKEN=$(cat /tmp/gmd_meta/drift_status     2>/dev/null || echo "unknown")
  MKTG_TOKEN=$(cat /tmp/gmd_meta/marketing_status  2>/dev/null || echo "unknown")

  set +e
  python3 "${REPO_ROOT}/ops/scripts/write_run_state.py" \
    --run-id "${DATE}_daily_report" \
    --agent-type "daily_report" \
    --status "success" \
    --report-path "docs/reports/daily/${DATE}.md" \
    --build-result "${BUILD_TOKEN}" \
    --drift-status "${DRIFT_TOKEN}" \
    --marketing-health "${MKTG_TOKEN}"
  SUPA_EXIT=$?
  set -e

  if [ ${SUPA_EXIT} -eq 0 ]; then
    echo "  ✅ Supabase write OK"
  else
    echo "  ⚠️ Supabase write failed (exit ${SUPA_EXIT}) — non-fatal"
  fi
fi

# ══════════════════════════════════════════════════════════════════════
# STEP 6: GIT COMMIT + PUSH (optional)
# Skipped in --dry-run and --skip-commit.
# Uses GITHUB_TOKEN injected into remote URL — does not modify .git/config.
# Non-zero is WARNING, not failure.
# ══════════════════════════════════════════════════════════════════════
echo ""
echo "── GIT COMMIT + PUSH ──────────────────────────────────────"

if [ "${DRY_RUN}" = true ]; then
  echo "  SKIPPED (--dry-run)"
elif [ "${SKIP_COMMIT}" = true ]; then
  echo "  SKIPPED (--skip-commit)"
elif [ ! -d "${REPO_ROOT}/.git" ]; then
  echo "  SKIPPED (.git directory not found)"
elif [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "  SKIPPED (GITHUB_TOKEN not set)"
else
  cd "${REPO_ROOT}"
  git config user.email "agent@give-me-a-day.ai" 2>/dev/null || true
  git config user.name  "Docs Agent"              2>/dev/null || true

  # Stage: daily report + last-check sidecars
  git add "docs/reports/daily/${DATE}.md"                  2>/dev/null || true
  git add "docs/reports/daily/_last_build_check.md"        2>/dev/null || true
  git add "docs/reports/daily/_last_drift_check.md"        2>/dev/null || true
  git add "docs/reports/daily/_last_marketing_check.md"    2>/dev/null || true

  if git diff --cached --quiet 2>/dev/null; then
    echo "  nothing to commit (already up to date)"
  else
    # Inject token into remote URL for push — does not permanently change config
    REMOTE_URL=$(git remote get-url origin 2>/dev/null \
                 || echo "https://github.com/haruki121731-del/Give-Me-a-DAY-.git")
    REMOTE_WITH_TOKEN=$(echo "${REMOTE_URL}" | sed "s|https://|https://${GITHUB_TOKEN}@|")

    set +e
    git commit -m "report: daily ${DATE} [agent]" 2>/dev/null
    git push "${REMOTE_WITH_TOKEN}" HEAD:main      2>/dev/null
    PUSH_EXIT=$?
    set -e

    if [ ${PUSH_EXIT} -eq 0 ]; then
      echo "  ✅ pushed to main"
    else
      echo "  ⚠️ git push failed (exit ${PUSH_EXIT}) — report exists locally"
      echo "     Manual push: git push origin main"
    fi
  fi
fi

# ══════════════════════════════════════════════════════════════════════
# STEP 7: RUN SUMMARY
# ══════════════════════════════════════════════════════════════════════
echo ""
echo "── RUN SUMMARY ────────────────────────────────────────────"
echo "  ✅ Run contract satisfied"
echo "  Date:   ${DATE}"
echo "  Report: ${REPORT_PATH}"
echo "  Size:   ${ARTIFACT_SIZE} bytes"
echo ""
echo "  ✅ ops/run.sh completed (exit 0)"
exit 0
