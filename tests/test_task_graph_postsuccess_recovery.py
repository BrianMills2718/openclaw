"""Tests for graph-task post-success recovery in the local shim."""

from __future__ import annotations

from pathlib import Path
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


def test_recover_postsuccess_failure_materializes_direct_single_output(tmp_path: Path, monkeypatch) -> None:
    """Direct-task text output should be written to its declared output file before validator replay."""

    review_path = tmp_path / "review.json"

    def _run_validators(validators):
        del validators
        return [
            {
                "passed": review_path.exists(),
                "reason": None if review_path.exists() else "missing",
                "type": "file_exists",
                "value": str(review_path),
            }
        ]

    monkeypatch.setattr(task_graph._MODULE, "run_validators", _run_validators)
    task = SimpleNamespace(
        id="review_r1",
        agent="direct",
        validators=[{"type": "file_exists", "path": str(review_path)}],
        outputs={"review_json": str(review_path)},
    )
    result = SimpleNamespace(
        task_id="review_r1",
        status=task_graph.TaskStatus.FAILED,
        wave=1,
        model_selected="gpt-5.2-pro",
        difficulty=5,
        duration_s=1.0,
        cost_usd=0.0,
        tokens_in=0,
        tokens_out=0,
        validation_results=[],
        agent_output='{"status":"pass","summary":"ok","critical_issues":[],"next_objective":"none"}',
        reasoning_effort="xhigh",
        background_mode=None,
        requested_model="gpt-5.2-pro",
        resolved_model="openrouter/openai/gpt-5.2-pro",
        routing_trace={"selected_model": "openrouter/openai/gpt-5.2-pro"},
        spec_hash="abc123",
        uncertainties=[],
        error="validator failed before direct output was materialized",
    )

    recovered = task_graph._recover_postsuccess_failure(task, result)

    assert review_path.read_text().strip().startswith('{"status":"pass"')
    assert recovered.status == task_graph.TaskStatus.COMPLETED
    assert recovered.validation_results[0].passed is True
