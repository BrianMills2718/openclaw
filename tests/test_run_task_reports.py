"""Tests for Plan #2 Phase 4: report schema fields for delivery mode and gating.

Verifies that graph reports carry the new fields (planner_lineage,
review_gate, commit_evidence) and that flat reports remain backward-compatible.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

_MOLTBOT_ROOT = Path(__file__).resolve().parent.parent
if str(_MOLTBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_MOLTBOT_ROOT))

from run_task import _write_task_report  # type: ignore[import]


class TestGraphReportFields:
    """Graph reports must carry delivery mode, review gate, and commit evidence."""

    def test_graph_report_includes_planner_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            with patch("run_task.REPORTS_DIR", reports_dir):
                payload = {
                    "report_version": "v1",
                    "task_type": "graph",
                    "graph_id": "test-graph",
                    "status": "completed",
                    "destination": "completed",
                    "planner_lineage": {
                        "delivery_mode": "review_cycle",
                        "task_kind": "code_change",
                    },
                    "review_gate": {"passed": True, "status": "pass"},
                    "commit_evidence": {"commit_detected": True, "commit_sha": "abc1234"},
                    "finished_at": "2026-04-04T00:00:00+00:00",
                }
                out = _write_task_report("test-graph", payload)
                written = json.loads(out.read_text())
        assert "planner_lineage" in written
        assert written["planner_lineage"]["delivery_mode"] == "review_cycle"

    def test_graph_report_includes_review_gate_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            with patch("run_task.REPORTS_DIR", reports_dir):
                payload = {
                    "report_version": "v1",
                    "task_type": "graph",
                    "review_gate": {
                        "passed": False,
                        "status": "needs_changes",
                        "reason": "too many issues",
                    },
                    "commit_evidence": {"commit_detected": False},
                    "finished_at": "2026-04-04T00:00:00+00:00",
                }
                out = _write_task_report("test-graph-fail", payload)
                written = json.loads(out.read_text())
        assert written["review_gate"]["passed"] is False
        assert written["review_gate"]["status"] == "needs_changes"

    def test_graph_report_includes_commit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            with patch("run_task.REPORTS_DIR", reports_dir):
                payload = {
                    "report_version": "v1",
                    "commit_evidence": {
                        "commit_detected": True,
                        "commit_sha": "deadbeef",
                        "commit_timestamp": "2026-04-04T01:00:00+00:00",
                        "passed": True,
                    },
                    "finished_at": "2026-04-04T00:00:00+00:00",
                }
                out = _write_task_report("test-graph-commit", payload)
                written = json.loads(out.read_text())
        assert written["commit_evidence"]["commit_sha"] == "deadbeef"


class TestFlatReportBackwardCompat:
    """Flat task reports must remain valid (additive-only changes)."""

    def test_flat_report_without_new_fields_still_writes(self) -> None:
        """A flat report without planner_lineage must still serialize and write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            with patch("run_task.REPORTS_DIR", reports_dir):
                payload = {
                    "report_version": "v1",
                    "task_type": "flat",
                    "task_id": "old-style-task",
                    "status": "completed",
                    "finished_at": "2026-04-04T00:00:00+00:00",
                }
                out = _write_task_report("old-style-task", payload)
                written = json.loads(out.read_text())
        assert written["task_type"] == "flat"
        assert written["status"] == "completed"
        # New fields absent — that's fine for old reports
        assert "planner_lineage" not in written

    def test_flat_report_with_planner_lineage_records_it(self) -> None:
        """When planner_lineage is present in a flat report, it is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir) / "reports"
            with patch("run_task.REPORTS_DIR", reports_dir):
                payload = {
                    "report_version": "v1",
                    "task_type": "flat",
                    "planner_lineage": {
                        "delivery_mode": "flat",
                        "task_kind": "docs_only",
                    },
                    "finished_at": "2026-04-04T00:00:00+00:00",
                }
                out = _write_task_report("new-flat-task", payload)
                written = json.loads(out.read_text())
        assert written["planner_lineage"]["delivery_mode"] == "flat"
