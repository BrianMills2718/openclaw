"""Smoke tests for shared runtime import bootstrap roots."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import run_task
import scripts.meta.task_graph as local_task_graph


def test_project_meta_runtime_imports_resolve_from_bootstrap() -> None:
    """run_task bootstrap exposes the shared task-graph runtime modules."""

    assert importlib.import_module("scripts.meta.task_graph") is not None
    assert importlib.import_module("scripts.meta.analyzer") is not None
    assert Path(run_task.__file__).exists()


def test_runtime_env_defaults_codex_transport_to_auto(monkeypatch) -> None:
    """The runtime should default Codex agent tasks to auto transport."""

    monkeypatch.delenv("LLM_CLIENT_CODEX_TRANSPORT", raising=False)

    run_task._bootstrap_runtime_env_defaults()

    assert os.environ["LLM_CLIENT_CODEX_TRANSPORT"] == "auto"


def test_runtime_env_defaults_preserve_explicit_codex_transport(monkeypatch) -> None:
    """Explicit operator transport settings should win over runtime defaults."""

    monkeypatch.setenv("LLM_CLIENT_CODEX_TRANSPORT", "cli")

    run_task._bootstrap_runtime_env_defaults()

    assert os.environ["LLM_CLIENT_CODEX_TRANSPORT"] == "cli"


def test_local_task_graph_bootstrap_respects_existing_module_resolution(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Explicit higher-priority module paths should not be shadowed by bootstrap roots."""

    bootstrap_path = tmp_path / "llm_client"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    monkeypatch.setattr(local_task_graph.importlib.util, "find_spec", lambda name: object())

    local_task_graph._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")

    assert list(sys.path) == original_sys_path


def test_local_task_graph_bootstrap_prepends_missing_module_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Bootstrap should still expose local roots when no importable module exists yet."""

    bootstrap_path = tmp_path / "llm_client"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    monkeypatch.setattr(local_task_graph.importlib.util, "find_spec", lambda name: None)

    try:
        local_task_graph._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(bootstrap_path.resolve())
    finally:
        sys.path[:] = original_sys_path
