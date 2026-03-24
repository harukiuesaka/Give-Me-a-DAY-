#!/usr/bin/env python3
"""
ops/scripts/write_run_state.py
Purpose: Supabase の run_logs テーブルに実行結果を insert する最小スクリプト。
Usage: python3 ops/scripts/write_run_state.py \
         --run-id "2026-03-24_daily_report" \
         --agent-type "daily_report" \
         --status "success" \
         --report-path "docs/reports/daily/2026-03-24.md" \
         --build-result "success" \
         --drift-status "none" \
         --marketing-health "weak_signal" \
         --cost-estimate 0.000142
Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError


def main():
    parser = argparse.ArgumentParser(description="Write run state to Supabase")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--agent-type", required=True,
                        choices=["dev_build", "docs_knowledge", "growth_cmo", "daily_report"])
    parser.add_argument("--status", required=True,
                        choices=["running", "success", "fail", "skipped"])
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--build-result", default="unknown",
                        choices=["success", "fail", "skip", "unknown"])
    parser.add_argument("--drift-status", default="unknown",
                        choices=["none", "weak_signal", "concern", "unknown"])
    parser.add_argument("--marketing-health", default="unknown",
                        choices=["none", "weak_signal", "concern", "unknown"])
    parser.add_argument("--cost-estimate", type=float, default=None)
    parser.add_argument("--error-message", default=None)
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        print("ERROR: SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY を環境変数に設定してください。")
        sys.exit(1)

    now = datetime.now(timezone.utc).isoformat()

    payload = {
        "run_id": args.run_id,
        "agent_type": args.agent_type,
        "started_at": now,
        "finished_at": now,
        "status": args.status,
        "report_path": args.report_path,
        "build_result": args.build_result,
        "drift_status": args.drift_status,
        "marketing_health": args.marketing_health,
        "cost_estimate": args.cost_estimate,
        "error_message": args.error_message,
    }

    # None を除去
    payload = {k: v for k, v in payload.items() if v is not None}

    url = f"{supabase_url.rstrip('/')}/rest/v1/run_logs"
    body = json.dumps(payload).encode("utf-8")

    req = Request(url, data=body, method="POST")
    req.add_header("apikey", service_role_key)
    req.add_header("Authorization", f"Bearer {service_role_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=minimal")

    try:
        with urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                print(f"OK: run_id={args.run_id} status={args.status}")
            else:
                print(f"WARNING: HTTP {resp.status}")
    except URLError as e:
        print(f"ERROR: Supabase への書き込みに失敗しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
