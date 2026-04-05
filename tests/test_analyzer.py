"""Contract tests for the local task-graph analyzer module."""

from __future__ import annotations

from pathlib import Path

from analyzer import IssueCategory
from analyzer import analyze_history
from task_graph import ExperimentRecord


def test_analyze_history_handles_empty_logs(tmp_path: Path) -> None:
    """The analyzer should tolerate an empty history without proposals."""

    experiment_log = tmp_path / "experiments.jsonl"
    proposals_log = tmp_path / "proposals.jsonl"
    floors_path = tmp_path / "model_floors.json"

    report = analyze_history(
        experiment_log=experiment_log,
        proposals_log=proposals_log,
        floors_path=floors_path,
        db_path=tmp_path / "missing.db",
    )

    assert report.experiments_analyzed == 0
    assert report.tasks_analyzed == 0
    assert report.proposals == []
    assert report.floors_updated == {}
    assert not proposals_log.exists()


def test_analyze_history_emits_model_overkill_proposal(tmp_path: Path) -> None:
    """Repeated clean successes should trigger a downgrade proposal locally."""

    experiment_log = tmp_path / "experiments.jsonl"
    proposals_log = tmp_path / "proposals.jsonl"
    floors_path = tmp_path / "model_floors.json"

    records = [
        ExperimentRecord(
            run_id=f"sample_{idx}",
            task_id="summarize",
            wave=0,
            timestamp=f"2026-04-04T00:00:0{idx}+00:00",
            hypothesis="tier 2 can handle summarize",
            difficulty=2,
            model_selected="gemini/gemini-2.5-pro",
            agent="codex",
            result={"cost_usd": 0.25, "validation_results": []},
            outcome="confirmed",
            git_commit="abc1234",
        )
        for idx in range(5)
    ]
    experiment_log.write_text(
        "\n".join(record.model_dump_json() for record in records) + "\n"
    )

    report = analyze_history(
        experiment_log=experiment_log,
        proposals_log=proposals_log,
        floors_path=floors_path,
        db_path=tmp_path / "missing.db",
    )

    assert report.experiments_analyzed == 5
    assert report.tasks_analyzed == 1
    assert [proposal.category for proposal in report.proposals] == [
        IssueCategory.MODEL_OVERKILL
    ]
    assert proposals_log.exists()
