"""Tests for Plan #2 Phase 1: review-cycle graph writer contract.

Verifies that write_review_cycle_task produces a valid graph YAML with:
- deterministic id derived from planner task id
- planner_metadata block with final_review_json path
- review and synthesis tasks present for 1-round cycles
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

_MOLTBOT_ROOT = Path(__file__).resolve().parent.parent
if str(_MOLTBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_MOLTBOT_ROOT))

from task_planner import write_review_cycle_task  # type: ignore[import]


def _make_code_task(**overrides: object) -> dict:
    """Build a minimal valid code_change task dict."""
    base = {
        "id": "my-code-task",
        "priority": "high",
        "agent": "codex",
        "model": "codex",
        "project": str(Path.home() / "projects" / "moltbot"),
        "goal_advanced": "test goal",
        "max_budget_usd": 1.0,
        "max_turns": 20,
        "title": "Test code task",
        "objective": "Add a small helper function.",
        "acceptance_criteria": ["function exists", "tests pass"],
        "task_kind": "code_change",
        "delivery_mode": "review_cycle",
        "file_scope": ["task_planner.py"],
        "review_rounds": 1,
    }
    base.update(overrides)
    return base


class TestWriteReviewCycleTask:
    """write_review_cycle_task produces correct graph YAML artifacts."""

    def test_write_review_cycle_task_emits_graph_yaml(self) -> None:
        """A review-cycle task produces a .yaml file in pending/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_code_task()
                dest = write_review_cycle_task(task)
                assert dest.exists(), f"Expected {dest} to exist"
                assert dest.suffix == ".yaml", f"Expected .yaml, got {dest.suffix}"

    def test_graph_yaml_has_deterministic_id(self) -> None:
        """Graph id must be derived from planner task id, not random."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_code_task(id="my-code-task")
                dest = write_review_cycle_task(task)
                assert "my-code-task" in dest.name

    def test_graph_yaml_includes_planner_metadata(self) -> None:
        """Graph YAML must include planner_metadata block for run_task.py gating."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_code_task()
                dest = write_review_cycle_task(task)
                graph = yaml.safe_load(dest.read_text())
        assert "planner_metadata" in graph, "Missing planner_metadata in graph YAML"
        pm = graph["planner_metadata"]
        assert pm.get("delivery_mode") == "review_cycle"
        assert pm.get("task_kind") == "code_change"
        assert pm.get("review_rounds") == 1

    def test_graph_yaml_includes_final_review_json_reference(self) -> None:
        """planner_metadata.final_review_json must point to round_1/review.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_code_task(review_rounds=1)
                dest = write_review_cycle_task(task)
                graph = yaml.safe_load(dest.read_text())
        final_review_json = graph["planner_metadata"]["final_review_json"]
        assert "round_1" in final_review_json, f"Expected round_1 in path: {final_review_json}"
        assert final_review_json.endswith("review.json"), f"Expected review.json: {final_review_json}"

    def test_graph_yaml_has_review_and_synthesis_tasks(self) -> None:
        """1-round graph must still contain review and synthesis stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_code_task(review_rounds=1)
                dest = write_review_cycle_task(task)
                graph = yaml.safe_load(dest.read_text())
        task_names = list(graph.get("tasks", {}).keys())
        assert any("review" in t for t in task_names), f"No review task in {task_names}"
        assert any("synth" in t or "synthesis" in t for t in task_names), (
            f"No synthesis task in {task_names}"
        )
