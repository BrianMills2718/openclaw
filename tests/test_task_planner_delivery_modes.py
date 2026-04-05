"""Contract tests for planner delivery modes and queue emission."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

import run_task
import task_planner


def _base_task(**overrides: object) -> dict[str, object]:
    """Build one normalized planner task fixture."""

    task: dict[str, object] = {
        "id": "demo-task",
        "priority": "high",
        "agent": "codex",
        "model": "codex",
        "project": str(Path("/tmp/demo-project")),
        "goal_advanced": "Prove end-to-end planner routing",
        "max_budget_usd": 1.0,
        "max_turns": 12,
        "title": "Demo task",
        "objective": "Implement the bounded change and verify it.",
        "acceptance_criteria": ["Tests pass"],
        "task_kind": "code_change",
        "delivery_mode": "review_cycle",
        "file_scope": ["run_task.py"],
        "review_rounds": 1,
    }
    task.update(overrides)
    return task


def test_generate_task_contract_rejects_invalid_delivery_mode_combo() -> None:
    """Code-changing tasks must use the gated review-cycle delivery path."""

    task = _base_task(delivery_mode="flat", review_rounds=None)

    try:
        task_planner._validate_generated_task(task)
    except ValueError as exc:
        assert "code_change tasks must use delivery_mode=review_cycle" in str(exc)
    else:
        raise AssertionError("expected invalid delivery contract to be rejected")


def test_write_flat_task_keeps_existing_markdown_format(tmp_path: Path, monkeypatch) -> None:
    """Flat tasks remain markdown frontmatter tasks consumable by run_task."""

    created_at = datetime(2026, 4, 4, 1, 2, 3, tzinfo=timezone.utc)
    project_dir = tmp_path / "repo"
    project_dir.mkdir()
    task = task_planner._validate_generated_task(
        _base_task(
            id="docs-refresh",
            project=str(project_dir),
            task_kind="docs_only",
            delivery_mode="flat",
            file_scope=["README.md"],
            review_rounds=None,
        )
    )
    monkeypatch.setattr(task_planner, "PENDING_DIR", tmp_path)

    path = task_planner.write_task_file(task, created_at=created_at)

    assert path.suffix == ".md"
    assert path.name == "planner-2026-04-04-docs-refresh.md"
    parsed = run_task.TaskSpec.from_file(path)
    assert parsed.id == "planner-2026-04-04-docs-refresh"
    assert parsed.constraints.file_scope == ["README.md"]
    text = path.read_text()
    assert "# Demo task" in text
    assert "delivery_mode: flat" in text


def test_write_review_cycle_task_emits_graph_yaml_with_deterministic_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Planner review-cycle tasks become deterministic graph queue artifacts."""

    created_at = datetime(2026, 4, 4, 4, 5, 6, tzinfo=timezone.utc)
    queue_dir = tmp_path / "pending"
    workspace_dir = tmp_path / "workspace"
    project_dir = tmp_path / "repo"
    project_dir.mkdir()
    monkeypatch.setattr(task_planner, "PENDING_DIR", queue_dir)
    task = task_planner._validate_generated_task(
        _base_task(project=str(project_dir), file_scope=["run_task.py", "task_planner.py"])
    )

    path = task_planner.write_task_file(
        task,
        created_at=created_at,
        config={
            "queue_dir": str(queue_dir),
            "workspace_dir": str(workspace_dir),
            "cycle": {"timeout_minutes": 90, "checkpoint": "none"},
            "agents": {
                "implement": {"agent": "codex", "model": None, "difficulty": 3, "mcp_servers": []},
                "review": {
                    "agent": "direct",
                    "model": "gpt-5.2-pro",
                    "reasoning_effort": "xhigh",
                    "difficulty": 5,
                    "mcp_servers": [],
                },
                "context": {
                    "agent": "codex",
                    "model": "gemini/gemini-2.5-flash",
                    "difficulty": 2,
                    "mcp_servers": [],
                },
                "synthesis": {
                    "agent": "codex",
                    "model": "gemini/gemini-2.5-flash",
                    "difficulty": 2,
                    "mcp_servers": [],
                },
            },
            "context_pack": {"enabled": True, "filename": "context_pack.md"},
            "validation": {"require_json_review": True},
        },
    )

    assert path.suffix == ".yaml"
    assert path.name == "planner-2026-04-04-demo-task.yaml"
    payload = yaml.safe_load(path.read_text())
    assert payload["graph"]["id"] == "planner-2026-04-04-demo-task"
    assert payload["metadata"]["delivery_mode"] == "review_cycle"
    assert payload["metadata"]["planner_lineage"]["planner_task_id"] == "planner-2026-04-04-demo-task"
    assert payload["metadata"]["file_scope"] == ["run_task.py", "task_planner.py"]
    assert payload["tasks"]["implement_r1"]["agent"] == "codex"
    assert payload["tasks"]["implement_r1"]["model"] == "codex"


