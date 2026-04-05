"""Smoke tests for shared runtime import bootstrap roots."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import run_task


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
