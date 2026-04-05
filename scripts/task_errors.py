#!/usr/bin/env python3
"""Show recent OpenClaw task failures with failure reason and gate outcome.

Reads JSON report files from REPORTS_DIR and prints a table of failed/partial
tasks in the requested time window, with failure class, gate outcome, and cost.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


TASKS_DIR = Path.home() / ".openclaw" / "tasks"
REPORTS_DIR = TASKS_DIR / "reports"


def _load_failures(days: int) -> list[dict]:
    """Load all failed/partial reports within the last N days."""
    if not REPORTS_DIR.exists():
        return []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
    results = []
    for report_file in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(report_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        status = data.get("status", "")
        if status not in ("failed", "failed_exception", "partial") and not status.startswith("fail"):
            continue
        # Time filter
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


def _render_table(failures: list[dict], days: int) -> None:
    """Print a human-readable failure table."""
    print(f"OpenClaw Task Failures — last {days} day(s)")
    print("=" * 80)
    if not failures:
        print(f"  No failures in the last {days} day(s).")
        print("=" * 80)
        return

    print(f"  {'Task':<40} {'Status':<18} {'Failure Class':<20}")
    print(f"  {'-'*40} {'-'*18} {'-'*20}")
    for r in failures:
        task_id = r.get("task_id") or r.get("task_file") or "unknown"
        if len(task_id) > 40:
            task_id = task_id[-40:]
        status = r.get("status", "unknown")
        failure_class = r.get("primary_failure_class") or "—"
        if len(failure_class) > 20:
            failure_class = failure_class[:17] + "..."

        # Review gate info
        gate = r.get("review_gate") or {}
        gate_info = ""
        if gate:
            gate_info = "gate:" + ("pass" if gate.get("review_passed") else "fail")

        # Exception snippet
        exc = r.get("exception") or ""
        if exc and len(exc) > 60:
            exc = exc[:57] + "..."

        print(f"  {task_id:<40} {status:<18} {failure_class:<20}")
        if gate_info:
            print(f"    {'':>3} {gate_info}")
        if exc:
            print(f"    {'':>3} error: {exc}")

        # Failure event codes
        codes = r.get("failure_event_codes") or []
        if codes:
            print(f"    {'':>3} codes: {', '.join(codes[:3])}")

    print("=" * 80)
    print(f"  Total failures: {len(failures)}")


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Show recent OpenClaw task failures"
    )
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    failures = _load_failures(args.days)

    if args.json:
        print(json.dumps(failures, indent=2))
    else:
        _render_table(failures, args.days)

    return 0


if __name__ == "__main__":
    sys.exit(main())
