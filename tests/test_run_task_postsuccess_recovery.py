"""Regression tests for bounded post-success runtime recovery."""

from __future__ import annotations

from pathlib import Path

import run_task


def _task(tmp_path: Path) -> run_task.TaskSpec:
    """Build a minimal task spec for recovery tests."""

    return run_task.TaskSpec(
        id="test-task",
        priority="high",
        agent="claude-code",
        project=str(tmp_path),
        created="2026-04-03T00:00:00Z",
        status="pending",
        constraints=run_task.TaskConstraints(),
        title="Test task",
        objective="Verify recovery logic",
        acceptance_criteria="",
        context="",
        source_path=tmp_path / "task.md",
        model="claude-code",
    )


def test_recoverable_reason_matches_generic_claude_exit() -> None:
    """The measured Claude exit-code wrapper error remains recoverable."""

    reason = run_task._recoverable_postsuccess_agent_error_reason(
        "LLMError",
        "Command failed with exit code 1 (exit code: 1)\n"
        "Error output: Check stderr output for details",
    )

    assert reason == "generic claude agent subprocess exit after bounded work"


def test_recoverable_reason_preserves_empty_error_path() -> None:
    """Empty SDK errors stay recoverable for post-validation fallback."""

    reason = run_task._recoverable_postsuccess_agent_error_reason("LLMError", "")

    assert reason == "empty agent error after bounded work"


def test_meaningful_new_status_lines_ignores_hook_log_only() -> None:
    """Hook-log-only churn is not treated as meaningful recovery evidence."""

    assert (
        run_task._meaningful_new_status_lines(
            "",
            "?? .claude/hook_log.jsonl",
        )
        == []
    )


def test_meaningful_new_status_lines_keeps_bounded_source_edits() -> None:
    """Real source-file edits remain visible to the recovery gate."""

    assert run_task._meaningful_new_status_lines(
        "",
        " M README.md\n M src/json_diff/cli.py\n?? .claude/hook_log.jsonl",
    ) == [" M README.md", " M src/json_diff/cli.py"]


def test_postsuccess_recovery_requires_commit_or_meaningful_changes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Recovery requires commit evidence or meaningful bounded changes."""

    task = _task(tmp_path)
    error_text = (
        "Command failed with exit code 1 (exit code: 1)\n"
        "Error output: Check stderr output for details"
    )

    monkeypatch.setattr(run_task, "_agent_committed", lambda task: False)
    monkeypatch.setattr(run_task, "_agent_produced_meaningful_changes", lambda task, pre_status: [])
    assert run_task._postsuccess_recovery_context(task, "LLMError", error_text, "") is None

    monkeypatch.setattr(run_task, "_agent_committed", lambda task: True)
    monkeypatch.setattr(run_task, "_agent_produced_meaningful_changes", lambda task, pre_status: [])
    assert (
        run_task._postsuccess_recovery_context(task, "LLMError", error_text, "")["reason"]
        == "generic claude agent subprocess exit after bounded work"
    )

    monkeypatch.setattr(run_task, "_agent_committed", lambda task: False)
    monkeypatch.setattr(
        run_task,
        "_agent_produced_meaningful_changes",
        lambda task, pre_status: [" M src/json_diff/cli.py"],
    )
    context = run_task._postsuccess_recovery_context(task, "LLMError", error_text, "")
    assert context is not None
    assert context["committed"] is False
    assert context["changed_lines"] == [" M src/json_diff/cli.py"]


def test_non_measured_error_family_does_not_recover(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Unrelated runtime failures should still route to failure."""

    task = _task(tmp_path)
    monkeypatch.setattr(run_task, "_agent_committed", lambda task: True)

    assert (
        run_task._postsuccess_recovery_context(
            task,
            "RuntimeError",
            "permission denied while starting sandbox",
            "",
        )
        is None
    )
