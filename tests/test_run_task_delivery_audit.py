"""Tests for non-destructive delivery-readiness audits."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import run_task


def _flat_task_file(tmp_path: Path) -> Path:
    """Create one minimal flat task for audit coverage."""

    task_path = tmp_path / "planner-2026-04-04-docs-refresh.md"
    task_path.write_text(
        """---
id: planner-2026-04-04-docs-refresh
priority: medium
agent: codex
model: codex
project: {project}
created: 2026-04-04T00:00:00+00:00
status: pending
task_kind: docs_only
delivery_mode: flat
planner_lineage:
  planner_task_id: planner-2026-04-04-docs-refresh
  generated_at: "2026-04-04T10:00:00+00:00"
constraints:
  max_turns: 12
  max_budget_usd: 1.0
---
# Refresh docs

## Objective
Refresh docs.

## Acceptance Criteria
- [ ] Docs updated
""".format(project=tmp_path)
    )
    return task_path


def test_audit_delivery_readiness_for_flat_task_reports_ready_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Flat-task audits should surface the same delivery contract and preflight state."""

    task_path = _flat_task_file(tmp_path)

    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.25))
    monkeypatch.setattr(
        run_task,
        "_run_flat_preflight",
        lambda task: {
            "passed": True,
            "checks": [{"check": "project_path_exists", "passed": True}],
            "failures": [],
            "failure_event_codes": [],
            "primary_failure_class": "none",
        },
    )

    audit = run_task._audit_delivery_readiness(task_path)

    assert audit["ready"] is True
    assert audit["task_type"] == "flat"
    assert audit["task_id"] == "planner-2026-04-04-docs-refresh"
    assert audit["task_kind"] == "docs_only"
    assert audit["delivery_mode"] == "flat"
    assert audit["planner_lineage"]["planner_task_id"] == "planner-2026-04-04-docs-refresh"
    assert audit["planner_lineage"]["generated_at"] == "2026-04-04T10:00:00+00:00"
    assert audit["budget_check"]["passed"] is True
    assert audit["preflight"]["passed"] is True


def test_audit_delivery_readiness_for_graph_reports_ready_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Graph audits should surface graph shape and delivery metadata without execution."""

    task_graph_module = types.ModuleType("scripts.meta.task_graph")
    task_graph_module.load_graph = lambda path: SimpleNamespace(
        meta=SimpleNamespace(id="graph-1", description="demo graph"),
        tasks={"implement_r1": {}, "review_r1": {}, "synthesize": {}},
        waves=[["implement_r1"], ["review_r1"], ["synthesize"]],
    )
    monkeypatch.setitem(sys.modules, "scripts.meta.task_graph", task_graph_module)
    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.5))
    monkeypatch.setattr(run_task, "_load_mcp_registry", lambda: {})
    monkeypatch.setattr(
        run_task,
        "_run_graph_preflight",
        lambda graph, mcp_configs: {
            "passed": True,
            "checks": [{"check": "graph_non_empty", "passed": True}],
            "failures": [],
            "failure_event_codes": [],
            "primary_failure_class": "none",
        },
    )

    task_path = tmp_path / "graph-1.yaml"
    task_path.write_text(
        yaml.safe_dump(
            {
                "graph": {"id": "graph-1", "description": "demo", "timeout_minutes": 30, "checkpoint": "none"},
                "tasks": {"implement_r1": {}, "review_r1": {}, "synthesize": {}},
                "metadata": {
                    "delivery_mode": "review_cycle",
                    "task_kind": "code_change",
                    "planner_lineage": {
                        "planner_task_id": "planner-2026-04-04-demo-task",
                        "generated_at": "2026-04-04T12:34:56+00:00",
                    },
                },
            },
            sort_keys=False,
        )
    )

    audit = run_task._audit_delivery_readiness(task_path)

    assert audit["ready"] is True
    assert audit["task_type"] == "graph"
    assert audit["graph_id"] == "graph-1"
    assert audit["task_count"] == 3
    assert audit["wave_count"] == 3
    assert audit["task_kind"] == "code_change"
    assert audit["delivery_mode"] == "review_cycle"
    assert audit["planner_lineage"]["planner_task_id"] == "planner-2026-04-04-demo-task"
    assert audit["planner_lineage"]["generated_at"] == "2026-04-04T12:34:56+00:00"
    assert audit["preflight"]["passed"] is True


def test_audit_delivery_readiness_for_graph_fails_when_workdir_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Graph audits should fail before execution when a task working directory is missing."""

    task_graph_module = types.ModuleType("scripts.meta.task_graph")
    task_graph_module.load_graph = lambda path: SimpleNamespace(
        meta=SimpleNamespace(id="graph-1", description="demo graph"),
        tasks={
            "implement_r1": SimpleNamespace(mcp_servers=[], working_directory=str(tmp_path / "missing-repo")),
        },
        waves=[["implement_r1"]],
    )
    monkeypatch.setitem(sys.modules, "scripts.meta.task_graph", task_graph_module)
    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.5))
    monkeypatch.setattr(run_task, "_load_mcp_registry", lambda: {})

    task_path = tmp_path / "graph-1.yaml"
    task_path.write_text(
        yaml.safe_dump(
            {
                "graph": {"id": "graph-1", "description": "demo", "timeout_minutes": 30, "checkpoint": "none"},
                "tasks": {"implement_r1": {}},
                "metadata": {"delivery_mode": "review_cycle", "task_kind": "code_change"},
            },
            sort_keys=False,
        )
    )

    audit = run_task._audit_delivery_readiness(task_path)

    assert audit["ready"] is False
    assert audit["preflight"]["passed"] is False
    assert audit["preflight"]["failure_event_codes"] == ["OPENCLAW_PREFLIGHT_WORKDIR_MISSING"]


