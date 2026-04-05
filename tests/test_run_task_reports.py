"""Tests for additive report metadata on flat and graph tasks."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import yaml

import run_task


def _task_result(
    *,
    task_id: str,
    status: str,
    wave: int,
    error: str | None = None,
    validation_results: list[dict[str, object]] | None = None,
) -> SimpleNamespace:
    """Build one fake graph task result for report tests."""

    return SimpleNamespace(
        task_id=task_id,
        status=status,
        wave=wave,
        model_selected="codex",
        requested_model="codex",
        resolved_model="codex",
        duration_s=1.0,
        cost_usd=0.1,
        validation_results=validation_results or [],
        error=error,
    )


def test_graph_report_records_delivery_mode_review_gate_and_commit_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Graph reports include the additive delivery, review, and commit fields."""

    analyzer_module = types.ModuleType("scripts.meta.analyzer")
    analyzer_module.analyze_run = lambda *args, **kwargs: SimpleNamespace(proposals=[])
    task_graph_module = types.ModuleType("scripts.meta.task_graph")
    task_graph_module.ExecutionReport = object
    task_graph_module.load_graph = lambda path: SimpleNamespace(
        meta=SimpleNamespace(id="graph-1"),
        tasks={"implement_r1": {}, "review_r1": {}, "synthesize": {}},
        waves=[["implement_r1"], ["review_r1"], ["synthesize"]],
    )

    async def _run_graph(*args, **kwargs):
        return SimpleNamespace(
            status="completed",
            total_cost_usd=0.1,
            total_duration_s=1.0,
            waves_completed=3,
            waves_total=3,
            task_results=[
                _task_result(
                    task_id="implement_r1",
                    status="completed",
                    wave=0,
                    validation_results=[{"passed": True, "type": "file_exists", "path": "implementation.md"}],
                ),
                _task_result(
                    task_id="review_r1",
                    status="completed",
                    wave=1,
                    validation_results=[{"passed": True, "type": "json_schema", "path": "review.json"}],
                ),
            ],
        )

    task_graph_module.run_graph = _run_graph
    monkeypatch.setitem(sys.modules, "scripts.meta.analyzer", analyzer_module)
    monkeypatch.setitem(sys.modules, "scripts.meta.task_graph", task_graph_module)

    review_path = tmp_path / "workspace" / "graph-1" / "round_1" / "review.json"
    review_path.parent.mkdir(parents=True)
    review_path.write_text('{"status": "pass", "summary": "ok"}')
    task_path = tmp_path / "graph-1.yaml"
    task_path.write_text(
        yaml.safe_dump(
            {
                "graph": {"id": "graph-1", "description": "demo", "timeout_minutes": 30, "checkpoint": "none"},
                "tasks": {"implement_r1": {}, "review_r1": {}, "synthesize": {}},
                "metadata": {
                    "delivery_mode": "review_cycle",
                    "task_kind": "code_change",
                    "target_repo_path": str(tmp_path / "repo"),
                    "final_review_json": str(review_path),
                    "planner_lineage": {"planner_task_id": "planner-2026-04-04-demo-task"},
                },
            },
            sort_keys=False,
        )
    )
    reports: list[dict[str, object]] = []

    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.0))
    monkeypatch.setattr(run_task, "_load_mcp_registry", lambda: {})
    monkeypatch.setattr(run_task, "_run_graph_preflight", lambda graph, mcp_configs: {"passed": True})
    monkeypatch.setattr(run_task, "_move_task", lambda path, destination: path)
    monkeypatch.setattr(run_task, "_write_task_report", lambda task_ref, payload: reports.append(payload) or tmp_path / "report.json")
    monkeypatch.setattr(
        run_task,
        "_detect_commit_evidence",
        lambda project_path, started_at: {
            "required": True,
            "passed": True,
            "commit_detected": True,
            "commit_sha": "abc123",
            "commit_timestamp": "2026-04-04T01:02:03+00:00",
        },
    )

    asyncio.run(run_task._run_graph_task(task_path))

    assert reports[-1]["delivery_mode"] == "review_cycle"
    assert reports[-1]["task_kind"] == "code_change"
    assert reports[-1]["planner_lineage"]["planner_task_id"] == "planner-2026-04-04-demo-task"
    assert reports[-1]["review_gate"]["passed"] is True
    assert reports[-1]["commit_evidence"]["commit_sha"] == "abc123"
    assert reports[-1]["run"]["failing_task_waves"] == {"count": 0, "waves": []}
    assert reports[-1]["task_results"][0]["task_id"] == "implement_r1"
    assert reports[-1]["task_results"][0]["status"] == "completed"
    assert reports[-1]["task_results"][0]["validation_summary"]["all_passed"] is True
    assert reports[-1]["task_results"][1]["task_id"] == "review_r1"


