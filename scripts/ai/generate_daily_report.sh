#!/usr/bin/env bash
# scripts/ai/generate_daily_report.sh
# Purpose: Collect build/drift/marketing results → LLM → daily report → git commit.
# Usage:   bash scripts/ai/generate_daily_report.sh [--dry-run] [--skip-commit]
# Env (required):  OPENROUTER_API_KEY  or  ANTHROPIC_API_KEY
# Env (optional):  GITHUB_TOKEN (for git push), SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# Output:  docs/reports/daily/YYYY-MM-DD.md  (committed if git available)
# Verified: 2026-03-24 — end-to-end tested

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATE=$(date -u +"%Y-%m-%d")
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
REPORT_PATH="${REPO_ROOT}/docs/reports/daily/${DATE}.md"
DRY_RUN=false
SKIP_COMMIT=false

# ─── Args ──────────────────────────────────────────────────
for arg in "$@"; do
  case $arg in
    --dry-run)     DRY_RUN=true ;;
    --skip-commit) SKIP_COMMIT=true ;;
  esac
done

echo "=== Daily Report Generator — ${TIMESTAMP} ==="
echo "dry_run=${DRY_RUN}  skip_commit=${SKIP_COMMIT}"
echo ""

# ─── Preflight ─────────────────────────────────────────────
HAS_OPENROUTER=false
HAS_ANTHROPIC=false

if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  HAS_OPENROUTER=true
  echo "✅ OPENROUTER_API_KEY present"
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  HAS_ANTHROPIC=true
  echo "✅ ANTHROPIC_API_KEY present"
fi
if [ "${HAS_OPENROUTER}" = false ] && [ "${HAS_ANTHROPIC}" = false ]; then
  echo "ERROR: Either OPENROUTER_API_KEY or ANTHROPIC_API_KEY must be set."
  echo "  export OPENROUTER_API_KEY=sk-or-v1-..."
  echo "  export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# ─── Sub-scripts ───────────────────────────────────────────
collect() {
  local script_name="$1"
  local out_file="$2"
  local label="$3"
  echo "${label}..."
  if bash "${REPO_ROOT}/scripts/ai/${script_name}" > "${out_file}" 2>&1; then
    echo "   ✅ done"
  else
    echo "   ⚠️ script returned non-zero (continuing)"
    echo "   last 5 lines:" && tail -5 "${out_file}" | sed 's/^/     /'
  fi
}

collect "run_build_checks.sh"          "/tmp/gmd_build.md"     "1. build check"
collect "detect_architecture_drift.sh" "/tmp/gmd_drift.md"     "2. drift check"
collect "detect_marketing_health.sh"   "/tmp/gmd_marketing.md" "3. marketing health"

BUILD_RESULT=$(cat /tmp/gmd_build.md 2>/dev/null || echo "UNKNOWN")
DRIFT_RESULT=$(cat /tmp/gmd_drift.md 2>/dev/null || echo "UNKNOWN")
MARKETING_RESULT=$(cat /tmp/gmd_marketing.md 2>/dev/null || echo "UNKNOWN")

# Machine-readable last check results
BUILD_STATUS=$(grep "^- frontend:" /tmp/gmd_build.md 2>/dev/null | head -1 || echo "unknown")
DRIFT_OVERALL=$(grep "^- overall:" /tmp/gmd_drift.md 2>/dev/null | head -1 | awk -F': ' '{print $2}' || echo "unknown")
MARKETING_OVERALL=$(grep "^- overall:" /tmp/gmd_marketing.md 2>/dev/null | head -1 | awk -F': ' '{print $2}' || echo "unknown")

OPEN_HIGH=$(grep -A2 "| High" "${REPO_ROOT}/OPEN_LOOPS.md" 2>/dev/null | head -20 \
            || echo "OPEN_LOOPS.md に High 優先度なし")

