"""Tests for Plan #2 Phase 0-1: delivery contract validation and task writers.

Verifies that the planner enforces valid delivery contract combinations
and that both writer paths produce correct artifacts.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure moltbot root is importable
_MOLTBOT_ROOT = Path(__file__).resolve().parent.parent
if str(_MOLTBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_MOLTBOT_ROOT))

from task_planner import (  # type: ignore[import]
    VALID_DELIVERY_MODES,
    VALID_TASK_KINDS,
    validate_task_delivery_contract,
    write_flat_task,
)


def _make_task(**overrides: object) -> dict:
    """Build a minimal valid task dict."""
    base = {
        "id": "test-slug",
        "priority": "high",
        "agent": "codex",
        "model": "codex",
        "project": "/tmp",
        "goal_advanced": "test goal",
        "max_budget_usd": 1.0,
        "max_turns": 20,
        "title": "Test task",
        "objective": "Do something useful.",
        "acceptance_criteria": ["criterion one"],
        "task_kind": "docs_only",
        "delivery_mode": "flat",
        "file_scope": [],
        "review_rounds": None,
    }
    base.update(overrides)
    return base


class TestValidateDeliveryContract:
    """validate_task_delivery_contract rejects invalid field combinations."""

    def test_valid_flat_docs_task(self) -> None:
        task = _make_task(task_kind="docs_only", delivery_mode="flat", review_rounds=None)
        assert validate_task_delivery_contract(task) == []

    def test_valid_flat_analysis_task(self) -> None:
        task = _make_task(task_kind="analysis_only", delivery_mode="flat", review_rounds=None)
        assert validate_task_delivery_contract(task) == []

    def test_valid_review_cycle_code_task(self) -> None:
        task = _make_task(task_kind="code_change", delivery_mode="review_cycle", review_rounds=1)
        assert validate_task_delivery_contract(task) == []

    def test_rejects_review_cycle_without_code_change(self) -> None:
        task = _make_task(task_kind="docs_only", delivery_mode="review_cycle", review_rounds=1)
        errors = validate_task_delivery_contract(task)
        assert any("task_kind='code_change'" in e for e in errors), errors

    def test_rejects_review_cycle_without_review_rounds(self) -> None:
        task = _make_task(task_kind="code_change", delivery_mode="review_cycle", review_rounds=None)
        errors = validate_task_delivery_contract(task)
        assert any("review_rounds" in e for e in errors), errors

    def test_rejects_flat_with_review_rounds(self) -> None:
        task = _make_task(task_kind="docs_only", delivery_mode="flat", review_rounds=1)
        errors = validate_task_delivery_contract(task)
        assert any("flat" in e and "review_rounds" in e for e in errors), errors

    def test_rejects_invalid_task_kind(self) -> None:
        task = _make_task(task_kind="bogus", delivery_mode="flat", review_rounds=None)
        errors = validate_task_delivery_contract(task)
        assert any("task_kind" in e for e in errors), errors

    def test_rejects_invalid_delivery_mode(self) -> None:
        task = _make_task(task_kind="docs_only", delivery_mode="bogus", review_rounds=None)
        errors = validate_task_delivery_contract(task)
        assert any("delivery_mode" in e for e in errors), errors


class TestWriteFlatTask:
    """write_flat_task produces correct flat .md format."""

    def test_writes_md_file_to_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_task()
                dest = write_flat_task(task)
            assert dest.exists()
            assert dest.suffix == ".md"

    def test_flat_task_keeps_yaml_frontmatter_format(self) -> None:
        """Existing flat-task consumers expect YAML frontmatter delimited by ---."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_task(id="my-slug")
                dest = write_flat_task(task)
            content = dest.read_text()
        assert content.startswith("---\n"), "Flat task must start with YAML frontmatter"
        assert "\n---\n" in content, "Frontmatter must be closed with ---"

    def test_flat_task_records_planner_lineage(self) -> None:
        """Flat tasks must embed delivery_mode for observability."""
        import yaml

        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_task(task_kind="docs_only")
                dest = write_flat_task(task)
            content = dest.read_text()

        fm_text = re.match(r"---\n(.*?)\n---", content, re.DOTALL).group(1)  # type: ignore[union-attr]
        fm = yaml.safe_load(fm_text)
        assert fm.get("planner_lineage", {}).get("delivery_mode") == "flat"
        assert fm.get("planner_lineage", {}).get("task_kind") == "docs_only"

    def test_flat_task_id_is_deterministic_slug(self) -> None:
        """Task id includes the planner- prefix and the original slug."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = Path(tmpdir) / "pending"
            with patch("task_planner.PENDING_DIR", pending):
                task = _make_task(id="my-unique-slug")
                dest = write_flat_task(task)
        assert "my-unique-slug" in dest.name