def test_graph_report_exposes_failed_task_error_directly(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Failed graph reports should surface the failing task summary directly."""

    analyzer_module = types.ModuleType("scripts.meta.analyzer")
    analyzer_module.analyze_run = lambda *args, **kwargs: SimpleNamespace(proposals=[])
    task_graph_module = types.ModuleType("scripts.meta.task_graph")
    task_graph_module.ExecutionReport = object
    task_graph_module.load_graph = lambda path: SimpleNamespace(
        meta=SimpleNamespace(id="graph-1"),
        tasks={"implement_r1": {}, "review_r1": {}},
        waves=[["implement_r1"], ["review_r1"]],
    )

    async def _run_graph(*args, **kwargs):
        return SimpleNamespace(
            status="partial",
            total_cost_usd=0.1,
            total_duration_s=1.0,
            waves_completed=1,
            waves_total=2,
            task_results=[
                _task_result(
                    task_id="implement_r1",
                    status="failed",
                    wave=0,
                    error="validator failed: implementation.md missing",
                    validation_results=[{"passed": False, "type": "file_exists", "path": "implementation.md"}],
                )
            ],
        )

    task_graph_module.run_graph = _run_graph
    monkeypatch.setitem(sys.modules, "scripts.meta.analyzer", analyzer_module)
    monkeypatch.setitem(sys.modules, "scripts.meta.task_graph", task_graph_module)

    task_path = tmp_path / "graph-1.yaml"
    task_path.write_text(
        yaml.safe_dump(
            {
                "graph": {"id": "graph-1", "description": "demo", "timeout_minutes": 30, "checkpoint": "none"},
                "tasks": {"implement_r1": {}, "review_r1": {}},
                "metadata": {},
            },
            sort_keys=False,
        )
    )
    reports: list[dict[str, object]] = []

    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.0))
    monkeypatch.setattr(run_task, "_load_mcp_registry", lambda: {})
    monkeypatch.setattr(run_task, "_run_graph_preflight", lambda graph, mcp_configs: {"passed": True})
    monkeypatch.setattr(run_task, "_move_task", lambda path, destination: path)
    monkeypatch.setattr(run_task, "_write_task_report", lambda task_ref, payload: reports.append(payload) or tmp_path / "report.json")

    completed = asyncio.run(run_task._run_graph_task(task_path))

    assert completed is False
    assert reports[-1]["status"] == "failed"
    assert reports[-1]["run"]["graph_execution_status"] == "partial"
    assert reports[-1]["run"]["first_failed_task_id"] == "implement_r1"
    assert reports[-1]["run"]["failing_task_waves"] == {"count": 1, "waves": [0]}
    assert reports[-1]["task_results"][0]["task_id"] == "implement_r1"
    assert reports[-1]["task_results"][0]["error"] == "validator failed: implementation.md missing"
    assert reports[-1]["task_results"][0]["validation_summary"]["failure_refs"] == [
        "file_exists:implementation.md"
    ]


def test_flat_report_records_planner_lineage_when_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Flat task reports keep additive planner lineage without breaking compatibility."""

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
    reports: list[dict[str, object]] = []

    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.0))
    monkeypatch.setattr(run_task, "_run_flat_preflight", lambda task: {"passed": True})
    monkeypatch.setattr(run_task, "_move_task", lambda path, destination: path)
    monkeypatch.setattr(run_task, "_append_status_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_task, "_append_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_task, "_log_cost", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_task, "_run_validation", lambda task, pre_status="": (True, "ok"))
    monkeypatch.setattr(run_task, "_write_task_report", lambda task_ref, payload: reports.append(payload) or tmp_path / "report.json")

    async def _execute_flat_task(task, *, parent_trace_id=None, attempt_context=""):
        return {
            "trace_id": "trace-1",
            "model": "codex",
            "cost_usd": 0.1,
            "duration_s": 1.0,
            "tool_calls_count": 0,
            "finish_reason": "stop",
            "usage": {},
            "primary_failure_class": "none",
            "failure_event_codes": [],
            "failure_event_code_counts": {},
            "content": "",
        }

    monkeypatch.setattr(run_task, "_execute_flat_task", _execute_flat_task)

    completed = asyncio.run(run_task._run_flat_task(task_path))

    assert completed is True
    assert reports[-1]["delivery_mode"] == "flat"
    assert reports[-1]["task_kind"] == "docs_only"
    assert reports[-1]["planner_lineage"]["planner_task_id"] == "planner-2026-04-04-docs-refresh"