def test_audit_delivery_readiness_reports_load_failures_without_throwing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Audit failures should stay observable and non-destructive when graph loading breaks."""

    task_graph_module = types.ModuleType("scripts.meta.task_graph")
    task_graph_module.load_graph = lambda path: (_ for _ in ()).throw(RuntimeError("broken graph"))
    monkeypatch.setitem(sys.modules, "scripts.meta.task_graph", task_graph_module)
    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.0))

    task_path = tmp_path / "broken.yaml"
    task_path.write_text("graph: [")

    audit = run_task._audit_delivery_readiness(task_path)

    assert audit["ready"] is False
    assert audit["preflight"]["passed"] is False
    assert audit["preflight"]["failure_event_codes"] == ["OPENCLAW_AUDIT_LOAD_FAILED"]
    assert audit["preflight"]["failures"][0]["error_code"] == "OPENCLAW_AUDIT_LOAD_FAILED"


def test_print_delivery_readiness_audit_for_graph_shows_planner_lineage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Graph audit output should expose planner lineage fields when present."""

    run_task._print_delivery_readiness_audit(
        {
            "ready": True,
            "task_file": "/tmp/graph-1.yaml",
            "task_type": "graph",
            "graph_id": "graph-1",
            "description": "demo graph",
            "task_count": 3,
            "wave_count": 2,
            "planner_lineage": {
                "planner_task_id": "planner-2026-04-04-demo-task",
                "generated_at": "2026-04-04T12:34:56+00:00",
            },
            "task_kind": "code_change",
            "delivery_mode": "review_cycle",
            "budget_check": {"passed": True, "spent_today_usd": 0.5, "daily_budget_usd": 20.0},
            "preflight": {"passed": True, "checks": [], "failures": [], "failure_event_codes": []},
        }
    )

    output = capsys.readouterr().out
    assert "Planner task ID: planner-2026-04-04-demo-task" in output
    assert "Generated at: 2026-04-04T12:34:56+00:00" in output


def test_print_delivery_readiness_audit_for_flat_shows_planner_lineage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Flat audit output should expose planner lineage fields when present."""

    run_task._print_delivery_readiness_audit(
        {
            "ready": True,
            "task_file": "/tmp/planner-2026-04-04-docs-refresh.md",
            "task_type": "flat",
            "task_id": "planner-2026-04-04-docs-refresh",
            "title": "Refresh docs",
            "agent": "codex",
            "model": "codex",
            "project": "/tmp/repo",
            "priority": "medium",
            "planner_lineage": {
                "planner_task_id": "planner-2026-04-04-docs-refresh",
                "generated_at": "2026-04-04T10:00:00+00:00",
            },
            "task_kind": "docs_only",
            "delivery_mode": "flat",
            "budget_check": {"passed": True, "spent_today_usd": 0.25, "daily_budget_usd": 20.0},
            "preflight": {"passed": True, "checks": [], "failures": [], "failure_event_codes": []},
        }
    )

    output = capsys.readouterr().out
    assert "Planner task ID: planner-2026-04-04-docs-refresh" in output
    assert "Generated at: 2026-04-04T10:00:00+00:00" in output


def test_print_delivery_readiness_audit_for_flat_omits_missing_planner_lineage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Flat audit output should stay clean when planner lineage is absent."""

    run_task._print_delivery_readiness_audit(
        {
            "ready": True,
            "task_file": "/tmp/manual-task.md",
            "task_type": "flat",
            "task_id": "manual-task",
            "title": "Some manual task",
            "agent": "codex",
            "model": "codex",
            "project": "/tmp/repo",
            "priority": "medium",
            "budget_check": {"passed": True, "spent_today_usd": 0.5, "daily_budget_usd": 20.0},
            "preflight": {"passed": True, "checks": [], "failures": [], "failure_event_codes": []},
        }
    )

    output = capsys.readouterr().out
    assert "Planner task ID:" not in output
    assert "Generated at:" not in output


