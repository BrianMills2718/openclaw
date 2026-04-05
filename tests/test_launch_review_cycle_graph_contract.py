"""Tests for review-cycle graph metadata and stage wiring."""

from __future__ import annotations

from pathlib import Path

import launch_review_cycle


def _config(tmp_path: Path) -> dict[str, object]:
    """Build a minimal review-cycle config fixture."""

    return {
        "queue_dir": str(tmp_path / "pending"),
        "workspace_dir": str(tmp_path / "workspace"),
        "cycle": {"timeout_minutes": 120, "checkpoint": "none"},
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
    }


def test_build_graph_includes_final_review_json_reference(tmp_path: Path) -> None:
    """Graph metadata exposes the final review artifact required for gating."""

    graph = launch_review_cycle.build_graph(
        cycle_id="planner-2026-04-04-demo-task",
        project_path=tmp_path / "repo",
        objective="Implement the bounded change.",
        rounds=2,
        config=_config(tmp_path),
        metadata={"delivery_mode": "review_cycle"},
    )

    assert graph["metadata"]["target_repo_path"] == str(tmp_path / "repo")
    assert graph["metadata"]["final_review_json"].endswith("planner-2026-04-04-demo-task/round_2/review.json")
    assert graph["metadata"]["delivery_mode"] == "review_cycle"


def test_build_graph_rounds_one_still_emits_review_and_synthesis_tasks(tmp_path: Path) -> None:
    """One-round graphs still contain the required review and synthesis stages."""

    graph = launch_review_cycle.build_graph(
        cycle_id="planner-2026-04-04-demo-task",
        project_path=tmp_path / "repo",
        objective="Implement the bounded change.",
        rounds=1,
        config=_config(tmp_path),
    )

    assert "implement_r1" in graph["tasks"]
    assert "review_r1" in graph["tasks"]
    assert "synthesize" in graph["tasks"]


def test_default_context_and_synthesis_models_use_agent_runtime() -> None:
    """File-writing graph defaults must resolve to agent-capable models."""

    config = launch_review_cycle._load_config(None)
    graph = launch_review_cycle.build_graph(
        cycle_id="planner-2026-04-04-demo-task",
        project_path=Path("/tmp/demo-repo"),
        objective="Implement the bounded change.",
        rounds=1,
        config=config,
    )

    assert graph["tasks"]["context_init"]["model"] == "codex"
    assert graph["tasks"]["synthesize"]["model"] == "codex"
