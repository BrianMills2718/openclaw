"""Contract tests for the local task-graph runtime module."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from task_graph import load_graph
from task_graph import run_graph


def test_load_graph_populates_execution_waves(tmp_path: Path) -> None:
    """The local runtime should parse a DAG and derive deterministic waves."""

    graph_path = tmp_path / "graph.yaml"
    graph_path.write_text(
        """
graph:
  id: sample
tasks:
  first:
    difficulty: 0
    prompt: "alpha"
  second:
    difficulty: 0
    prompt: "beta"
    depends_on: [first]
  third:
    difficulty: 0
    prompt: "gamma"
    depends_on: [first]
""".strip()
    )

    graph = load_graph(graph_path)

    assert graph.meta.id == "sample"
    assert graph.waves == [["first"], ["second", "third"]]


def test_load_graph_rejects_unknown_dependencies(tmp_path: Path) -> None:
    """Bad DAGs should fail before the runtime starts dispatching work."""

    graph_path = tmp_path / "graph.yaml"
    graph_path.write_text(
        """
graph:
  id: broken
tasks:
  only:
    difficulty: 0
    prompt: "alpha"
    depends_on: [missing]
""".strip()
    )

    with pytest.raises(ValueError, match="doesn't exist"):
        load_graph(graph_path)


def test_run_graph_dry_run_keeps_execution_local(tmp_path: Path) -> None:
    """Dry-run should exercise the runtime contract without dispatching agents."""

    graph_path = tmp_path / "graph.yaml"
    graph_path.write_text(
        """
graph:
  id: dry-run
tasks:
  scripted:
    difficulty: 0
    prompt: "noop"
""".strip()
    )

    report = asyncio.run(run_graph(load_graph(graph_path), dry_run=True))

    assert report.status == "completed"
    assert report.waves_completed == 1
    assert [result.task_id for result in report.task_results] == ["scripted"]
