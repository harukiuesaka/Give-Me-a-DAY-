#!/usr/bin/env bash
# scripts/ai/detect_architecture_drift.sh
# Purpose: docs/architecture/current_system.md vs 実際の repo 構造を比較し、
#          drift 候補を markdown で出力する。
# Usage: bash scripts/ai/detect_architecture_drift.sh
# Output: stdout (markdown) + docs/reports/daily/_last_drift_check.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
ARCH_DOC="${REPO_ROOT}/docs/architecture/current_system.md"
RESULT_FILE="${REPO_ROOT}/docs/reports/daily/_last_drift_check.md"

echo "## Architecture Drift Check — ${TIMESTAMP}"
echo ""

# --- 既知のモジュール（current_system.md で定義済み） ---
KNOWN_BACKEND_MODULES=(
  "api" "companion" "domain" "execution" "judgment" "llm" "persistence" "pipeline" "reporting"
)
KNOWN_FRONTEND_PAGES=(
  "ApprovalPage.tsx" "InputPage.tsx" "LoadingPage.tsx" "PresentationPage.tsx" "StatusPage.tsx"
)
KNOWN_SCRIPTS=(
  "run_build_checks.sh" "generate_daily_report.sh" "detect_architecture_drift.sh" "detect_marketing_health.sh"
)

drift_count=0
drift_items=""

# --- Backend modules ---
echo "### Backend Modules"
if [ -d "${REPO_ROOT}/backend/src" ]; then
  for mod in "${KNOWN_BACKEND_MODULES[@]}"; do
    if [ ! -d "${REPO_ROOT}/backend/src/${mod}" ]; then
      echo "- ⚠️ concern: docs に ${mod}/ があるが実装に見つからない"
      drift_items="${drift_items}\n| concern | backend/${mod}/ が docs に記載されているが実装に見つからない |"
      drift_count=$((drift_count + 1))
    fi
  done

  # docs にない新規モジュールを検出
  for actual_mod in "${REPO_ROOT}/backend/src"/*/; do
    mod_name=$(basename "$actual_mod")
    found=false
    for known in "${KNOWN_BACKEND_MODULES[@]}"; do
      [ "$known" = "$mod_name" ] && found=true && break
    done
    if [ "$found" = false ] && [ "$mod_name" != "__pycache__" ]; then
      echo "- ℹ️ weak signal: ${mod_name}/ が実装にあるが docs/architecture に記載なし"
      drift_items="${drift_items}\n| weak signal | backend/${mod_name}/ が実装にあるが current_system.md 未記載 |"
      drift_count=$((drift_count + 1))
    fi
  done
  echo "  → backend scan 完了"
else
  echo "  ⚠️ backend/src/ が見つからない"
fi

echo ""

# --- Frontend pages ---
echo "### Frontend Pages"
if [ -d "${REPO_ROOT}/frontend/src/pages" ]; then
  for page in "${KNOWN_FRONTEND_PAGES[@]}"; do
    if [ ! -f "${REPO_ROOT}/frontend/src/pages/${page}" ]; then
      echo "- ⚠️ concern: docs に ${page} があるが実装に見つからない"
      drift_items="${drift_items}\n| concern | frontend/pages/${page} が docs に記載されているが実装に見つからない |"
      drift_count=$((drift_count + 1))
    fi
  done

  # docs にない新規ページを検出
  for actual_page in "${REPO_ROOT}/frontend/src/pages"/*.tsx; do
    page_name=$(basename "$actual_page")
    found=false
    for known in "${KNOWN_FRONTEND_PAGES[@]}"; do
      [ "$known" = "$page_name" ] && found=true && break
    done
    if [ "$found" = false ]; then
      echo "- ℹ️ weak signal: ${page_name} が実装にあるが docs/architecture に記載なし"
      drift_items="${drift_items}\n| weak signal | frontend/pages/${page_name} が実装にあるが current_system.md 未記載 |"
      drift_count=$((drift_count + 1))
    fi
  done
  echo "  → frontend scan 完了"
else
  echo "  ⚠️ frontend/src/pages/ が見つからない"
fi

echo ""

# --- Scripts/ai ---
echo "### AI Scripts"
for script in "${KNOWN_SCRIPTS[@]}"; do
  if [ ! -f "${REPO_ROOT}/scripts/ai/${script}" ]; then
    echo "- ℹ️ weak signal: ${script} が docs に記載されているが未実装"
    drift_items="${drift_items}\n| weak signal | scripts/ai/${script} が docs に記載されているが未実装 |"
    drift_count=$((drift_count + 1))
  fi
done
echo "  → scripts scan 完了"

echo ""

# --- Stub modules (known stubs that should stay stubs) ---
echo "### Stub Modules"
STUB_MODULES=(
  "backend/src/reporting/__init__.py"
  "backend/src/judgment/audit_patterns/__init__.py"
  "backend/src/execution/paper_run/__init__.py"
)
for stub in "${STUB_MODULES[@]}"; do
  stub_dir=$(dirname "${REPO_ROOT}/${stub}")
  if [ -d "$stub_dir" ]; then
    file_count=$(find "$stub_dir" -name "*.py" | wc -l)
    if [ "$file_count" -gt 1 ]; then
      echo "- ℹ️ weak signal: ${stub} のディレクトリに新規ファイルが追加された可能性 (${file_count} .py files)"
      drift_items="${drift_items}\n| weak signal | ${stub} stub ディレクトリに新規 .py が追加された (${file_count} files) |"
      drift_count=$((drift_count + 1))
    else
      echo "  ✅ ${stub} — stub のまま（変化なし）"
    fi
  fi
done

echo ""
echo "---"
echo ""

# Summary
if [ "$drift_count" -eq 0 ]; then
  echo "### Result: ✅ no drift detected"
  overall="none"
else
  echo "### Result: ${drift_count} drift candidate(s) found"
  overall="weak signal"
  echo ""
  echo "| 分類 | 内容 |"
  echo "|-----|------|"
  echo -e "${drift_items}"
fi

# Write result file
mkdir -p "$(dirname "${RESULT_FILE}")"
cat > "${RESULT_FILE}" <<MD
# Last Drift Check
- timestamp: ${TIMESTAMP}
- drift_count: ${drift_count}
- overall: ${overall}
MD

