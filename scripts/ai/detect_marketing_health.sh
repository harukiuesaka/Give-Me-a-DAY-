#!/usr/bin/env bash
# scripts/ai/detect_marketing_health.sh
# Purpose: docs/marketing/ を読み、マーケ反応の健全性を none/weak signal/concern で分類する。
# Usage: bash scripts/ai/detect_marketing_health.sh
# Output: stdout (markdown) + docs/reports/daily/_last_marketing_check.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
LOGS_DIR="${REPO_ROOT}/docs/marketing/logs"
KPI_DIR="${REPO_ROOT}/docs/marketing/weekly_kpi"
RESULT_FILE="${REPO_ROOT}/docs/reports/daily/_last_marketing_check.md"

echo "## Marketing Health Check — ${TIMESTAMP}"
echo ""

overall="none"

# --- ログ存在チェック ---
echo "### Log Coverage"
log_count=0
if [ -d "$LOGS_DIR" ]; then
  log_count=$(find "$LOGS_DIR" -name "*.md" ! -name "index.md" ! -name "_template.md" | wc -l)
fi

if [ "$log_count" -eq 0 ]; then
  echo "- ⚠️ concern: 施策ログが 0 件。Growth/CMO Agent の入力がない。"
  overall="concern"
elif [ "$log_count" -lt 3 ]; then
  echo "- ℹ️ weak signal: 施策ログが ${log_count} 件のみ。サンプルが少ない。"
  overall="weak signal"
else
  echo "- ✅ 施策ログ: ${log_count} 件"
fi

# --- KPI 存在チェック ---
echo ""
echo "### KPI Coverage"
kpi_count=0
if [ -d "$KPI_DIR" ]; then
  kpi_count=$(find "$KPI_DIR" -name "*.md" ! -name "index.md" ! -name "_template.md" | wc -l)
fi

if [ "$kpi_count" -eq 0 ]; then
  echo "- ⚠️ concern: KPI週報が 0 件。数値ベースの判断ができない。"
  [ "$overall" != "concern" ] && overall="concern"
else
  echo "- ✅ KPI週報: ${kpi_count} 件"
fi

# --- 最新ログの鮮度チェック ---
echo ""
echo "### Log Freshness"
if [ "$log_count" -gt 0 ]; then
  latest_log=$(find "$LOGS_DIR" -name "*.md" ! -name "index.md" ! -name "_template.md" | sort | tail -1)
  latest_date=$(basename "$latest_log" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1 || echo "UNKNOWN")
  today=$(date -u +"%Y-%m-%d")
  
  if [ "$latest_date" = "UNKNOWN" ]; then
    echo "- ℹ️ weak signal: 最新ログの日付が読み取れない"
    [ "$overall" = "none" ] && overall="weak signal"
  else
    # 7日以上更新なしチェック
    days_since=$(python3 -c "from datetime import datetime; print((datetime.strptime('${today}','%Y-%m-%d') - datetime.strptime('${latest_date}','%Y-%m-%d')).days)" 2>/dev/null || echo "UNKNOWN")
    if [ "$days_since" = "UNKNOWN" ]; then
      echo "- ℹ️ weak signal: ログの鮮度計算不可"
    elif [ "$days_since" -ge 7 ]; then
      echo "- ⚠️ concern: 最新ログが ${days_since} 日前 (${latest_date})。施策が止まっている可能性。"
      overall="concern"
    elif [ "$days_since" -ge 3 ]; then
      echo "- ℹ️ weak signal: 最新ログが ${days_since} 日前 (${latest_date})。"
      [ "$overall" = "none" ] && overall="weak signal"
    else
      echo "- ✅ 最新ログ: ${latest_date} (${days_since} 日前)"
    fi
  fi
else
  echo "- UNKNOWN: ログなし"
fi

echo ""
echo "---"
echo "### Overall: ${overall}"

# Write result file
mkdir -p "$(dirname "${RESULT_FILE}")"
cat > "${RESULT_FILE}" <<MD
# Last Marketing Health Check
- timestamp: ${TIMESTAMP}
- log_count: ${log_count}
- kpi_count: ${kpi_count}
- overall: ${overall}
MD

