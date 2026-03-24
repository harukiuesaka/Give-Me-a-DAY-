#!/usr/bin/env python3
"""
scripts/ai/collect_issue_context.py
Purpose : GitHub Issues の open/recent-closed を収集して daily report 用の要約を出力する。
Usage   : python3 scripts/ai/collect_issue_context.py [--limit N] [--output FILE]
Env     : GITHUB_TOKEN  (optional — 未設定時は unauthenticated API で rate limit 60req/h)
Output  : stdout (markdown) or --output に指定したファイル
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

REPO = "haruki121731-del/Give-Me-a-DAY-"
API_BASE = f"https://api.github.com/repos/{REPO}"


def fetch_issues(token: str | None, state: str = "open", limit: int = 20) -> list[dict]:
    url = f"{API_BASE}/issues?state={state}&per_page={limit}&sort=updated&direction=desc"
    req = Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except (HTTPError, URLError) as e:
        print(f"WARNING: GitHub API error: {e}", file=sys.stderr)
        return []


def summarize_issue(issue: dict) -> str:
    title = issue.get("title", "(no title)")
    number = issue.get("number", "?")
    state = issue.get("state", "?")
    labels = [lb["name"] for lb in issue.get("labels", [])]
    label_str = ", ".join(f"`{lb}`" for lb in labels) if labels else "—"
    updated = issue.get("updated_at", "")[:10]
    url = issue.get("html_url", "")
    return f"- [#{number}]({url}) **{title}** | state: {state} | labels: {label_str} | updated: {updated}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect GitHub issue context for daily report")
    parser.add_argument("--limit", type=int, default=15, help="Max issues to fetch (default: 15)")
    parser.add_argument("--output", default=None, help="Output file path (default: stdout)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    open_issues = fetch_issues(token, state="open", limit=args.limit)
    # Filter out pull requests (GitHub API returns PRs in issues endpoint)
    open_issues = [i for i in open_issues if "pull_request" not in i]

    # Recently closed (last 7 days)
    closed_issues = fetch_issues(token, state="closed", limit=args.limit)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_closed = [
        i for i in closed_issues
        if "pull_request" not in i
        and datetime.fromisoformat(i.get("closed_at", "2000-01-01T00:00:00Z").replace("Z", "+00:00")) > week_ago
    ]

    lines = [
        f"## Issue Context — {now}",
        "",
        f"### Open Issues ({len(open_issues)}件)",
    ]
    if open_issues:
        lines += [summarize_issue(i) for i in open_issues]
    else:
        lines.append("- なし")

    lines += [
        "",
        f"### 直近7日でCloseされたIssue ({len(recent_closed)}件)",
    ]
    if recent_closed:
        lines += [summarize_issue(i) for i in recent_closed]
    else:
        lines.append("- なし")

    output = "\n".join(lines) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Written: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
