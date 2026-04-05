#!/usr/bin/env python3
"""Show LLM cost breakdown for OpenClaw/moltbot tasks.

Queries the shared llm_client observability DB for calls attributed to
project='moltbot' or tasks matching 'openclaw.*', and renders a breakdown
table by task name.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


DEFAULT_DB = Path.home() / "projects" / "data" / "llm_observability.db"
OPENCLAW_DB_ENV = "OPENCLAW_OBSERVABILITY_DB"

# Projects/task prefixes that belong to the moltbot/openclaw runtime
MOLTBOT_PROJECTS = ("moltbot", ".openclaw", "openclaw")
OPENCLAW_TASK_PREFIX = "openclaw."


def _get_db_path() -> Path:
    """Return the observability DB path from env or default."""
    env_path = os.environ.get(OPENCLAW_DB_ENV)
    if env_path:
        return Path(env_path)
    return DEFAULT_DB


def _query_costs(db_path: Path, days: int) -> list[dict]:
    """Query llm_calls for moltbot/openclaw rows in the last N days."""
    if not db_path.exists():
        return []
    cutoff_iso = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                project,
                task,
                COUNT(*) as calls,
                SUM(COALESCE(cost, 0)) as total_cost,
                SUM(COALESCE(prompt_tokens, 0)) as prompt_tokens,
                SUM(COALESCE(completion_tokens, 0)) as completion_tokens
            FROM llm_calls
            WHERE timestamp >= ?
              AND (
                project IN ({proj_placeholders})
                OR task LIKE ?
              )
            GROUP BY project, task
            ORDER BY total_cost DESC
            """.format(proj_placeholders=",".join("?" * len(MOLTBOT_PROJECTS))),
            [cutoff_iso, *MOLTBOT_PROJECTS, OPENCLAW_TASK_PREFIX + "%"],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _render_table(rows: list[dict], days: int, db_path: Path) -> None:
    """Print a human-readable cost breakdown table."""
    total_cost = sum(r["total_cost"] for r in rows)
    total_calls = sum(r["calls"] for r in rows)

    print(f"OpenClaw LLM Cost — last {days} day(s)  [DB: {db_path}]")
    print("=" * 72)
    if not rows:
        print("  No moltbot/openclaw rows found in this window.")
        print("  Tip: verify task= kwarg is set on all llm_client calls in run_task.py")
        print("=" * 72)
        return

    print(f"  {'Task':<40} {'Calls':>6} {'Cost':>10}")
    print(f"  {'-'*40} {'-'*6} {'-'*10}")
    for r in rows:
        label = f"{r['project']}/{r['task']}"
        if len(label) > 40:
            label = "..." + label[-37:]
        print(f"  {label:<40} {r['calls']:>6} ${r['total_cost']:>9.4f}")
    print(f"  {'─'*40} {'─'*6} {'─'*10}")
    print(f"  {'TOTAL':<40} {total_calls:>6} ${total_cost:>9.4f}")
    print("=" * 72)


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Show LLM cost breakdown for OpenClaw tasks"
    )
    parser.add_argument("--days", type=int, default=7, help="Look back N days (default: 7)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    db_path = _get_db_path()
    rows = _query_costs(db_path, args.days)

    if args.json:
        output = {
            "days": args.days,
            "db": str(db_path),
            "rows": rows,
            "total_cost": sum(r["total_cost"] for r in rows),
        }
        print(json.dumps(output, indent=2))
    else:
        _render_table(rows, args.days, db_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