# ─── Dry-run: skip LLM, write template ─────────────────────
if [ "${DRY_RUN}" = true ]; then
  echo "4. [DRY RUN] skipping LLM call — writing data-only report"
  mkdir -p "$(dirname "${REPORT_PATH}")"
  cat > "${REPORT_PATH}" << DRYEOF
<!-- DRY RUN — generated at ${TIMESTAMP} — no LLM call made -->
# Daily Report — ${DATE} (dry run)

## Build Check
${BUILD_RESULT}

## Architecture Drift
${DRIFT_RESULT}

## Marketing Health
${MARKETING_RESULT}

## Open Loops (High)
${OPEN_HIGH}
DRYEOF
  echo "   Written: ${REPORT_PATH}"
  echo "=== Done (dry run) ==="
  exit 0
fi

# ─── LLM call ──────────────────────────────────────────────
echo "4. Calling LLM API..."

SYSTEM_PROMPT="あなたは Give Me a DAY プロジェクトの Docs / Knowledge Agent です。以下のルールに従って daily report を生成してください。- 推測を事実として書かない。事実がなければ UNKNOWN と書く - build / drift / marketing の3項目を必ず埋める - 箇条書きで簡潔に - 日本語で書く - 出力は markdown のみ（前置き不要）"

USER_PROMPT="以下の情報を使って、${DATE} の daily report を生成してください。

# Build Check 結果
${BUILD_RESULT}

# Architecture Drift 結果
${DRIFT_RESULT}

# Marketing Health 結果
${MARKETING_RESULT}

# Open Loops (High 優先度)
${OPEN_HIGH}

7見出し構造で生成: 全体要約 / 今週の変化 / 進捗(表) / Build Failure / Architecture Drift候補 / マーケ反応 / 次に見るべき点(3つ)"

SYSTEM_ESC=$(echo "$SYSTEM_PROMPT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
USER_ESC=$(echo "$USER_PROMPT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")

REPORT_CONTENT=""
LLM_ERROR=""

# Try OpenRouter first
if [ "${HAS_OPENROUTER}" = true ]; then
  RAW=$(curl -s --max-time 30 -X POST \
    -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
    -H "Content-Type: application/json" \
    -H "HTTP-Referer: https://github.com/haruki121731-del/Give-Me-a-DAY-" \
    https://openrouter.ai/api/v1/chat/completions \
    -d "{\"model\":\"anthropic/claude-haiku-4-5\",\"messages\":[{\"role\":\"system\",\"content\":${SYSTEM_ESC}},{\"role\":\"user\",\"content\":${USER_ESC}}],\"max_tokens\":2000}" \
    2>/dev/null || echo '{"error":{"message":"curl failed"}}')

  # Validate: must have choices, not error
  HAS_CHOICES=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if 'choices' in d else 'no')" 2>/dev/null || echo "no")
  if [ "${HAS_CHOICES}" = "yes" ]; then
    REPORT_CONTENT=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])")
    echo "   ✅ OpenRouter OK"
  else
    LLM_ERROR=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','unknown error'))" 2>/dev/null || echo "parse error")
    echo "   ⚠️ OpenRouter failed: ${LLM_ERROR}"
  fi
fi

