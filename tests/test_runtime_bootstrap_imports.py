"""Smoke tests for shared runtime import bootstrap roots."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import run_task


def _local_task_graph_module():
    """Import the local task-graph shim lazily to keep collection side effects small."""

    return importlib.import_module("scripts.meta.task_graph")


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


def test_run_task_bootstrap_respects_existing_module_resolution(tmp_path: Path) -> None:
    """run_task bootstrap should not shadow explicit higher-priority module roots."""

    override_root = tmp_path / "override-root"
    (override_root / "llm_client").mkdir(parents=True)
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    try:
        sys.path.insert(0, str(override_root))
        run_task._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert list(sys.path) == [str(override_root), *original_sys_path]
    finally:
        sys.path[:] = original_sys_path


def test_run_task_bootstrap_prepends_missing_module_root(tmp_path: Path) -> None:
    """run_task bootstrap should still expose repo roots when imports would otherwise fail."""

    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    try:
        sys.path[:] = [
            entry
            for entry in original_sys_path
            if not (Path(entry).expanduser().resolve() / "llm_client").is_dir()
        ]
        run_task._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(bootstrap_path.resolve())
    finally:
        sys.path[:] = original_sys_path


def test_run_task_bootstrap_ignores_parent_directory_namespace_false_positive(
    tmp_path: Path,
) -> None:
    """A parent directory containing the repo should not count as the package facade."""

    parent_root = tmp_path / "projects-root"
    repo_root = parent_root / "llm_client"
    package_root = repo_root / "llm_client"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("acall_llm = object()\n")
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    try:
        filtered = [
            entry
            for entry in original_sys_path
            if not ((Path(entry).expanduser().resolve() / "llm_client" / "__init__.py").is_file())
        ]
        sys.path[:] = [str(parent_root), *filtered]
        run_task._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(bootstrap_path.resolve())
    finally:
        sys.path[:] = original_sys_path


def test_local_task_graph_bootstrap_respects_existing_module_resolution(tmp_path: Path) -> None:
    """Explicit higher-priority module paths should not be shadowed by bootstrap roots."""

    local_task_graph = _local_task_graph_module()
    override_root = tmp_path / "override-root"
    (override_root / "llm_client").mkdir(parents=True)
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    try:
        sys.path.insert(0, str(override_root))
        local_task_graph._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert list(sys.path) == [str(override_root), *original_sys_path]
    finally:
        sys.path[:] = original_sys_path


def test_local_task_graph_bootstrap_ignores_parent_directory_namespace_false_positive(
    tmp_path: Path,
) -> None:
    """A parent directory containing the repo should not suppress bootstrap prepending."""

    local_task_graph = _local_task_graph_module()
    parent_root = tmp_path / "projects-root"
    repo_root = parent_root / "llm_client"
    package_root = repo_root / "llm_client"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("acall_llm = object()\n")
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    try:
        filtered = [
            entry
            for entry in original_sys_path
            if not ((Path(entry).expanduser().resolve() / "llm_client" / "__init__.py").is_file())
        ]
        sys.path[:] = [str(parent_root), *filtered]
        local_task_graph._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(bootstrap_path.resolve())
    finally:
        sys.path[:] = original_sys_path


def test_local_task_graph_bootstrap_prepends_missing_module_root(tmp_path: Path) -> None:
    """Bootstrap should still expose local roots when no importable module exists yet."""

    local_task_graph = _local_task_graph_module()
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    try:
        sys.path[:] = [
            entry
            for entry in original_sys_path
            if not (Path(entry).expanduser().resolve() / "llm_client").is_dir()
        ]
        local_task_graph._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(bootstrap_path.resolve())
    finally:
        sys.path[:] = original_sys_path
