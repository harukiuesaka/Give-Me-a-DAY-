#!/usr/bin/env bash
# scripts/ai/run_build_checks.sh
# Purpose: Run build and test checks. Output markdown summary.
# Usage: bash scripts/ai/run_build_checks.sh
# Called by: GitHub Actions, Railway cron, manual AI session

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
RESULT_FILE="${REPO_ROOT}/docs/reports/daily/_last_build_check.md"

frontend_status="unknown"
backend_status="unknown"
frontend_log=""
backend_log=""

echo "## Build Check — ${TIMESTAMP}"
echo ""

# --- Frontend ---
echo "### Frontend (tsc + vite build)"
if [ -d "${REPO_ROOT}/frontend" ]; then
  cd "${REPO_ROOT}/frontend"
  if npm ci --silent 2>/dev/null && npm run build 2>&1; then
    frontend_status="✅ success"
    echo "Status: ${frontend_status}"
  else
    frontend_status="❌ fail"
    frontend_log=$(npm run build 2>&1 | tail -20 || true)
    echo "Status: ${frontend_status}"
    echo "\`\`\`"
    echo "${frontend_log}"
    echo "\`\`\`"
  fi
else
  frontend_status="⚠️ skip (frontend/ not found)"
  echo "Status: ${frontend_status}"
fi

echo ""

# --- Backend ---
echo "### Backend (pytest -q)"
if [ -d "${REPO_ROOT}/backend" ]; then
  cd "${REPO_ROOT}/backend"
  if pip install -e ".[dev]" -q 2>/dev/null && pytest -q --tb=short 2>&1; then
    backend_status="✅ success"
    echo "Status: ${backend_status}"
  else
    backend_status="❌ fail"
    backend_log=$(pytest -q --tb=short 2>&1 | tail -30 || true)
    echo "Status: ${backend_status}"
    echo "\`\`\`"
    echo "${backend_log}"
    echo "\`\`\`"
  fi
else
  backend_status="⚠️ skip (backend/ not found)"
  echo "Status: ${backend_status}"
fi

echo ""
echo "---"
echo "| | Status |"
echo "|---|---|"
echo "| frontend build | ${frontend_status} |"
echo "| backend pytest | ${backend_status} |"

# Write result to file for daily report ingestion
mkdir -p "$(dirname "${RESULT_FILE}")"
cat > "${RESULT_FILE}" <<MD
# Last Build Check
- timestamp: ${TIMESTAMP}
- frontend: ${frontend_status}
- backend: ${backend_status}
MD
