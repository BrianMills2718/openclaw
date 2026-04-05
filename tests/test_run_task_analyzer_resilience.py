"""Tests for optional analyzer failure handling on graph runs."""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import yaml

import run_task


def test_graph_analyzer_failure_does_not_abort_routing(monkeypatch, tmp_path: Path) -> None:
    """Analyzer exceptions should not fail an otherwise completed graph run."""

    analyzer_module = types.ModuleType("scripts.meta.analyzer")
    def _raise(*args, **kwargs):
        raise RuntimeError("analyzer blew up")
    analyzer_module.analyze_run = _raise

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
            task_results=[],
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
                    "planner_lineage": {"planner_task_id": "planner-2026-04-05-demo-task"},
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
            "commit_timestamp": "2026-04-05T01:02:03+00:00",
        },
    )

    completed = asyncio.run(run_task._run_graph_task(task_path))

    assert completed is True
    assert reports[-1]["status"] == "completed"
    decision_events = reports[-1]["decision_provenance"]["events"]
    assert any(event["selected_action"] == "skip_failed_analyzer" for event in decision_events)
