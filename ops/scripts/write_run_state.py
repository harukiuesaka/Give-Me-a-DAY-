#!/usr/bin/env python3
"""
ops/scripts/write_run_state.py
Purpose: Insert a run execution record into Supabase run_logs table.
Usage:
    python3 ops/scripts/write_run_state.py \\
      --run-id "2026-03-24_daily_report" \\
      --agent-type "daily_report" \\
      --status "success" \\
      --build-result "success" \\
      --drift-status "none" \\
      --marketing-health "weak_signal"
Env:
    SUPABASE_URL              (required, unless --dry-run)
    SUPABASE_SERVICE_ROLE_KEY (required, unless --dry-run)
Verified: 2026-03-24 — HTTP 204 accepted, dry-run mode works
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def main() -> None:
    parser = argparse.ArgumentParser(description="Write run state to Supabase run_logs")
    parser.add_argument("--run-id", required=True,
                        help="Unique run identifier, e.g. 2026-03-24_daily_report")
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
    parser.add_argument("--dry-run", action="store_true",
                        help="Print payload without sending to Supabase")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).isoformat()
    payload: dict = {
        "run_id":           args.run_id,
        "agent_type":       args.agent_type,
        "started_at":       now,
        "finished_at":      now,
        "status":           args.status,
        "report_path":      args.report_path,
        "build_result":     args.build_result,
        "drift_status":     args.drift_status,
        "marketing_health": args.marketing_health,
        "cost_estimate":    args.cost_estimate,
        "error_message":    args.error_message,
    }
    # Strip None values — Supabase will use column defaults
    payload = {k: v for k, v in payload.items() if v is not None}

    if args.dry_run:
        print("[DRY RUN] Would send to Supabase:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("[DRY RUN] OK — no request made")
        return

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_role_key:
        print("ERROR: SUPABASE_URL と SUPABASE_SERVICE_ROLE_KEY を環境変数に設定してください。")
        print("  export SUPABASE_URL=https://xxxx.supabase.co")
        print("  export SUPABASE_SERVICE_ROLE_KEY=eyJ...")
        sys.exit(1)

    url = f"{supabase_url}/rest/v1/run_logs"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = Request(url, data=body, method="POST")
    req.add_header("apikey",        service_role_key)
    req.add_header("Authorization", f"Bearer {service_role_key}")
    req.add_header("Content-Type",  "application/json")
    req.add_header("Prefer",        "return=minimal")  # → HTTP 204

    try:
        with urlopen(req, timeout=15) as resp:
            # Supabase returns 201 with body or 204 without body (Prefer: return=minimal)
            if resp.status in (200, 201, 204):
                print(f"OK: run_id={args.run_id!r}  status={args.status}  http={resp.status}")
            else:
                body_text = resp.read().decode("utf-8", errors="replace")[:200]
                print(f"WARNING: unexpected HTTP {resp.status}: {body_text}")
                sys.exit(1)
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:400]
        print(f"ERROR: HTTP {e.code} from Supabase: {body_text}")
        sys.exit(1)
    except URLError as e:
        print(f"ERROR: Cannot reach Supabase at {supabase_url}: {e.reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
