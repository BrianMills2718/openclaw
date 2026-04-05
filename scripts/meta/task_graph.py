"""Moltbot-local task-graph shim with narrow post-success recovery.

The canonical task-graph runtime now lives in this repo at the top-level
`task_graph.py`. This shim preserves the import surface
`scripts.meta.task_graph` for callers that still expect the extracted layout,
while adding the local post-success recovery rule discovered during end-to-end
proof runs: if a workspace-agent task returns `FAILED` but its declared
validators now pass, treat that task as completed and allow the graph to
continue.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def _module_facade_exists(root: Path, module_name: str) -> bool:
    """Return True when a root exposes a concrete importable module facade."""

    package_dir = root / module_name
    return (package_dir / "__init__.py").is_file() or (root / f"{module_name}.py").is_file()


def _pythonpath_module_root(module_name: str) -> Path | None:
    """Return the first PYTHONPATH entry that exposes the requested module facade."""

    raw_pythonpath = os.environ.get("PYTHONPATH", "")
    if not raw_pythonpath:
        return None
    for entry in raw_pythonpath.split(os.pathsep):
        if not entry:
            continue
        try:
            root = Path(entry).expanduser().resolve()
        except OSError:
            continue
        if root.is_dir() and _module_facade_exists(root, module_name):
            return root
    return None


def _module_root_already_present(module_name: str) -> bool:
    """Return True when an earlier sys.path entry already exposes the module root."""

    for entry in sys.path:
        try:
            root = Path(entry).expanduser().resolve()
        except OSError:
            continue
        if not root.exists() or not root.is_dir():
            continue
        if _module_facade_exists(root, module_name):
            return True
    return False


def _prepend_repo_root_if_present(path: Path, *, module_name: str | None = None) -> None:
    """Prepend a repo root when it exists and no higher-priority module is set."""

    if not path.is_dir():
        return
    if module_name:
        preferred_root = _pythonpath_module_root(module_name)
        if preferred_root is not None:
            preferred = str(preferred_root)
            if preferred in sys.path:
                sys.path.remove(preferred)
            sys.path.insert(0, preferred)
            return
        if _module_root_already_present(module_name):
            return
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_prepend_repo_root_if_present(_REPO_ROOT)

_PROJECTS_ROOT = Path(
    os.environ.get("PROJECTS_ROOT", str(Path.home() / "projects"))
).expanduser().resolve()
for _repo_name in ("llm_client", "agentic_scaffolding"):
    _prepend_repo_root_if_present(_PROJECTS_ROOT / _repo_name, module_name=_repo_name)
_LOCAL_TASK_GRAPH = _REPO_ROOT / "task_graph.py"

if not _LOCAL_TASK_GRAPH.is_file():
    raise FileNotFoundError(
        "Expected canonical task_graph implementation at "
        f"{_LOCAL_TASK_GRAPH}"
    )

_SPEC = importlib.util.spec_from_file_location(
    "_moltbot_task_graph_runtime",
    _LOCAL_TASK_GRAPH,
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load task_graph spec from {_LOCAL_TASK_GRAPH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

TaskStatus = _MODULE.TaskStatus
TaskDef = _MODULE.TaskDef
GraphMeta = _MODULE.GraphMeta
TaskGraph = _MODULE.TaskGraph
Uncertainty = _MODULE.Uncertainty
TaskResult = _MODULE.TaskResult
ExperimentRecord = _MODULE.ExperimentRecord
ExecutionReport = _MODULE.ExecutionReport
load_graph = _MODULE.load_graph
toposort_waves = _MODULE.toposort_waves
_validate_dag = _MODULE._validate_dag
_resolve_task_model = _MODULE._resolve_task_model
_resolve_templates = _MODULE._resolve_templates
_is_agent_model_family = _MODULE._is_agent_model_family
_make_experiment_record = _MODULE._make_experiment_record
_append_experiment = _MODULE._append_experiment
_git_checkpoint = _MODULE._git_checkpoint

_ORIGINAL_EXECUTE_TASK = _MODULE._execute_task

TaskDef.model_rebuild(force=True, _types_namespace={"Any": Any})
TaskGraph.model_rebuild(
    force=True,
    _types_namespace={"Any": Any, "GraphMeta": GraphMeta, "TaskDef": TaskDef},
)
TaskResult.model_rebuild(
    force=True,
    _types_namespace={
        "Any": Any,
        "TaskStatus": TaskStatus,
        "ValidationResult": _MODULE.ValidationResult,
        "Uncertainty": Uncertainty,
    },
)
ExecutionReport.model_rebuild(
    force=True,
    _types_namespace={"Any": Any, "TaskResult": TaskResult},
)
ExperimentRecord.model_rebuild(force=True, _types_namespace={"Any": Any})


def _recover_postsuccess_failure(
    task: Any,
    result: Any,
) -> Any:
    """Recover a failed agent task when its declared validators now pass."""

    if getattr(result, "status", None) != TaskStatus.FAILED:
        return result
    validators = getattr(task, "validators", None) or []
    if not validators:
        return result

    if (
        getattr(task, "agent", None) == "direct"
        and isinstance(getattr(result, "agent_output", None), str)
        and result.agent_output.strip()
    ):
        outputs = getattr(task, "outputs", None)
        if isinstance(outputs, dict) and len(outputs) == 1:
            output_path = next(iter(outputs.values()))
            if isinstance(output_path, str) and output_path.strip():
                output_file = Path(output_path).expanduser()
                if not output_file.exists():
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    output_file.write_text(result.agent_output.strip() + "\n")
                    logger.warning(
                        "Materialized direct task output for %s at %s before validator replay",
                        getattr(task, "id", "<unknown>"),
                        output_file,
                    )

    validation_results = _MODULE.run_validators(validators)
    def _validator_passed(item: Any) -> bool:
        if isinstance(item, dict):
            return bool(item.get("passed"))
        return bool(getattr(item, "passed", False))

    if not all(_validator_passed(v) for v in validation_results):
        return result

    logger.warning(
        "Recovering failed task-graph task %s after validators passed",
        getattr(task, "id", "<unknown>"),
    )
    return TaskResult(
        task_id=result.task_id,
        status=TaskStatus.COMPLETED,
        wave=result.wave,
        model_selected=result.model_selected,
        difficulty=result.difficulty,
        duration_s=result.duration_s,
        cost_usd=result.cost_usd,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        validation_results=validation_results,
        agent_output=result.agent_output,
        reasoning_effort=result.reasoning_effort,
        background_mode=result.background_mode,
        requested_model=result.requested_model,
        resolved_model=result.resolved_model,
        routing_trace=result.routing_trace,
        spec_hash=result.spec_hash,
        uncertainties=result.uncertainties,
    )


async def _execute_task(
    *,
    task: Any,
    wave_idx: int,
    graph: Any,
    model_floors: dict[str, dict[str, Any]] | None,
    mcp_server_configs: dict[str, dict[str, Any]],
    completed_results: dict[str, Any],
    completed_outputs: dict[str, dict[str, str]],
    working_directory: str | None,
) -> Any:
    """Delegate to the canonical executor and apply narrow post-success recovery."""

    result = await _ORIGINAL_EXECUTE_TASK(
        task=task,
        wave_idx=wave_idx,
        graph=graph,
        model_floors=model_floors,
        mcp_server_configs=mcp_server_configs,
        completed_results=completed_results,
        completed_outputs=completed_outputs,
        working_directory=working_directory,
    )
    return _recover_postsuccess_failure(task, result)


_MODULE._execute_task = _execute_task
run_graph = _MODULE.run_graph