def test_print_delivery_readiness_audit_for_graph_omits_missing_planner_lineage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Graph audit output should stay clean when planner lineage is absent."""

    run_task._print_delivery_readiness_audit(
        {
            "ready": True,
            "task_file": "/tmp/graph-1.yaml",
            "task_type": "graph",
            "graph_id": "graph-1",
            "description": "demo graph",
            "task_count": 3,
            "wave_count": 2,
            "budget_check": {"passed": True, "spent_today_usd": 0.5, "daily_budget_usd": 20.0},
            "preflight": {"passed": True, "checks": [], "failures": [], "failure_event_codes": []},
        }
    )

    output = capsys.readouterr().out
    assert "Planner task ID:" not in output
    assert "Generated at:" not in output


def test_main_audit_delivery_readiness_exits_before_task_execution(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI audit mode should exit early instead of dispatching task execution."""

    task_path = _flat_task_file(tmp_path)
    printed: list[dict[str, object]] = []

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_task.py", "--audit-delivery-readiness", str(task_path)],
    )
    monkeypatch.setattr(
        run_task,
        "_audit_delivery_readiness",
        lambda path: {
            "ready": False,
            "task_file": str(path),
            "task_type": "flat",
            "budget_check": {"passed": True, "spent_today_usd": 0.0, "daily_budget_usd": 20.0},
            "preflight": {"passed": False, "checks": [], "failures": [], "failure_event_codes": []},
        },
    )
    monkeypatch.setattr(run_task, "_print_delivery_readiness_audit", lambda payload: printed.append(payload))
    monkeypatch.setattr(
        run_task.asyncio,
        "run",
        lambda coroutine: (_ for _ in ()).throw(AssertionError("task execution should not start in audit mode")),
    )

    with pytest.raises(SystemExit) as excinfo:
        run_task.main()

    assert excinfo.value.code == 1
    assert printed and printed[0]["task_file"] == str(task_path)
    assert capsys.readouterr().out == ""


def test_main_audit_delivery_readiness_exits_zero_when_ready(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The CLI audit mode should return success when the task is ready."""

    task_path = _flat_task_file(tmp_path)
    printed: list[dict[str, object]] = []

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_task.py", "--audit-delivery-readiness", str(task_path)],
    )
    monkeypatch.setattr(
        run_task,
        "_audit_delivery_readiness",
        lambda path: {
            "ready": True,
            "task_file": str(path),
            "task_type": "flat",
            "budget_check": {"passed": True, "spent_today_usd": 0.0, "daily_budget_usd": 20.0},
            "preflight": {"passed": True, "checks": [], "failures": [], "failure_event_codes": []},
        },
    )
    monkeypatch.setattr(run_task, "_print_delivery_readiness_audit", lambda payload: printed.append(payload))
    monkeypatch.setattr(
        run_task.asyncio,
        "run",
        lambda coroutine: (_ for _ in ()).throw(AssertionError("task execution should not start in audit mode")),
    )

    with pytest.raises(SystemExit) as excinfo:
        run_task.main()

    assert excinfo.value.code == 0
    assert printed and printed[0]["task_file"] == str(task_path)


def test_main_audit_delivery_readiness_prints_planner_lineage(
    monkeypatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI audit output should include planner lineage fields when present."""

    task_path = _flat_task_file(tmp_path)

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_task.py", "--audit-delivery-readiness", str(task_path)],
    )
    monkeypatch.setattr(
        run_task,
        "_audit_delivery_readiness",
        lambda path: {
            "ready": True,
            "task_file": str(path),
            "task_type": "flat",
            "task_id": "planner-2026-04-04-docs-refresh",
            "title": "Refresh docs",
            "agent": "codex",
            "model": "codex",
            "project": str(tmp_path),
            "priority": "medium",
            "planner_lineage": {
                "planner_task_id": "planner-2026-04-04-docs-refresh",
                "generated_at": "2026-04-04T10:00:00+00:00",
            },
            "task_kind": "docs_only",
            "delivery_mode": "flat",
            "budget_check": {"passed": True, "spent_today_usd": 0.0, "daily_budget_usd": 20.0},
            "preflight": {"passed": True, "checks": [], "failures": [], "failure_event_codes": []},
        },
    )
    monkeypatch.setattr(
        run_task.asyncio,
        "run",
        lambda coroutine: (_ for _ in ()).throw(AssertionError("task execution should not start in audit mode")),
    )

    with pytest.raises(SystemExit) as excinfo:
        run_task.main()

    output = capsys.readouterr().out
    assert excinfo.value.code == 0
    assert "Planner task ID: planner-2026-04-04-docs-refresh" in output
    assert "Generated at: 2026-04-04T10:00:00+00:00" in output
