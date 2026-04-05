"""Tests for graph-level review and commit gating."""

from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import yaml

import run_task


def _install_fake_graph_modules(monkeypatch, *, status: str = "completed") -> None:
    """Provide fake graph runner modules so _run_graph_task stays unit-testable."""

    analyzer_module = types.ModuleType("scripts.meta.analyzer")
    analyzer_module.analyze_run = lambda *args, **kwargs: SimpleNamespace(proposals=[])
    task_graph_module = types.ModuleType("scripts.meta.task_graph")
    task_graph_module.ExecutionReport = object
    task_graph_module.load_graph = lambda path: SimpleNamespace(
        meta=SimpleNamespace(id=Path(path).stem),
        tasks={"implement_r1": {}, "review_r1": {}, "synthesize": {}},
        waves=[["implement_r1"], ["review_r1"], ["synthesize"]],
    )

    async def _run_graph(*args, **kwargs):
        return SimpleNamespace(
            status=status,
            total_cost_usd=0.1,
            total_duration_s=1.0,
            waves_completed=3,
            waves_total=3,
            task_results=[],
        )

    task_graph_module.run_graph = _run_graph
    monkeypatch.setitem(sys.modules, "scripts.meta.analyzer", analyzer_module)
    monkeypatch.setitem(sys.modules, "scripts.meta.task_graph", task_graph_module)


def _graph_file(tmp_path: Path, review_status: str = "pass") -> Path:
    """Create one planner-generated review-cycle graph and its review artifact."""

    repo = tmp_path / "repo"
    repo.mkdir()
    review_path = tmp_path / "workspace" / "graph-1" / "round_1" / "review.json"
    review_path.parent.mkdir(parents=True)
    review_path.write_text(json.dumps({"status": review_status, "summary": "review summary"}))
    task_path = tmp_path / "graph-1.yaml"
    task_path.write_text(
        yaml.safe_dump(
            {
                "graph": {"id": "graph-1", "description": "demo", "timeout_minutes": 30, "checkpoint": "none"},
                "tasks": {"implement_r1": {}, "review_r1": {}, "synthesize": {}},
                "metadata": {
                    "delivery_mode": "review_cycle",
                    "task_kind": "code_change",
                    "target_repo_path": str(repo),
                    "final_review_json": str(review_path),
                    "planner_lineage": {"planner_task_id": "planner-2026-04-04-demo-task"},
                },
            },
            sort_keys=False,
        )
    )
    return task_path


def test_graph_routes_to_failed_when_final_review_status_is_needs_changes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Review status must semantically approve the graph before completion."""

    _install_fake_graph_modules(monkeypatch)
    task_path = _graph_file(tmp_path, review_status="needs_changes")
    reports: list[dict[str, object]] = []

    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.0))
    monkeypatch.setattr(run_task, "_load_mcp_registry", lambda: {})
    monkeypatch.setattr(run_task, "_run_graph_preflight", lambda graph, mcp_configs: {"passed": True})
    monkeypatch.setattr(run_task, "_move_task", lambda path, destination: path)
    monkeypatch.setattr(run_task, "_write_task_report", lambda task_ref, payload: reports.append(payload) or tmp_path / "report.json")
    monkeypatch.setattr(run_task, "_detect_commit_evidence", lambda project_path, started_at: {"required": True, "passed": True, "commit_detected": True})

    completed = asyncio.run(run_task._run_graph_task(task_path))

    assert completed is False
    assert reports[-1]["status"] == "failed"
    assert reports[-1]["failure_event_codes"] == ["OPENCLAW_GRAPH_REVIEW_FAILED"]
    assert reports[-1]["review_gate"]["status"] == "needs_changes"


def test_graph_routes_to_failed_when_commit_missing_after_review_pass(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Review pass alone is not enough for planner-generated review-cycle graphs."""

    _install_fake_graph_modules(monkeypatch)
    task_path = _graph_file(tmp_path, review_status="pass")
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
            "passed": False,
            "commit_detected": False,
            "reason": "latest commit is not newer than task start",
        },
    )

    completed = asyncio.run(run_task._run_graph_task(task_path))

    assert completed is False
    assert reports[-1]["status"] == "failed"
    assert reports[-1]["failure_event_codes"] == ["OPENCLAW_GRAPH_COMMIT_MISSING"]
    assert reports[-1]["commit_evidence"]["passed"] is False


def test_graph_routes_to_completed_when_review_pass_and_commit_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Planner-generated review-cycle graphs complete only with both gates satisfied."""

    _install_fake_graph_modules(monkeypatch)
    task_path = _graph_file(tmp_path, review_status="pass")
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

    completed = asyncio.run(run_task._run_graph_task(task_path))

    assert completed is True
    assert reports[-1]["status"] == "completed"
    assert reports[-1]["review_gate"]["passed"] is True
    assert reports[-1]["commit_evidence"]["commit_detected"] is True
