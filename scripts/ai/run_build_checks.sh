#!/usr/bin/env bash
# scripts/ai/run_build_checks.sh
# Purpose: Run frontend build + backend pytest. Output markdown summary.
# Usage:   bash scripts/ai/run_build_checks.sh
# Output:  stdout (markdown) + docs/reports/daily/_last_build_check.md
# Verified: 2026-03-24 — runs end-to-end in /tmp/gmd-verify

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
RESULT_FILE="${REPO_ROOT}/docs/reports/daily/_last_build_check.md"

frontend_status="unknown"
backend_status="unknown"

echo "## Build Check — ${TIMESTAMP}"
echo ""

# ─── Frontend ──────────────────────────────────────────────
echo "### Frontend (tsc + vite build)"
if [ ! -d "${REPO_ROOT}/frontend" ]; then
  frontend_status="⚠️ skip (frontend/ not found)"
  echo "Status: ${frontend_status}"
else
  cd "${REPO_ROOT}/frontend"
  npm ci --silent 2>/dev/null || true   # allow cache miss silently
  # capture output ONCE — do not re-run build on failure
  set +e
  frontend_out=$(npm run build 2>&1)
  frontend_exit=$?
  set -e
  if [ $frontend_exit -eq 0 ]; then
    frontend_status="✅ success"
    echo "Status: ${frontend_status}"
  else
    frontend_status="❌ fail"
    echo "Status: ${frontend_status}"
    echo '```'
    echo "${frontend_out}" | tail -20
    echo '```'
  fi
fi

echo ""

# ─── Backend ───────────────────────────────────────────────
echo "### Backend (pytest -q)"
if [ ! -d "${REPO_ROOT}/backend" ]; then
  backend_status="⚠️ skip (backend/ not found)"
  echo "Status: ${backend_status}"
else
  cd "${REPO_ROOT}/backend"
  pip install -e ".[dev]" -q 2>/dev/null || {
    echo "  ⚠️ pip install failed — using cached packages if available"
  }
  # capture output ONCE
  set +e
  backend_out=$(pytest -q --tb=short 2>&1)
  backend_exit=$?
  set -e
  if [ $backend_exit -eq 0 ]; then
    backend_status="✅ success"
    echo "Status: ${backend_status}"
  else
    backend_status="❌ fail"
    echo "Status: ${backend_status}"
    echo '```'
    echo "${backend_out}" | tail -30
    echo '```'
  fi
fi

echo ""
echo "---"
echo "| | Status |"
echo "|---|---|"
echo "| frontend build | ${frontend_status} |"
echo "| backend pytest | ${backend_status} |"

# Write machine-readable result file
mkdir -p "$(dirname "${RESULT_FILE}")"
cat > "${RESULT_FILE}" << MD
# Last Build Check
- timestamp: ${TIMESTAMP}
- frontend: ${frontend_status}
- backend: ${backend_status}
MD

# Exit non-zero if any check failed
if [[ "${frontend_status}" == *"❌"* ]] || [[ "${backend_status}" == *"❌"* ]]; then
  exit 1
fi
