"""Review gate audit log — surface all review-cycle task outcomes.

Scans the OpenClaw reports directory for tasks that went through the
planner review-cycle gate and renders a human-readable summary table.

Usage:
    python scripts/review_gate_log.py [--days N] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TASKS_DIR = Path(os.environ.get("OPENCLAW_TASKS_DIR", Path.home() / ".openclaw" / "tasks"))
REPORTS_DIR = Path(os.environ.get("OPENCLAW_REPORTS_DIR", TASKS_DIR / "reports"))


def _load_reports(max_age_days: int) -> list[dict]:
    """Load all report JSON files, filtered by age."""
    if not REPORTS_DIR.exists():
        return []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
    reports = []
    for path in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        # Age filter on finished_at or file mtime
        ts_str = data.get("finished_at") or data.get("started_at")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue
            except ValueError:
                pass
        reports.append(data)
    return reports


def _is_review_cycle(report: dict) -> bool:
    lineage = report.get("planner_lineage") or {}
    meta = report.get("planner_metadata") or {}
    return (
        lineage.get("delivery_mode") == "review_cycle"
        or meta.get("delivery_mode") == "review_cycle"
    )


def _summarize(report: dict) -> dict:
    gate = report.get("review_gate") or {}
    commit = report.get("commit_evidence") or {}
    lineage = report.get("planner_lineage") or {}
    return {
        "task": report.get("task_id") or report.get("graph_id") or "unknown",
        "status": report.get("destination") or report.get("status") or "?",
        "finished_at": (report.get("finished_at") or "")[:19],
        "review_passed": gate.get("passed"),
        "review_status": gate.get("status") or gate.get("reason") or "",
        "commit_detected": commit.get("commit_detected"),
        "commit_sha": (commit.get("commit_sha") or "")[:8],
        "task_kind": lineage.get("task_kind") or "",
    }


def render_table(rows: list[dict]) -> str:
    """Render as a simple ASCII table."""
    if not rows:
        return "(no review-cycle tasks found in range)"
    cols = ["task", "status", "finished_at", "review_passed", "review_status", "commit_sha"]
    widths = {c: max(len(c), max(len(str(r.get(c) or "")) for r in rows)) for c in cols}
    sep = "  ".join("-" * widths[c] for c in cols)
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    lines = [header, sep]
    for r in rows:
        lines.append("  ".join(str(r.get(c) or "").ljust(widths[c]) for c in cols))
    passed = sum(1 for r in rows if r["review_passed"] is True)
    failed = sum(1 for r in rows if r["review_passed"] is False)
    committed = sum(1 for r in rows if r["commit_detected"] is True)
    lines.append("")
    lines.append(f"Total: {len(rows)}  |  Review passed: {passed}  |  Review failed: {failed}  |  Commits detected: {committed}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="Look back N days (default 30)")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output JSON")
    args = parser.parse_args(argv)

    reports = _load_reports(args.days)
    review_reports = [r for r in reports if _is_review_cycle(r)]
    rows = [_summarize(r) for r in review_reports]

    if args.json_out:
        print(json.dumps(rows, indent=2))
        return 0

    print(f"Review-cycle gate log — last {args.days} days — {REPORTS_DIR}\n")
    print(render_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
