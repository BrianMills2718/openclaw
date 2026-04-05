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


def test_graph_runtime_modules_import_task_graph_before_analyzer_preserves_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Graph runtime imports must load the shim before analyzer-side llm_client imports."""

    repo_root = tmp_path / "repo-root"
    scripts_meta_root = repo_root / "scripts" / "meta"
    scripts_meta_root.mkdir(parents=True)
    (repo_root / "scripts" / "__init__.py").write_text("")
    (scripts_meta_root / "__init__.py").write_text("")

    override_root = tmp_path / "override-root"
    override_package = override_root / "llm_client"
    override_package.mkdir(parents=True)
    (override_package / "__init__.py").write_text("SOURCE = 'override'\n")

    canonical_root = tmp_path / "canonical-root"
    canonical_package = canonical_root / "llm_client"
    canonical_package.mkdir(parents=True)
    (canonical_package / "__init__.py").write_text("SOURCE = 'canonical'\n")

    (scripts_meta_root / "task_graph.py").write_text(
        "import os\n"
        "import sys\n"
        "\n"
        "preferred = os.environ['TEST_OVERRIDE_ROOT']\n"
        "if preferred in sys.path:\n"
        "    sys.path.remove(preferred)\n"
        "sys.path.insert(0, preferred)\n"
        "\n"
        "class ExecutionReport:\n"
        "    pass\n"
        "\n"
        "def load_graph(*args, **kwargs):\n"
        "    return None\n"
        "\n"
        "async def run_graph(*args, **kwargs):\n"
        "    return None\n"
    )
    (scripts_meta_root / "analyzer.py").write_text(
        "import llm_client\n"
        "\n"
        "def analyze_run(*args, **kwargs):\n"
        "    return llm_client.SOURCE\n"
    )

    monkeypatch.setenv("TEST_OVERRIDE_ROOT", str(override_root))
    original_sys_path = list(sys.path)
    module_names = [
        "scripts",
        "scripts.meta",
        "scripts.meta.task_graph",
        "scripts.meta.analyzer",
        "llm_client",
    ]
    original_modules = {name: sys.modules.get(name) for name in module_names}

    try:
        sys.path[:] = [str(repo_root), str(canonical_root), *original_sys_path]
        for name in module_names:
            sys.modules.pop(name, None)

        analyze_run, _, _, _ = run_task._load_graph_runtime_modules()
        llm_client_module = importlib.import_module("llm_client")

        assert llm_client_module.SOURCE == "override"
        assert analyze_run() == "override"
    finally:
        sys.path[:] = original_sys_path
        for name in module_names:
            sys.modules.pop(name, None)
        for name, module in original_modules.items():
            if module is not None:
                sys.modules[name] = module


def test_runtime_env_defaults_codex_transport_to_cli(monkeypatch) -> None:
    """The runtime should default Codex agent tasks to explicit CLI transport."""

    monkeypatch.delenv("LLM_CLIENT_CODEX_TRANSPORT", raising=False)

    run_task._bootstrap_runtime_env_defaults()

    assert os.environ["LLM_CLIENT_CODEX_TRANSPORT"] == "cli"


def test_runtime_env_defaults_preserve_explicit_codex_transport(monkeypatch) -> None:
    """Explicit operator transport settings should win over runtime defaults."""

    monkeypatch.setenv("LLM_CLIENT_CODEX_TRANSPORT", "auto")

    run_task._bootstrap_runtime_env_defaults()

    assert os.environ["LLM_CLIENT_CODEX_TRANSPORT"] == "auto"


def test_run_task_bootstrap_respects_existing_module_resolution(tmp_path: Path) -> None:
    """run_task bootstrap should not shadow explicit higher-priority module roots."""

    override_root = tmp_path / "override-root"
    package_root = override_root / "llm_client"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("acall_llm = object()\n")
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


def test_run_task_bootstrap_prefers_pythonpath_module_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Explicit PYTHONPATH worktree roots should be promoted ahead of canonical fallback."""

    override_root = tmp_path / "override-root"
    package_root = override_root / "llm_client"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("acall_llm = object()\n")
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    monkeypatch.setenv("PYTHONPATH", str(override_root))

    try:
        sys.path[:] = [entry for entry in original_sys_path if str(override_root) not in entry]
        run_task._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(override_root.resolve())
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
    package_root = override_root / "llm_client"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("acall_llm = object()\n")
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


def test_local_task_graph_bootstrap_prefers_pythonpath_module_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The local shim should prioritize explicit PYTHONPATH module roots too."""

    local_task_graph = _local_task_graph_module()
    override_root = tmp_path / "override-root"
    package_root = override_root / "llm_client"
    package_root.mkdir(parents=True)
    (package_root / "__init__.py").write_text("acall_llm = object()\n")
    bootstrap_path = tmp_path / "bootstrap-root"
    bootstrap_path.mkdir()
    original_sys_path = list(sys.path)

    monkeypatch.setenv("PYTHONPATH", str(override_root))

    try:
        sys.path[:] = [entry for entry in original_sys_path if str(override_root) not in entry]
        local_task_graph._prepend_repo_root_if_present(bootstrap_path, module_name="llm_client")
        assert sys.path[0] == str(override_root.resolve())
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
