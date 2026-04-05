#!/usr/bin/env python3
"""Summarize task execution history from OpenClaw reports/.

Reads JSON report files from REPORTS_DIR and prints a summary table showing
task counts, success/fail rates, review gate pass rates, and commit rates
for the requested time window.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


TASKS_DIR = Path.home() / ".openclaw" / "tasks"
REPORTS_DIR = TASKS_DIR / "reports"


def _load_reports(days: int) -> list[dict]:
    """Load all reports within the last N days."""
    if not REPORTS_DIR.exists():
        return []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    results = []
    for report_file in REPORTS_DIR.glob("*.json"):
        try:
            data = json.loads(report_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        # Parse finished_at for time filtering
        finished_at_str = data.get("finished_at") or data.get("started_at")
        if finished_at_str:
            try:
                finished_at = datetime.fromisoformat(finished_at_str.replace("Z", "+00:00"))
                if finished_at < cutoff:
                    continue
            except ValueError:
                pass
        results.append(data)
    return results


def _summarize(reports: list[dict]) -> dict:
    """Aggregate key metrics from a list of report dicts."""
    total = len(reports)
    completed = sum(1 for r in reports if r.get("status") == "completed")
    failed = sum(1 for r in reports if r.get("status", "").startswith("fail"))

    # Review gate and commit evidence (flat tasks that went through review cycle)
    review_total = 0
    review_passed = 0
    commits_detected = 0
    total_cost_usd = 0.0

    for r in reports:
        lineage = r.get("planner_lineage") or {}
        if lineage.get("delivery_mode") == "review_cycle":
            review_total += 1
            gate = r.get("review_gate") or {}
            if gate.get("review_passed"):
                review_passed += 1
            if gate.get("commit_detected") or gate.get("commit_sha"):
                commits_detected += 1

        # Accumulate cost
        run = r.get("run") or {}
        cost = run.get("cost_usd") or run.get("total_cost_usd")
        if isinstance(cost, (int, float)):
            total_cost_usd += cost

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "other": total - completed - failed,
        "review_total": review_total,
        "review_passed": review_passed,
        "commits_detected": commits_detected,
        "total_cost_usd": total_cost_usd,
    }


def _render_table(summary: dict, days: int) -> None:
    """Print a human-readable summary table."""
    total = summary["total"]
    completed = summary["completed"]
    failed = summary["failed"]
    other = summary["other"]
    review_total = summary["review_total"]
    review_passed = summary["review_passed"]
    commits_detected = summary["commits_detected"]
    cost = summary["total_cost_usd"]

    success_pct = f"{100*completed/total:.0f}%" if total else "n/a"
    gate_pct = f"{100*review_passed/review_total:.0f}%" if review_total else "n/a"
    commit_pct = f"{100*commits_detected/review_total:.0f}%" if review_total else "n/a"

    print(f"OpenClaw Task Summary — last {days} day(s)")
    print("=" * 50)
    print(f"  Total tasks reported:   {total}")
    print(f"  Completed:              {completed}  ({success_pct} success)")
    print(f"  Failed:                 {failed}")
    print(f"  Other (partial/etc):    {other}")
    print()
    print(f"  Review-cycle tasks:     {review_total}")
    print(f"  Review gate passed:     {review_passed}  ({gate_pct})")
    print(f"  Commits detected:       {commits_detected}  ({commit_pct})")
    print()
    print(f"  Total LLM cost:        ${cost:.4f}")
    print("=" * 50)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Summarize OpenClaw task execution history"
    )
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    reports = _load_reports(args.days)
    summary = _summarize(reports)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        _render_table(summary, args.days)

    return 0


if __name__ == "__main__":
    sys.exit(main())
