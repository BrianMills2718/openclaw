"""Smoke tests for shared runtime import bootstrap roots."""

from __future__ import annotations

import importlib
from pathlib import Path

import run_task


def test_project_meta_runtime_imports_resolve_from_bootstrap() -> None:
    """run_task bootstrap exposes the shared task-graph runtime modules."""

    assert importlib.import_module("scripts.meta.task_graph") is not None
    assert importlib.import_module("scripts.meta.analyzer") is not None
    assert Path(run_task.__file__).exists()
