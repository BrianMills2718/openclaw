"""Tests for the llm_client review-cycle OpenClaw adapter."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import yaml

import launch_llm_review_cycle
import run_task


def _write_review_cycle_task(tmp_path: Path) -> Path:
    task_file = tmp_path / "review_cycle_task.json"
    task_file.write_text(
        json.dumps(
            {
                "task_id": "adapter-smoke",
                "artifact_paths": ["paper.md"],
                "workspace_path": str(tmp_path / "repo"),
                "out_dir": str(tmp_path / "review-run"),
                "max_cycles": 1,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "repo").mkdir()
    return task_file


def test_llm_review_cycle_launcher_builds_sidecar_metadata(tmp_path: Path) -> None:
    """The launcher emits a graph wrapper without replacing report schemas."""

    task_file = _write_review_cycle_task(tmp_path)
    graph = launch_llm_review_cycle.build_graph(
        cycle_id="llm-review-cycle-adapter-smoke",
        review_cycle_task_file=task_file,
    )

    assert graph["tasks"] == {}
    assert graph["metadata"]["delivery_mode"] == "llm_review_cycle"
    assert graph["metadata"]["task_kind"] == "review_cycle"
    assert graph["metadata"]["review_cycle_task_file"] == str(task_file.resolve())
    assert graph["metadata"]["review_cycle_artifacts_path"].endswith("review_cycle_artifacts.json")


def test_run_task_executes_llm_review_cycle_adapter(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """OpenClaw reports link the llm_client sidecar/signoff artifacts."""

    task_file = _write_review_cycle_task(tmp_path)
    graph = launch_llm_review_cycle.build_graph(
        cycle_id="llm-review-cycle-adapter-smoke",
        review_cycle_task_file=task_file,
    )
    graph_path = tmp_path / "llm-review-cycle-adapter-smoke.yaml"
    graph_path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
    reports: list[dict[str, object]] = []

    def fake_run(command, cwd, capture_output, text, check):
        run_dir = tmp_path / "review-run"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "signoff.json").write_text(
            json.dumps(
                {
                    "task_id": "adapter-smoke",
                    "final_status": "max_cycles",
                    "cycles_completed": 1,
                    "final_verdict": "blocker",
                    "stop_reason": "Maximum review cycles reached.",
                    "budget_spent_usd": 0.25,
                    "actionable_count": 1,
                    "discussion_queue_count": 0,
                    "artifact_index": {"signoff.json": "signoff.json"},
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="review-cycle status: max_cycles", stderr="")

    monkeypatch.setattr(run_task, "_check_daily_budget", lambda: (True, 0.0))
    monkeypatch.setattr(run_task, "_move_task", lambda path, destination: path)
    monkeypatch.setattr(run_task, "_write_task_report", lambda task_ref, payload: reports.append(payload) or tmp_path / "report.json")
    monkeypatch.setattr(run_task.subprocess, "run", fake_run)

    completed = asyncio.run(run_task._run_graph_task(graph_path))

    assert completed is True
    report = reports[-1]
    assert report["status"] == "completed"
    assert report["delivery_mode"] == "llm_review_cycle"
    assert report["review_cycle_artifacts"]["signoff_present"] is True
    sidecar_path = Path(report["review_cycle_artifacts"]["path"])
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["schema_version"] == "openclaw.review_cycle_artifacts.v1"
    assert sidecar["signoff"]["budget_spent_usd"] == 0.25
    assert report["run"]["total_cost_usd"] == 0.25
    assert report["task_results"][0]["task_id"] == "llm_client_review_cycle"