def test_write_review_cycle_task_normalizes_workspace_lanes_to_codex(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Review-cycle graph lanes normalize to the proven Codex workspace runtime."""

    created_at = datetime(2026, 4, 4, 4, 5, 6, tzinfo=timezone.utc)
    queue_dir = tmp_path / "pending"
    project_dir = tmp_path / "repo"
    project_dir.mkdir()
    monkeypatch.setattr(task_planner, "PENDING_DIR", queue_dir)
    task = task_planner._validate_generated_task(
        _base_task(
            agent="claude-code",
            model="claude-3-5-sonnet-20240620",
            project=str(project_dir),
        )
    )

    path = task_planner.write_task_file(
        task,
        created_at=created_at,
        config={
            "queue_dir": str(queue_dir),
            "workspace_dir": ".openclaw/review-cycles",
            "cycle": {"timeout_minutes": 90, "checkpoint": "none"},
            "agents": {
                "implement": {"agent": "codex", "model": None, "difficulty": 3, "mcp_servers": []},
                "review": {
                    "agent": "direct",
                    "model": "gpt-5.2-pro",
                    "reasoning_effort": "xhigh",
                    "difficulty": 5,
                    "mcp_servers": [],
                },
                "context": {"agent": "codex", "model": None, "difficulty": 2, "mcp_servers": []},
                "synthesis": {"agent": "codex", "model": None, "difficulty": 2, "mcp_servers": []},
            },
            "context_pack": {"enabled": False, "filename": "context_pack.md"},
            "validation": {"require_json_review": True},
        },
    )

    payload = yaml.safe_load(path.read_text())
    assert payload["tasks"]["implement_r1"]["agent"] == "codex"
    assert payload["tasks"]["implement_r1"]["model"] == "codex"
    assert payload["tasks"]["synthesize"]["agent"] == "codex"
    assert payload["tasks"]["synthesize"]["model"] == "codex"


def test_validate_generated_task_uses_explicit_single_target_project(monkeypatch, tmp_path: Path) -> None:
    """A single explicit target project should override planner project drift."""

    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setattr(task_planner, "TARGET_PROJECTS", str(target))

    normalized = task_planner._validate_generated_task(
        _base_task(project=str(target / "openclaw"))
    )

    assert normalized["project"] == str(target.resolve())


def test_validate_generated_task_rejects_missing_project_path(monkeypatch, tmp_path: Path) -> None:
    """Planner output should not be allowed to reference nonexistent repos."""

    monkeypatch.setattr(task_planner, "TARGET_PROJECTS", "")
    missing = tmp_path / "missing-repo"

    try:
        task_planner._validate_generated_task(_base_task(project=str(missing)))
    except ValueError as exc:
        assert "planner task project path does not exist" in str(exc)
    else:
        raise AssertionError("expected nonexistent planner project path to be rejected")
