"""Tests for graph-task post-success recovery in the local shim."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.meta import task_graph


def test_recover_postsuccess_failure_when_validators_now_pass(monkeypatch) -> None:
    """Failed graph tasks can recover when their declared validators pass."""

    monkeypatch.setattr(
        task_graph._MODULE,
        "run_validators",
        lambda validators: [{"passed": True, "reason": "ok", "type": "file_exists", "value": "context_pack.md"}],
    )
    task = SimpleNamespace(id="context_init", validators=[{"type": "file_exists"}])
    result = SimpleNamespace(
        task_id="context_init",
        status=task_graph.TaskStatus.FAILED,
        wave=0,
        model_selected="codex",
        difficulty=2,
        duration_s=1.0,
        cost_usd=0.0,
        tokens_in=0,
        tokens_out=0,
        validation_results=[],
        agent_output=None,
        reasoning_effort=None,
        background_mode=None,
        requested_model=None,
        resolved_model=None,
        routing_trace=None,
        spec_hash="abc123",
        uncertainties=[],
        error="generic agent failure after writing output",
    )

    recovered = task_graph._recover_postsuccess_failure(task, result)

    assert recovered.status == task_graph.TaskStatus.COMPLETED
    assert recovered.validation_results[0].passed is True