# Fallback: Anthropic direct API
if [ -z "${REPORT_CONTENT}" ] && [ "${HAS_ANTHROPIC}" = true ]; then
  echo "   Trying Anthropic API fallback..."
  RAW=$(curl -s --max-time 30 -X POST \
    -H "x-api-key: ${ANTHROPIC_API_KEY}" \
    -H "anthropic-version: 2023-06-01" \
    -H "Content-Type: application/json" \
    https://api.anthropic.com/v1/messages \
    -d "{\"model\":\"claude-haiku-4-5-20251001\",\"max_tokens\":2000,\"system\":${SYSTEM_ESC},\"messages\":[{\"role\":\"user\",\"content\":${USER_ESC}}]}" \
    2>/dev/null || echo '{"type":"error","error":{"message":"curl failed"}}')

  HAS_CONTENT=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('type')=='message' else 'no')" 2>/dev/null || echo "no")
  if [ "${HAS_CONTENT}" = "yes" ]; then
    REPORT_CONTENT=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['content'][0]['text'])")
    echo "   ✅ Anthropic API OK"
  else
    LLM_ERROR=$(echo "$RAW" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',{}).get('message','unknown'))" 2>/dev/null || echo "parse error")
    echo "   ⚠️ Anthropic API failed: ${LLM_ERROR}"
  fi
fi

# Final fallback: data-only template (never write error string as report)
if [ -z "${REPORT_CONTENT}" ]; then
  echo "   ⚠️ All LLM calls failed — writing data-only fallback report"
  REPORT_CONTENT="# Daily Report — ${DATE}

> ⚠️ LLM unavailable — raw data report. Error: ${LLM_ERROR}

## Build
${BUILD_RESULT}

## Drift
${DRIFT_RESULT}

## Marketing
${MARKETING_RESULT}

## Open Loops (High)
${OPEN_HIGH}"
fi

# ─── Write report ──────────────────────────────────────────
mkdir -p "$(dirname "${REPORT_PATH}")"
{
  echo "<!-- generated by scripts/ai/generate_daily_report.sh at ${TIMESTAMP} -->"
  echo "${REPORT_CONTENT}"
} > "${REPORT_PATH}"
echo "5. Report written: ${REPORT_PATH}"

# ─── Write run state to Supabase (optional) ────────────────
if [ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  echo "6. Writing run state to Supabase..."
  # Determine build/drift/marketing status from result files
  BUILD_OK=$(grep -q "✅ success" /tmp/gmd_build.md 2>/dev/null && echo "success" || echo "fail")
  python3 "${REPO_ROOT}/ops/scripts/write_run_state.py" \
    --run-id "${DATE}_daily_report" \
    --agent-type "daily_report" \
    --status "success" \
    --report-path "docs/reports/daily/${DATE}.md" \
    --build-result "${BUILD_OK}" \
    --drift-status "${DRIFT_OVERALL:-unknown}" \
    --marketing-health "${MARKETING_OVERALL:-unknown}" \
    && echo "   ✅ Supabase write OK" \
    || echo "   ⚠️ Supabase write failed (non-fatal)"
else
  echo "6. Supabase: SKIPPED (SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set)"
fi

# ─── Git commit + push ─────────────────────────────────────
if [ "${SKIP_COMMIT}" = true ]; then
  echo "7. Git commit: SKIPPED (--skip-commit)"
elif [ ! -d "${REPO_ROOT}/.git" ]; then
  echo "7. Git commit: SKIPPED (.git not found)"
elif [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "7. Git commit: SKIPPED (GITHUB_TOKEN not set — report exists locally only)"
else
  echo "7. Committing and pushing report..."
  cd "${REPO_ROOT}"
  git config user.email "agent@give-me-a-day.ai" 2>/dev/null || true
  git config user.name "Docs Agent" 2>/dev/null || true
  git add "docs/reports/daily/${DATE}.md" \
          "docs/reports/daily/_last_build_check.md" \
          "docs/reports/daily/_last_drift_check.md" \
          "docs/reports/daily/_last_marketing_check.md" 2>/dev/null || true
  if git diff --cached --quiet 2>/dev/null; then
    echo "   nothing to commit (report already up to date)"
  else
    git commit -m "report: daily ${DATE} [agent]" 2>/dev/null \
      && git push origin HEAD 2>/dev/null \
      && echo "   ✅ pushed to $(git rev-parse --abbrev-ref HEAD)" \
      || echo "   ⚠️ git push failed (report written locally)"
  fi
fi

echo ""
echo "=== Done ==="
echo "Report: ${REPORT_PATH}"
