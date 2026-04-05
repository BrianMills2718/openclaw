#!/usr/bin/env python3
"""Task runner for the multi-agent system.

Reads task files, executes them via llm_client agent SDKs,
validates results, and archives to completed/ or failed/.

Supports two formats:
- .md files: Flat tasks with YAML frontmatter (original format)
- .yaml/.yml files: Task graph DAGs via llm_client.task_graph

Usage:
    run_task.py [task_file]          # Run a specific task
    run_task.py                      # Run highest-priority pending task
    run_task.py --list               # List pending tasks
    run_task.py --dry-run [file]     # Parse and show what would run
"""

import argparse
import asyncio
import fcntl
import json
import logging
import os
import shutil
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _prepend_repo_root_if_present(path: Path) -> None:
    """Prepend a repo root to sys.path when it exists and is not already present."""

    if not path.is_dir():
        return
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def _bootstrap_shared_import_roots() -> None:
    """Expose shared editable repos through stable repo-root import paths.

    The local-first runtime often executes from a shared environment where an
    editable install of ``llm_client`` resolves to the repo root namespace
    instead of the inner package facade. Prepending the shared repo roots keeps
    the public imports (`from llm_client import ...`) truthful without relying
    on one-off operator shell mutations.
    """

    projects_root = Path(
        os.environ.get("PROJECTS_ROOT", str(Path.home() / "projects"))
    ).expanduser().resolve()
    for repo_name in ("llm_client", "agentic_scaffolding"):
        _prepend_repo_root_if_present(projects_root / repo_name)


_bootstrap_shared_import_roots()

# Ensure sibling modules (spawn_extract) are importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Ensure project-meta root is importable (for scripts.meta.task_graph, scripts.meta.analyzer)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

TASKS_DIR = Path(os.environ.get("OPENCLAW_TASKS_DIR", Path.home() / ".openclaw" / "tasks"))
COST_LOG = Path(os.environ.get("OPENCLAW_COST_LOG", Path.home() / ".openclaw" / "cost_log.jsonl"))
DAILY_BUDGET_USD = float(os.environ.get("OPENCLAW_DAILY_BUDGET", "20.0"))
SUPERVISOR_LOG = Path(os.environ.get(
    "OPENCLAW_SUPERVISOR_LOG",
    TASKS_DIR / "supervisor.jsonl",
))
SUPERVISOR_LOCK = Path(os.environ.get(
    "OPENCLAW_SUPERVISOR_LOCK",
    Path.home() / ".openclaw" / "run_task.supervisor.lock",
))

EXPERIMENT_LOG = Path(os.environ.get(
    "OPENCLAW_EXPERIMENT_LOG",
    Path.home() / "projects" / "data" / "task_graph" / "experiments.jsonl",
))
PROPOSALS_LOG = Path(os.environ.get(
    "OPENCLAW_PROPOSALS_LOG",
    Path.home() / "projects" / "data" / "task_graph" / "proposals.jsonl",
))
FLOORS_PATH = Path(os.environ.get(
    "OPENCLAW_MODEL_FLOORS",
    Path.home() / "projects" / "data" / "task_graph" / "model_floors.json",
))
MCP_REGISTRY = Path(os.environ.get(
    "OPENCLAW_MCP_REGISTRY",
    Path.home() / ".openclaw" / "mcp_registry.toml",
))
REPORTS_DIR = Path(os.environ.get(
    "OPENCLAW_REPORTS_DIR",
    TASKS_DIR / "reports",
))

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_task")


# ---------------------------------------------------------------------------
# MCP server registry
# ---------------------------------------------------------------------------


def _load_mcp_registry() -> dict[str, dict[str, Any]]:
    """Load MCP server configs from TOML registry.

    Returns dict mapping server_name -> {command, args, env?, cwd?}
    with ~ expanded in all paths.
    """
    if not MCP_REGISTRY.exists():
        log.warning("MCP registry not found: %s", MCP_REGISTRY)
        return {}

    with open(MCP_REGISTRY, "rb") as f:
        data = tomllib.load(f)

    home = str(Path.home())
    configs: dict[str, dict[str, Any]] = {}

    for name, server in data.get("servers", {}).items():
        entry: dict[str, Any] = {
            "command": server["command"].replace("~", home),
        }
        if "args" in server:
            entry["args"] = [a.replace("~", home) for a in server["args"]]
        if "cwd" in server:
            entry["cwd"] = server["cwd"].replace("~", home)
        if "env" in server:
            entry["env"] = {
                k: v.replace("~", home) if isinstance(v, str) else v
                for k, v in server["env"].items()
            }
        configs[name] = entry

    log.info("Loaded %d MCP server configs from %s", len(configs), MCP_REGISTRY)
    return configs


# ---------------------------------------------------------------------------
# Flat task data model (existing .md format)
# ---------------------------------------------------------------------------


@dataclass
class TaskConstraints:
    """Budget and scope constraints for a single task."""

    max_turns: int = 30
    max_budget_usd: float = 2.0
    mcp_servers: list[str] = field(default_factory=list)
    file_scope: list[str] = field(default_factory=list)


@dataclass
class TaskSpec:
    """Parsed flat task specification from a .md file with YAML frontmatter."""

    id: str
    priority: str
    agent: str
    project: str
    created: str
    status: str
    constraints: TaskConstraints
    title: str
    objective: str
    acceptance_criteria: str
    context: str
    source_path: Path
    model: str | None = None  # Explicit model override; baseline requires it for flat tasks
    reasoning_effort: str | None = None  # "low", "medium", "high", "xhigh"
    planner_lineage: dict | None = None  # Planner metadata (task_kind, delivery_mode, etc.)

    @classmethod
    def from_file(cls, path: Path) -> "TaskSpec":
        """Parse a flat task .md file into a TaskSpec."""
        text = path.read_text()
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Task file missing YAML frontmatter: {path}")

        meta = yaml.safe_load(parts[1])
        if not meta:
            raise ValueError(f"Empty YAML frontmatter: {path}")

        body = parts[2]
        constraints_raw = meta.get("constraints", {}) or {}

        # Handle agent: null from YAML → "direct"
        raw_agent = meta.get("agent")
        agent = raw_agent if raw_agent else "direct"

        return cls(
            id=str(meta["id"]),
            priority=meta.get("priority", "medium"),
            agent=agent,
            project=str(meta["project"]).replace("~", str(Path.home())),
            created=str(meta.get("created", "")),
            status=meta.get("status", "pending"),
            constraints=TaskConstraints(
                max_turns=constraints_raw.get("max_turns", 30),
                max_budget_usd=constraints_raw.get("max_budget_usd", 2.0),
                mcp_servers=constraints_raw.get("mcp_servers", []) or [],
                file_scope=constraints_raw.get("file_scope", []) or [],
            ),
            title=_extract_section_title(body),
            objective=_extract_section(body, "Objective"),
            acceptance_criteria=_extract_section(body, "Acceptance Criteria"),
            context=_extract_section(body, "Context"),
            source_path=path,
            model=meta.get("model"),
            reasoning_effort=meta.get("reasoning_effort"),
            planner_lineage=meta.get("planner_lineage") or {},
        )

    def sort_key(self) -> tuple[int, str]:
        """Return (priority_rank, created) for sorting tasks highest-priority first."""
        return (PRIORITY_ORDER.get(self.priority, 99), self.created)


def _extract_section_title(body: str) -> str:
    for line in body.strip().splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "(untitled)"


def _extract_section(body: str, heading: str) -> str:
    lines = body.splitlines()
    capturing = False
    captured: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and heading.lower() in stripped.lower():
            capturing = True
            continue
        if capturing and stripped.startswith("## "):
            break
        if capturing:
            captured.append(line)
    return "\n".join(captured).strip()


# ---------------------------------------------------------------------------
# Flat task execution (existing .md format)
# ---------------------------------------------------------------------------


def _load_spawning_prompt() -> str:
    """Load the agent spawning/escalation instructions from the YAML template.

    Returns the prompt content string, or empty string if the template
    is missing or unparseable (logged as warning, never raises).
    """
    template_path = Path(__file__).resolve().parent / "prompts" / "agent_spawning.yaml"
    if not template_path.exists():
        log.warning("Spawning prompt template not found: %s", template_path)
        return ""
    try:
        data = yaml.safe_load(template_path.read_text())
        return str(data.get("content", ""))
    except Exception as exc:
        log.warning("Failed to load spawning prompt: %s", exc)
        return ""


def _build_prompt(task: TaskSpec) -> str:
    parts = [f"# Task: {task.title}", ""]

    if task.objective:
        parts.append(task.objective)
        parts.append("")

    if task.acceptance_criteria:
        parts.append("## Acceptance Criteria")
        parts.append(task.acceptance_criteria)
        parts.append("")

    if task.constraints.file_scope:
        scope = ", ".join(task.constraints.file_scope)
        parts.append(f"## File Scope\nOnly modify files in: {scope}")
        parts.append("")

    if task.context:
        parts.append("## Context")
        parts.append(task.context)
        parts.append("")

    parts.append("## Instructions")
    project_root = Path(task.project).expanduser()
    governance_hints: list[str] = []
    if (project_root / "CLAUDE.md").exists():
        governance_hints.append("`CLAUDE.md` (canonical governance)")
    if (project_root / "AGENTS.md").exists():
        governance_hints.append("`AGENTS.md` (generated Codex projection)")
    if governance_hints:
        parts.append(
            "- Read repo-local governance before making changes: "
            + ", ".join(governance_hints)
        )
    else:
        parts.append("- Read relevant repo-local governance docs before making changes")
    if (project_root / "scripts" / "relationships.yaml").exists():
        parts.append(
            "- If present, treat `scripts/relationships.yaml` as the machine-readable governance graph for ADR, doc-coupling, and required-reading checks"
        )
    parts.append("- Commit your work with a descriptive message when verified. Use [Plan #N] prefix if a plan number is referenced in the objective, otherwise use [Unplanned].")
    parts.append("- Run tests before committing. Do not commit broken code.")
    parts.append("- If you get stuck, explain what blocked you in your final response")
    parts.append("- Do NOT push to remote unless the task explicitly asks for it")

    # Append spawning/escalation instructions from prompt template
    spawning_prompt = _load_spawning_prompt()
    if spawning_prompt:
        parts.append("")
        parts.append(spawning_prompt)

    return "\n".join(parts)


async def _execute_flat_task(
    task: TaskSpec,
    *,
    parent_trace_id: str | None = None,
    attempt_context: str = "",
) -> dict:
    """Execute a flat task via llm_client and return result metadata."""
    from llm_client import acall_llm

    prompt = _build_prompt(task)
    if attempt_context:
        prompt += "\n\n" + attempt_context
    messages = [{"role": "user", "content": prompt}]

    # Hierarchical trace_id: parent/child when dispatched, standalone otherwise
    timestamp = int(time.time())
    if parent_trace_id:
        trace_id = f"{parent_trace_id}/{task.id}"
    else:
        trace_id = f"openclaw.flat.{task.id}.{timestamp}"

    kwargs: dict = {}

    if task.agent in ("claude-code", "claude"):
        kwargs["cwd"] = task.project
        kwargs["max_turns"] = task.constraints.max_turns
        kwargs["permission_mode"] = "bypassPermissions"
        if task.constraints.max_budget_usd:
            kwargs["max_budget_usd"] = task.constraints.max_budget_usd
    elif task.agent in ("codex",):
        kwargs["working_directory"] = task.project
        kwargs["approval_policy"] = "never"
    elif task.agent in ("direct",):
        # Direct litellm call (no agent SDK) — used for gpt-5.2-pro reviews
        kwargs["execution_mode"] = "text"
    else:
        raise ValueError(f"Unknown agent: {task.agent!r}. Use 'claude-code', 'codex', or 'direct'.")

    if not isinstance(task.model, str) or not task.model.strip():
        raise ValueError(
            "Flat task requires explicit `model:` in frontmatter before execution. "
            "Example: model: codex OR model: claude-code OR model: gpt-5.2-pro"
        )
    model = task.model.strip()

    # Agent tasks need much more than the default 60s timeout.
    # Direct litellm tasks (e.g. gpt-5.2-pro xhigh) may think for 5-10 min.
    agent_timeout = max(300, task.constraints.max_turns * 30)
    if task.agent == "direct":
        agent_timeout = max(agent_timeout, 900)

    # Pass reasoning_effort if specified (e.g. "xhigh" for gpt-5.2-pro)
    if task.reasoning_effort:
        kwargs["reasoning_effort"] = task.reasoning_effort

    log.info("Calling %s in %s (max_turns=%d, budget=$%.2f, timeout=%ds, trace=%s)",
             model, task.project, task.constraints.max_turns,
             task.constraints.max_budget_usd, agent_timeout, trace_id)

    start = time.monotonic()
    result = await acall_llm(
        model, messages, timeout=agent_timeout,
        task=f"openclaw.{task.agent}",
        trace_id=trace_id,
        max_budget=0,
        **kwargs,
    )
    duration = time.monotonic() - start
    raw_response = getattr(result, "raw_response", None)
    metadata: dict[str, Any] = {}
    if hasattr(raw_response, "metadata") and isinstance(raw_response.metadata, dict):
        metadata = dict(raw_response.metadata)
    elif isinstance(raw_response, dict):
        raw_meta = raw_response.get("metadata")
        if isinstance(raw_meta, dict):
            metadata = dict(raw_meta)

    return {
        "content": result.content,
        "cost_usd": result.cost,
        "model": result.model,
        "usage": result.usage,
        "finish_reason": result.finish_reason,
        "duration_s": round(duration, 1),
        "tool_calls_count": len(result.tool_calls),
        "trace_id": trace_id,
        "primary_failure_class": metadata.get("primary_failure_class"),
        "failure_event_codes": metadata.get("failure_event_codes"),
        "failure_event_code_counts": metadata.get("failure_event_code_counts"),
        "llm_metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Flat task validation
# ---------------------------------------------------------------------------


def _run_validation(task: TaskSpec, pre_status: str = "") -> tuple[bool, str]:
    """Run post-execution validation. Returns (passed, details)."""
    import subprocess

    project = Path(task.project).expanduser()
    checks_passed = []
    checks_failed = []
    venv_python = project / ".venv" / "bin" / "python3"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    # Check git status — report NEW uncommitted changes as info, not failure.
    # Agents are expected to create/modify files; uncommitted changes are normal output.
    git_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project, capture_output=True, text=True, timeout=10,
    )
    post_status = git_result.stdout.strip()
    new_changes = set(post_status.splitlines()) - set(pre_status.splitlines())
    if new_changes:
        checks_passed.append(f"Agent produced changes:\n" + "\n".join(new_changes))
    else:
        checks_passed.append("No new uncommitted changes")

    # Check if test suite exists and passes.
    # For docs_only/analysis_only tasks, skip tests: the agent only wrote docs,
    # so pre-existing test failures are not attributable to this task.
    task_kind = (task.planner_lineage or {}).get("task_kind", "")
    _skip_tests = task_kind in ("docs_only", "analysis_only")
    has_pytest = (project / "pytest.ini").exists() or (project / "pyproject.toml").exists()
    has_tests = (project / "tests").is_dir()

    if _skip_tests:
        checks_passed.append(f"Tests skipped (task_kind={task_kind!r})")
    elif has_pytest and has_tests:
        if venv_python.exists():
            test_result = subprocess.run(
                [str(venv_python), "-m", "pytest", "--tb=short", "-q"],
                cwd=project, capture_output=True, text=True, timeout=120,
            )
            if test_result.returncode == 0:
                checks_passed.append("Tests pass")
            else:
                checks_failed.append(f"Tests failed:\n{test_result.stdout[-500:]}")
        else:
            checks_passed.append("Tests skipped (no .venv)")
    else:
        checks_passed.append("No test suite")

    # Governance parity check for repos that define event taxonomy parity scripts.
    parity_script = project / "scripts" / "check_event_taxonomy_parity.py"
    taxonomy_file = project / "vision" / "EVENT_TAXONOMY_V1.md"
    runtime_mcp_agent = project.parent / "llm_client" / "llm_client" / "mcp_agent.py"
    if parity_script.exists() and taxonomy_file.exists():
        if runtime_mcp_agent.exists():
            parity_result = subprocess.run(
                [
                    python_bin,
                    str(parity_script),
                    "--taxonomy-file",
                    str(taxonomy_file),
                    "--mcp-agent-file",
                    str(runtime_mcp_agent),
                ],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if parity_result.returncode == 0:
                checks_passed.append("Event taxonomy parity")
            else:
                parity_tail = "\n".join(
                    part.strip()
                    for part in (parity_result.stdout, parity_result.stderr)
                    if part and part.strip()
                )[-800:]
                checks_failed.append(f"event taxonomy parity failed:\n{parity_tail}")
        else:
            checks_passed.append("Event taxonomy parity skipped (runtime source missing)")
    else:
        checks_passed.append("Event taxonomy parity skipped (not a governance repo)")

    # Scaffold validators (syntax, stubs, test existence) when available.
    # For docs_only/analysis_only tasks, skip stub detection: the agent only
    # writes markdown; pre-existing Python stubs are not the agent's fault.
    task_kind = (task.planner_lineage or {}).get("task_kind", "")
    _skip_stubs = task_kind in ("docs_only", "analysis_only")
    try:
        from agentic_scaffolding.validators.fail_fast import fail_fast
        ff_result = fail_fast(workspace=project, check_stubs=not _skip_stubs)
        if ff_result.passed:
            label = "scaffold.fail_fast pass" + (" (stubs skipped)" if _skip_stubs else "")
            checks_passed.append(label)
        else:
            checks_failed.append(f"scaffold.fail_fast: {'; '.join(ff_result.errors)}")
    except ImportError:
        pass  # agentic_scaffolding not installed
    except Exception as exc:
        log.warning("scaffold.fail_fast error (skipping): %s", exc)

    passed = len(checks_failed) == 0
    details_parts = []
    if checks_passed:
        details_parts.append("Passed: " + "; ".join(checks_passed))
    if checks_failed:
        details_parts.append("Failed: " + "; ".join(checks_failed))

    return passed, "\n".join(details_parts)


# ---------------------------------------------------------------------------
# Agent state checks
# ---------------------------------------------------------------------------


def _agent_committed(task: TaskSpec) -> bool:
    """Check if the agent created a new git commit in the last 5 minutes."""
    import subprocess
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--since=5 minutes ago", "-1"],
            cwd=task.project, capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _recoverable_postsuccess_agent_error_reason(
    error_type: str,
    error_text: str,
) -> str | None:
    """Return a recovery reason for bounded post-success agent failures.

    This is intentionally narrow. We only recover from the measured Claude
    agent false-negative family where the subprocess exits generically after the
    agent has already completed bounded work.
    """

    normalized = error_text.strip()
    if not normalized:
        return "empty agent error after bounded work"

    if (
        error_type == "LLMError"
        and "Command failed with exit code 1" in normalized
        and "Check stderr output for details" in normalized
    ):
        return "generic claude agent subprocess exit after bounded work"

    return None


def _meaningful_new_status_lines(
    pre_status: str,
    post_status: str,
) -> list[str]:
    """Return new git-status lines that represent meaningful work product."""

    ignored = {"?? .claude/hook_log.jsonl"}
    pre_lines = {line for line in pre_status.splitlines() if line.strip()}
    post_lines = {line for line in post_status.splitlines() if line.strip()}
    return sorted((post_lines - pre_lines) - ignored)


def _agent_produced_meaningful_changes(
    task: TaskSpec,
    pre_status: str,
) -> list[str]:
    """Return meaningful new worktree status lines for a task."""

    import subprocess

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=task.project,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    return _meaningful_new_status_lines(pre_status, result.stdout.strip())


def _postsuccess_recovery_context(
    task: TaskSpec,
    error_type: str,
    error_text: str,
    pre_status: str,
) -> dict[str, Any] | None:
    """Return bounded recovery context when evidence supports recovery."""

    reason = _recoverable_postsuccess_agent_error_reason(error_type, error_text)
    if reason is None:
        return None

    committed = _agent_committed(task)
    changed_lines = _agent_produced_meaningful_changes(task, pre_status)
    if not committed and not changed_lines:
        return None

    return {
        "reason": reason,
        "committed": committed,
        "changed_lines": changed_lines,
    }


# ---------------------------------------------------------------------------
# File management
# ---------------------------------------------------------------------------


def _move_task(task_path: Path, destination: str) -> Path:
    dest_dir = TASKS_DIR / destination
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / task_path.name
    shutil.move(str(task_path), str(dest))
    log.info("Moved %s -> %s/", task_path.name, destination)
    return dest


def _append_status_log(task_path: Path, entry: str) -> None:
    text = task_path.read_text()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_entry = f"\n- [{timestamp}] {entry}"

    if "## Status Log" in text:
        text = text.replace("## Status Log", f"## Status Log{log_entry}", 1)
    else:
        text += f"\n\n## Status Log{log_entry}\n"

    task_path.write_text(text)


def _append_result(task_path: Path, result_text: str) -> None:
    text = task_path.read_text()
    if "## Result" in text:
        text = text.replace("## Result", f"## Result\n\n{result_text}", 1)
    else:
        text += f"\n\n## Result\n\n{result_text}\n"
    task_path.write_text(text)


def _log_cost(task_id: str, agent: str, model: str,
              cost_usd: float, duration_s: float, status: str) -> None:
    entry = {
        "task_id": task_id,
        "agent": agent,
        "model": model,
        "cost_usd": cost_usd,
        "duration_s": duration_s,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(COST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    log.info("Cost: $%.4f in %.1fs", cost_usd, duration_s)


def _load_graph_yaml_raw(path: Path) -> dict[str, Any]:
    """Load a YAML task graph file as a raw dict, returning {} on any failure.

    Used to extract planner_metadata without going through the full typed loader.
    Failures are silent because this is a best-effort gate check.
    """
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _check_review_gate(
    planner_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Read the final review JSON for a planner-generated review_cycle graph.

    Returns a dict with:
    - passed: bool — True only when the review JSON exists, is valid, and status=='pass'
    - status: str — 'pass', 'needs_changes', 'missing', 'invalid', or 'error'
    - reason: str — human-readable explanation
    - review_json_path: str — the expected path
    - raw: dict | None — parsed review JSON when available
    """
    review_json_path = planner_metadata.get("final_review_json", "")
    result: dict[str, Any] = {
        "passed": False,
        "status": "missing",
        "reason": "",
        "review_json_path": review_json_path,
        "raw": None,
    }

    if not review_json_path:
        result["reason"] = "planner_metadata.final_review_json not set"
        return result

    path = Path(review_json_path)
    if not path.exists():
        result["reason"] = f"Review JSON not found: {review_json_path}"
        return result

    try:
        with open(path) as f:
            review = json.load(f)
        result["raw"] = review
    except json.JSONDecodeError as e:
        result["status"] = "invalid"
        result["reason"] = f"Review JSON is not valid JSON: {e}"
        return result
    except Exception as e:
        result["status"] = "error"
        result["reason"] = f"Failed to read review JSON: {e}"
        return result

    review_status = review.get("status", "")
    result["status"] = review_status or "invalid"
    if review_status == "pass":
        result["passed"] = True
        result["reason"] = "review gate passed"
    elif review_status == "needs_changes":
        result["reason"] = f"review requires changes: {review.get('next_objective', '')}"
    else:
        result["reason"] = f"unexpected review status: '{review_status}'"

    return result


def _check_commit_evidence(
    planner_metadata: dict[str, Any],
    task_started_at: str,
) -> dict[str, Any]:
    """Check whether a new commit exists in the target repo since the task started.

    Returns a dict with:
    - passed: bool — True when at least one new commit exists since task_started_at
    - commit_detected: bool
    - commit_sha: str | None
    - commit_timestamp: str | None
    - reason: str
    """
    import subprocess

    result: dict[str, Any] = {
        "passed": False,
        "commit_detected": False,
        "commit_sha": None,
        "commit_timestamp": None,
        "reason": "",
    }

    target_repo = planner_metadata.get("target_repo", "")
    if not target_repo:
        result["reason"] = "planner_metadata.target_repo not set"
        return result

    repo_path = Path(target_repo)
    if not repo_path.is_dir():
        result["reason"] = f"Target repo not found: {target_repo}"
        return result

    try:
        # Parse ISO start time to git-friendly format
        started_dt = datetime.fromisoformat(task_started_at)
        since_arg = started_dt.strftime("%Y-%m-%dT%H:%M:%S")
        cmd = ["git", "log", "--oneline", f"--since={since_arg}", "-1",
               "--format=%H %aI"]
        proc = subprocess.run(
            cmd, cwd=repo_path, capture_output=True, text=True, timeout=10,
        )
        output = proc.stdout.strip()
        if output:
            parts = output.split(" ", 1)
            result["commit_detected"] = True
            result["commit_sha"] = parts[0]
            result["commit_timestamp"] = parts[1] if len(parts) > 1 else None
            result["passed"] = True
            result["reason"] = f"commit detected: {parts[0][:8]}"
        else:
            result["reason"] = f"no new commit in {target_repo} since {since_arg}"
    except Exception as e:
        result["reason"] = f"commit check failed: {e}"

    return result


def _safe_report_slug(value: str) -> str:
    slug = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)
    slug = slug.strip("_")
    return slug[:80] or "task"


def _write_task_report(task_ref: str, payload: dict[str, Any]) -> Path:
    """Write one structured task report JSON artifact."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = REPORTS_DIR / f"{_safe_report_slug(task_ref)}_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return out_path


def _record_decision_event(
    report_payload: dict[str, Any],
    *,
    decision_stage: str,
    selected_action: str,
    decision_reason: str,
    alternatives_considered_count: int = 0,
    confidence: float | None = None,
    evidence_refs: list[str] | None = None,
) -> None:
    """Append one decision provenance event to report payload."""
    dp = report_payload.setdefault("decision_provenance", {})
    if not isinstance(dp, dict):
        dp = {}
        report_payload["decision_provenance"] = dp
    dp.setdefault("schema_version", "v1")
    events = dp.setdefault("events", [])
    if not isinstance(events, list):
        events = []
        dp["events"] = events

    event: dict[str, Any] = {
        "decision_at": datetime.now(timezone.utc).isoformat(),
        "decision_stage": decision_stage,
        "selected_action": selected_action,
        "decision_reason": decision_reason,
        "alternatives_considered_count": max(0, int(alternatives_considered_count)),
        "decision_source": "openclaw.run_task",
    }
    if confidence is not None:
        event["confidence"] = max(0.0, min(1.0, float(confidence)))
    event["evidence_refs"] = list(evidence_refs or [])
    events.append(event)


def _run_flat_preflight(task: TaskSpec) -> dict[str, Any]:
    """Deterministic preflight checks for flat tasks."""
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    project = Path(task.project).expanduser()

    if project.exists() and project.is_dir():
        checks.append({"check": "project_path_exists", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_PROJECT_PATH_MISSING",
            "message": f"Project path does not exist: {project}",
        })

    if task.agent in ("claude-code", "claude", "codex", "direct"):
        checks.append({"check": "agent_supported", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_UNSUPPORTED_AGENT",
            "message": f"Unsupported agent: {task.agent}",
        })

    if isinstance(task.model, str) and task.model.strip():
        checks.append({"check": "model_declared", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_MISSING_MODEL",
            "message": "Flat task requires explicit `model:` in frontmatter.",
        })

    if isinstance(task.constraints.max_turns, int) and task.constraints.max_turns > 0:
        checks.append({"check": "max_turns_valid", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_INVALID_MAX_TURNS",
            "message": f"max_turns must be > 0 (got {task.constraints.max_turns!r})",
        })

    if isinstance(task.constraints.max_budget_usd, (int, float)) and task.constraints.max_budget_usd >= 0:
        checks.append({"check": "max_budget_valid", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_INVALID_MAX_BUDGET",
            "message": f"max_budget_usd must be >= 0 (got {task.constraints.max_budget_usd!r})",
        })

    if project.exists():
        git_dir = project / ".git"
        if git_dir.exists():
            checks.append({"check": "project_is_git_repo", "passed": True})
        else:
            failures.append({
                "error_code": "OPENCLAW_PREFLIGHT_PROJECT_NOT_GIT_REPO",
                "message": f"Project path is not a git repo: {project}",
            })

    passed = len(failures) == 0
    return {
        "passed": passed,
        "checks": checks,
        "failures": failures,
        "failure_event_codes": [f["error_code"] for f in failures],
        "primary_failure_class": "none" if passed else "composability",
    }


def _run_graph_preflight(graph: Any, mcp_configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Deterministic preflight checks for YAML task graphs."""
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    if graph.tasks:
        checks.append({"check": "graph_has_tasks", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_EMPTY_GRAPH",
            "message": "Task graph contains no tasks.",
        })

    if graph.waves:
        checks.append({"check": "graph_has_waves", "passed": True})
    else:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_EMPTY_WAVES",
            "message": "Task graph contains no execution waves.",
        })

    missing_servers: set[str] = set()
    for task in graph.tasks.values():
        for server in task.mcp_servers or []:
            if server not in mcp_configs:
                missing_servers.add(server)
    if missing_servers:
        failures.append({
            "error_code": "OPENCLAW_PREFLIGHT_MISSING_MCP_SERVER_CONFIG",
            "message": f"Missing MCP server config(s): {sorted(missing_servers)}",
        })
    else:
        checks.append({"check": "graph_mcp_servers_configured", "passed": True})

    passed = len(failures) == 0
    return {
        "passed": passed,
        "checks": checks,
        "failures": failures,
        "failure_event_codes": [f["error_code"] for f in failures],
        "primary_failure_class": "none" if passed else "composability",
    }


def _check_daily_budget() -> tuple[bool, float]:
    """Check if daily budget allows another task. Returns (ok, spent_today)."""
    if not COST_LOG.exists():
        return True, 0.0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spent = 0.0
    for line in COST_LOG.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("timestamp", "").startswith(today):
            spent += entry.get("cost_usd", 0)

    return spent < DAILY_BUDGET_USD, spent


def _frontmatter_parts(path: Path) -> tuple[dict[str, Any], str]:
    """Parse flat-task frontmatter and return structured metadata plus body."""

    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Task file missing YAML frontmatter: {path}")
    metadata = yaml.safe_load(parts[1])
    if not isinstance(metadata, dict):
        raise ValueError(f"Malformed YAML frontmatter: {path}")
    return metadata, parts[2]


def _flat_task_model_gap(path: Path) -> dict[str, Any] | None:
    """Return frontmatter when a flat task is missing `model:`, else None."""

    metadata, _ = _frontmatter_parts(path)
    if not isinstance(metadata, dict):
        return None
    raw_model = metadata.get("model")
    if isinstance(raw_model, str) and raw_model.strip():
        return None
    return metadata


def _write_frontmatter(path: Path, metadata: dict[str, Any], body: str) -> None:
    """Rewrite a flat-task file after a targeted frontmatter update."""

    rendered_meta = yaml.safe_dump(metadata, sort_keys=False).rstrip()
    document = f"---\n{rendered_meta}\n---"
    if body:
        document += body if body.startswith("\n") else f"\n{body}"
    else:
        document += "\n"
    path.write_text(document, encoding="utf-8")


def _apply_flat_task_model_patch(path: Path, model: str) -> None:
    """Write an explicit `model:` field into a flat task in-place."""

    metadata, body = _frontmatter_parts(path)
    raw_model = metadata.get("model")
    if isinstance(raw_model, str) and raw_model.strip():
        raise ValueError(f"Flat task already declares model: {path}")

    updated_metadata: dict[str, Any] = {}
    inserted = False
    for key, value in metadata.items():
        updated_metadata[key] = value
        if key == "agent":
            updated_metadata["model"] = model
            inserted = True
    if not inserted:
        updated_metadata["model"] = model

    _write_frontmatter(path, updated_metadata, body)


def _infer_repair_model(agent: str, default_model: str | None) -> str:
    """Map a legacy flat-task agent to an explicit model for repair."""

    normalized_agent = agent.strip()
    if normalized_agent == "codex":
        return "codex"
    if normalized_agent in {"claude", "claude-code"}:
        return "claude-code"

    if isinstance(default_model, str) and default_model.strip():
        return default_model.strip()

    raise ValueError(
        "Cannot infer repair model for flat task agent "
        f"`{normalized_agent or 'direct'}`. Re-run with --repair-default-model."
    )


def _plan_flat_task_model_repairs(
    flat_gaps: list[tuple[Path, dict[str, Any]]],
    *,
    default_model: str | None,
) -> list[tuple[Path, dict[str, Any], str]]:
    """Resolve concrete repair actions for flat tasks with missing models."""

    repair_plan: list[tuple[Path, dict[str, Any], str]] = []
    failures: list[str] = []

    for path, metadata in flat_gaps:
        raw_agent = metadata.get("agent")
        agent = str(raw_agent).strip() if isinstance(raw_agent, str) else "direct"
        try:
            repaired_model = _infer_repair_model(agent, default_model)
        except ValueError as exc:
            failures.append(f"{path}: {exc}")
            continue
        repair_plan.append((path, metadata, repaired_model))

    if failures:
        raise ValueError("\n".join(failures))

    return repair_plan


def _scan_flat_model_gaps(
    *,
    include_pending: bool = True,
    include_active: bool = True,
) -> list[tuple[Path, dict[str, Any]]]:
    """Scan queued flat tasks for missing explicit `model:` declarations."""

    directories: list[Path] = []
    if include_pending:
        directories.append(TASKS_DIR / "pending")
    if include_active:
        directories.append(TASKS_DIR / "active")

    gaps: list[tuple[Path, dict[str, Any]]] = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            try:
                metadata = _flat_task_model_gap(path)
            except Exception:
                continue
            if metadata is not None:
                gaps.append((path, metadata))
    return gaps


def _scan_graph_model_gaps(
    *,
    include_pending: bool = True,
    include_active: bool = True,
) -> list[tuple[Path, list[str]]]:
    """Scan queued task graphs for nodes missing explicit `model:` declarations."""

    directories: list[Path] = []
    if include_pending:
        directories.append(TASKS_DIR / "pending")
    if include_active:
        directories.append(TASKS_DIR / "active")

    gaps: list[tuple[Path, list[str]]] = []
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
            try:
                payload = yaml.safe_load(path.read_text()) or {}
            except Exception:
                continue
            tasks = payload.get("tasks") if isinstance(payload, dict) else None
            if not isinstance(tasks, dict):
                continue

            missing: list[str] = []
            for task_id, task_cfg in tasks.items():
                if not isinstance(task_cfg, dict):
                    continue
                difficulty = int(task_cfg.get("difficulty", 0) or 0)
                if difficulty == 0:
                    continue
                raw_model = task_cfg.get("model")
                if not isinstance(raw_model, str) or not raw_model.strip():
                    missing.append(str(task_id))
            if missing:
                gaps.append((path, missing))
    return gaps


def _collect_model_gaps() -> tuple[list[tuple[Path, dict[str, Any]]], list[tuple[Path, list[str]]]]:
    """Collect queued flat-task and graph-task model declaration gaps."""

    return _scan_flat_model_gaps(), _scan_graph_model_gaps()


def _print_model_gap_report(
    flat_gaps: list[tuple[Path, dict[str, Any]]],
    graph_gaps: list[tuple[Path, list[str]]],
) -> bool:
    """Print a concise model-gap report and return True when the queue is clean."""

    if not flat_gaps and not graph_gaps:
        print("Model gaps: none")
        return True

    if flat_gaps:
        print("Flat tasks missing model:")
        for path, metadata in flat_gaps:
            print(
                f"  {path} (id={metadata.get('id', path.stem)} "
                f"agent={metadata.get('agent', '?')})"
            )

    if graph_gaps:
        print("Graph tasks missing model:")
        for path, missing in graph_gaps:
            print(f"  {path}: {', '.join(missing)}")

    return False


def _append_supervisor_log(event: str, **fields: Any) -> None:
    """Write a structured supervisor event line."""
    payload = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    SUPERVISOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SUPERVISOR_LOG, "a") as f:
        f.write(json.dumps(payload) + "\n")


def _recover_stale_active_tasks(stale_after_s: int) -> int:
    """Move stale tasks from active/ to failed/ to unblock the queue."""
    if stale_after_s <= 0:
        return 0

    active_dir = TASKS_DIR / "active"
    if not active_dir.exists():
        return 0

    now = time.time()
    recovered = 0
    for task_path in sorted(active_dir.iterdir()):
        if not task_path.is_file():
            continue
        if task_path.suffix not in (".md", ".yaml", ".yml"):
            continue
        age_s = int(now - task_path.stat().st_mtime)
        if age_s < stale_after_s:
            continue

        if task_path.suffix == ".md":
            _append_status_log(
                task_path,
                f"Supervisor recovered stale task after {age_s}s in active/",
            )
        _move_task(task_path, "failed")
        _append_supervisor_log(
            "stale_task_recovered",
            task_file=task_path.name,
            age_s=age_s,
            stale_after_s=stale_after_s,
        )
        recovered += 1

    return recovered


def _next_pending_task_path() -> Path | None:
    """Pick the next pending task using existing priority rules."""
    flat_tasks, graph_files = _list_pending()
    if flat_tasks:
        return flat_tasks[0].source_path
    if graph_files:
        return graph_files[0]
    return None


class _SupervisorLock:
    """Single-instance lock using flock()."""

    def __init__(self, lock_path: Path):
        self._lock_path = lock_path
        self._fh = None

    def __enter__(self) -> "_SupervisorLock":
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self._lock_path, "a+")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f"Supervisor already running (lock: {self._lock_path})")
        self._fh.seek(0)
        self._fh.truncate(0)
        self._fh.write(f"{os.getpid()}\n")
        self._fh.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
        try:
            self._lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def _run_supervisor_loop(
    *,
    poll_interval_s: float,
    max_idle_cycles: int,
    max_runs: int,
    stale_after_s: int,
) -> int:
    """Continuously drain pending tasks until stop condition is met."""
    runs = 0
    idle_cycles = 0
    _append_supervisor_log(
        "supervisor_started",
        pid=os.getpid(),
        poll_interval_s=poll_interval_s,
        max_idle_cycles=max_idle_cycles,
        max_runs=max_runs,
        stale_after_s=stale_after_s,
    )

    while True:
        _recover_stale_active_tasks(stale_after_s)
        next_task = _next_pending_task_path()
        if next_task is None:
            idle_cycles += 1
            _append_supervisor_log("idle_cycle", idle_cycles=idle_cycles)
            if max_idle_cycles > 0 and idle_cycles >= max_idle_cycles:
                _append_supervisor_log("supervisor_stopped", reason="max_idle_cycles", runs=runs)
                return 0
            time.sleep(max(0.0, poll_interval_s))
            continue

        idle_cycles = 0
        log.info("Supervisor dispatch: %s", next_task.name)
        _append_supervisor_log("dispatch", task_file=next_task.name)
        try:
            ok = asyncio.run(run_task(next_task))
        except Exception as e:
            log.error("Supervisor dispatch failed: %s: %s", type(e).__name__, e)
            _append_supervisor_log(
                "dispatch_exception",
                task_file=next_task.name,
                error=f"{type(e).__name__}: {e}",
            )
            ok = False

        runs += 1
        _append_supervisor_log(
            "dispatch_finished",
            task_file=next_task.name,
            success=ok,
            runs=runs,
        )

        if max_runs > 0 and runs >= max_runs:
            _append_supervisor_log("supervisor_stopped", reason="max_runs", runs=runs)
            return 0 if ok else 1

# ---------------------------------------------------------------------------
# Task graph execution (.yaml format)
# ---------------------------------------------------------------------------


async def _run_graph_task(task_path: Path) -> bool:
    """Execute a YAML task graph via llm_client.task_graph."""
    from scripts.meta.analyzer import analyze_run
    from scripts.meta.task_graph import ExecutionReport, load_graph, run_graph

    graph_ref = task_path.stem
    report_payload: dict[str, Any] = {
        "report_version": "v1",
        "task_type": "graph",
        "task_file": task_path.name,
        "graph_id": graph_ref,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _record_decision_event(
        report_payload,
        decision_stage="dispatch",
        selected_action="load_graph_task",
        decision_reason="task file is graph YAML; dispatching to graph runner",
        confidence=1.0,
        evidence_refs=[task_path.name],
    )

    # Budget check
    budget_ok, spent_today = _check_daily_budget()
    if not budget_ok:
        log.warning("Daily budget exceeded ($%.2f of $%.2f). Skipping.",
                     spent_today, DAILY_BUDGET_USD)
        _record_decision_event(
            report_payload,
            decision_stage="preflight",
            selected_action="skip_graph_budget_exceeded",
            decision_reason=f"daily budget exceeded (spent={spent_today:.2f}, limit={DAILY_BUDGET_USD:.2f})",
            evidence_refs=["OPENCLAW_DAILY_BUDGET_EXCEEDED"],
        )
        report_payload["status"] = "skipped_budget"
        report_payload["primary_failure_class"] = "provider"
        report_payload["failure_event_codes"] = ["OPENCLAW_DAILY_BUDGET_EXCEEDED"]
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(graph_ref, report_payload)
        return False

    # Move to active
    active_path = _move_task(task_path, "active")

    try:
        graph = load_graph(active_path)
        graph_ref = graph.meta.id
        report_payload["graph_id"] = graph_ref
        log.info("=== Running task graph: %s (%d tasks, %d waves) ===",
                 graph.meta.id, len(graph.tasks), len(graph.waves))

        # Load MCP server configs
        mcp_configs = _load_mcp_registry()
        preflight = _run_graph_preflight(graph, mcp_configs)
        report_payload["preflight"] = preflight
        if not preflight["passed"]:
            _record_decision_event(
                report_payload,
                decision_stage="preflight",
                selected_action="abort_graph_preflight",
                decision_reason=f"deterministic preflight failed with {len(preflight.get('failures', []))} failure(s)",
                evidence_refs=preflight.get("failure_event_codes") or [],
            )
            destination = "failed"
            _move_task(active_path, destination)
            report_payload["status"] = "failed_preflight"
            report_payload["destination"] = destination
            report_payload["primary_failure_class"] = preflight.get("primary_failure_class")
            report_payload["failure_event_codes"] = preflight.get("failure_event_codes")
            report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write_task_report(graph_ref, report_payload)
            log.warning("Graph preflight failed: %s", preflight.get("failures"))
            return False

        # Execute graph
        _record_decision_event(
            report_payload,
            decision_stage="execution",
            selected_action="execute_graph",
            decision_reason="preflight passed; executing graph waves",
        )
        report = await run_graph(
            graph,
            mcp_server_configs=mcp_configs,
            experiment_log=str(EXPERIMENT_LOG),
        )

        # Log per-task costs to OpenClaw cost_log
        for tr in report.task_results:
            _log_cost(
                task_id=f"{graph.meta.id}/{tr.task_id}",
                agent=tr.model_selected or "scripted",
                model=tr.model_selected or "",
                cost_usd=tr.cost_usd,
                duration_s=tr.duration_s,
                status=tr.status.value,
            )

        # Run self-improvement analyzer
        analysis = analyze_run(
            report,
            experiment_log=str(EXPERIMENT_LOG),
            proposals_log=str(PROPOSALS_LOG),
            floors_path=str(FLOORS_PATH),
        )
        if analysis.proposals:
            log.info("%d improvement proposals generated:", len(analysis.proposals))
            for p in analysis.proposals:
                log.info("  [%s] %s: %s for %s", p.risk, p.category, p.action, p.task_id)

        # Load planner metadata if present (Plan #2 semantic gating)
        graph_dict = _load_graph_yaml_raw(active_path)
        planner_metadata: dict[str, Any] = graph_dict.get("planner_metadata", {})
        is_planner_review_cycle = (
            planner_metadata.get("delivery_mode") == "review_cycle"
        )

        # Baseline routing from graph execution status
        if report.status != "completed":
            destination = "failed"
            review_gate: dict[str, Any] = {}
            commit_evidence: dict[str, Any] = {}
            semantic_gate_reason = "graph execution did not complete"
        elif is_planner_review_cycle:
            # Phase 2: Semantic review gate — graph completion alone is not enough
            review_gate = _check_review_gate(planner_metadata)
            if not review_gate["passed"]:
                destination = "failed"
                semantic_gate_reason = f"review gate failed: {review_gate['reason']}"
                commit_evidence = {}
                log.warning("Review gate failed for %s: %s", graph.meta.id, review_gate["reason"])
            else:
                # Phase 3: Commit evidence check
                commit_evidence = _check_commit_evidence(
                    planner_metadata,
                    task_started_at=report_payload["started_at"],
                )
                if not commit_evidence["passed"]:
                    destination = "failed"
                    semantic_gate_reason = (
                        f"review passed but no commit: {commit_evidence['reason']}"
                    )
                    log.warning(
                        "Commit gate failed for %s: %s", graph.meta.id, commit_evidence["reason"]
                    )
                else:
                    destination = "completed"
                    semantic_gate_reason = "review gate passed; commit detected"
        else:
            # Non-planner graph or flat delivery — existing behavior
            destination = "completed"
            review_gate = {}
            commit_evidence = {}
            semantic_gate_reason = "graph completed (no planner review gate)"

        _move_task(active_path, destination)
        report_payload["status"] = destination  # reflects semantic result, not just exec status
        report_payload["destination"] = destination
        report_payload["planner_lineage"] = planner_metadata if planner_metadata else {}
        report_payload["review_gate"] = review_gate
        report_payload["commit_evidence"] = commit_evidence

        _record_decision_event(
            report_payload,
            decision_stage="routing",
            selected_action=f"route_to_{destination}",
            decision_reason=semantic_gate_reason,
            evidence_refs=(
                []
                if destination == "completed"
                else ["OPENCLAW_GRAPH_SEMANTIC_GATE_FAILED"]
            ),
        )
        report_payload["run"] = {
            "total_cost_usd": report.total_cost_usd,
            "total_duration_s": report.total_duration_s,
            "waves_completed": report.waves_completed,
            "waves_total": report.waves_total,
            "task_results_count": len(report.task_results),
        }
        report_payload["primary_failure_class"] = "none" if destination == "completed" else "reasoning"
        report_payload["failure_event_codes"] = (
            [] if destination == "completed" else ["OPENCLAW_GRAPH_SEMANTIC_GATE_FAILED"]
        )
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(graph_ref, report_payload)

        log.info(
            "=== Graph %s: %s (cost=$%.4f, duration=%.1fs, %d/%d waves) — %s ===",
            destination.upper(), graph.meta.id,
            report.total_cost_usd, report.total_duration_s,
            report.waves_completed, report.waves_total,
            semantic_gate_reason,
        )

        return destination == "completed"

    except Exception as e:
        import traceback
        log.error("Graph execution failed: %s: %s\n%s",
                  type(e).__name__, e, traceback.format_exc())
        _move_task(active_path, "failed")
        report_payload["status"] = "failed_exception"
        report_payload["destination"] = "failed"
        _record_decision_event(
            report_payload,
            decision_stage="error_handling",
            selected_action="route_to_failed_exception",
            decision_reason=f"graph execution raised {type(e).__name__}",
            evidence_refs=["OPENCLAW_GRAPH_RUNTIME_EXCEPTION"],
        )
        report_payload["primary_failure_class"] = "provider"
        report_payload["failure_event_codes"] = ["OPENCLAW_GRAPH_RUNTIME_EXCEPTION"]
        report_payload["exception"] = f"{type(e).__name__}: {e}"
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(graph_ref, report_payload)
        return False


def _dry_run_graph(task_path: Path) -> None:
    """Show what a task graph would do without executing."""
    from scripts.meta.task_graph import load_graph, run_graph

    graph = load_graph(task_path)
    mcp_configs = _load_mcp_registry()

    print(f"Graph: {graph.meta.id}")
    print(f"Description: {graph.meta.description}")
    print(f"Tasks: {len(graph.tasks)}, Waves: {len(graph.waves)}")
    print(f"Timeout: {graph.meta.timeout_minutes}m, Checkpoint: {graph.meta.checkpoint}")

    for wave_idx, wave in enumerate(graph.waves):
        print(f"\nWave {wave_idx + 1}:")
        for tid in wave:
            task = graph.tasks[tid]
            print(f"  {tid}:")
            print(f"    difficulty={task.difficulty} agent={task.agent}", end="")
            if task.model:
                print(f" model={task.model}", end="")
            else:
                print(" model=REQUIRED_MISSING", end="")
            print()
            if task.depends_on:
                print(f"    depends_on: {task.depends_on}")
            if task.mcp_servers:
                available = [s for s in task.mcp_servers if s in mcp_configs]
                missing = [s for s in task.mcp_servers if s not in mcp_configs]
                if available:
                    print(f"    mcp: {available}")
                if missing:
                    print(f"    MISSING mcp: {missing}")
            if task.validators:
                print(f"    validators: {len(task.validators)}")
                for v in task.validators:
                    print(f"      - {v.get('type', '?')}: {v.get('path', v.get('command', '...'))}")


# ---------------------------------------------------------------------------
# Flat task runner (existing .md format)
# ---------------------------------------------------------------------------


async def _run_flat_task(task_path: Path, *, parent_trace_id: str | None = None) -> bool:
    """Run a flat .md task. Returns True if completed."""
    task = TaskSpec.from_file(task_path)
    report_payload: dict[str, Any] = {
        "report_version": "v1",
        "task_type": "flat",
        "task_id": task.id,
        "task_file": task_path.name,
        "agent": task.agent,
        "project": task.project,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _record_decision_event(
        report_payload,
        decision_stage="dispatch",
        selected_action="load_flat_task",
        decision_reason="task file is markdown frontmatter task; dispatching to flat runner",
        confidence=1.0,
        evidence_refs=[task_path.name],
    )

    # Budget check
    budget_ok, spent_today = _check_daily_budget()
    if not budget_ok:
        log.warning("Daily budget exceeded ($%.2f of $%.2f). Skipping.", spent_today, DAILY_BUDGET_USD)
        _record_decision_event(
            report_payload,
            decision_stage="preflight",
            selected_action="skip_task_budget_exceeded",
            decision_reason=f"daily budget exceeded (spent={spent_today:.2f}, limit={DAILY_BUDGET_USD:.2f})",
            evidence_refs=["OPENCLAW_DAILY_BUDGET_EXCEEDED"],
        )
        report_payload["status"] = "skipped_budget"
        report_payload["primary_failure_class"] = "provider"
        report_payload["failure_event_codes"] = ["OPENCLAW_DAILY_BUDGET_EXCEEDED"]
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(task.id, report_payload)
        return False

    log.info("=== Running task: %s ===", task.title)
    log.info("Agent: %s | Project: %s | Priority: %s", task.agent, task.project, task.priority)

    preflight = _run_flat_preflight(task)
    report_payload["preflight"] = preflight
    if not preflight["passed"]:
        _record_decision_event(
            report_payload,
            decision_stage="preflight",
            selected_action="abort_flat_preflight",
            decision_reason=f"deterministic preflight failed with {len(preflight.get('failures', []))} failure(s)",
            evidence_refs=preflight.get("failure_event_codes") or [],
        )
        destination = "failed"
        failed_path = _move_task(task_path, destination)
        report_payload["status"] = "failed_preflight"
        report_payload["destination"] = destination
        report_payload["failed_task_path"] = str(failed_path)
        report_payload["primary_failure_class"] = preflight.get("primary_failure_class")
        report_payload["failure_event_codes"] = preflight.get("failure_event_codes")
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(task.id, report_payload)
        return False

    active_path: Path | None = None
    pre_status = ""
    try:
        # Capture pre-execution git state to distinguish agent changes from pre-existing
        import subprocess
        pre_git = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=task.project, capture_output=True, text=True, timeout=10,
        )
        pre_status = pre_git.stdout.strip()

        # Move to active
        active_path = _move_task(task_path, "active")
        _append_status_log(active_path, f"Started by run_task.py (agent={task.agent})")

        # Pre-dispatch: safety limits, integrity baseline, attempt history
        attempt_context = ""
        try:
            from agentic_scaffolding.hooks import pre_dispatch as _pre_dispatch
            state_dir = active_path.parent / ".agentic_state" / task.id
            pre_result = _pre_dispatch(Path(task.project).expanduser(), state_dir)
            if not pre_result.proceed:
                log.warning("Pre-dispatch blocked: %s", pre_result.reason)
                _append_status_log(active_path, f"Pre-dispatch blocked: {pre_result.reason}")
                _move_task(active_path, "failed")
                _record_decision_event(
                    report_payload,
                    decision_stage="preflight",
                    selected_action="abort_pre_dispatch",
                    decision_reason=pre_result.reason or "pre-dispatch hook blocked execution",
                    evidence_refs=["OPENCLAW_PREFLIGHT_SAFETY_LIMIT"],
                )
                report_payload["status"] = "failed_preflight"
                report_payload["destination"] = "failed"
                report_payload["primary_failure_class"] = "composability"
                report_payload["failure_event_codes"] = ["OPENCLAW_PREFLIGHT_SAFETY_LIMIT"]
                report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
                _write_task_report(task.id, report_payload)
                return False
            attempt_context = pre_result.attempt_context
        except ImportError:
            pass  # agentic_scaffolding not installed — skip hooks
        except Exception as exc:
            log.warning("Pre-dispatch hook error (continuing): %s", exc)

        # Execute
        _record_decision_event(
            report_payload,
            decision_stage="execution",
            selected_action="execute_flat_task",
            decision_reason=f"invoking agent runner ({task.agent}) after successful preflight",
        )
        result = await _execute_flat_task(
            task, parent_trace_id=parent_trace_id,
            attempt_context=attempt_context,
        )
        _append_status_log(active_path, f"Agent returned (cost=${result['cost_usd']:.4f}, duration={result['duration_s']}s)")
        report_payload["run"] = {
            "trace_id": result.get("trace_id"),
            "model": result.get("model"),
            "cost_usd": result.get("cost_usd"),
            "duration_s": result.get("duration_s"),
            "tool_calls_count": result.get("tool_calls_count"),
            "finish_reason": result.get("finish_reason"),
            "usage": result.get("usage"),
        }
        report_payload["primary_failure_class"] = result.get("primary_failure_class") or "none"
        report_payload["failure_event_codes"] = result.get("failure_event_codes") or []
        report_payload["failure_event_code_counts"] = result.get("failure_event_code_counts") or {}

        # Write agent response
        response_summary = result["content"][:2000]
        if len(result["content"]) > 2000:
            response_summary += "\n\n... (truncated)"
        _append_result(active_path, response_summary)

        # Extract spawned tasks and escalations from agent output
        try:
            from spawn_extract import extract_escalations, extract_spawned_tasks
            from spawn_extract import write_escalation, write_spawned_task

            spawned = extract_spawned_tasks(result["content"])
            escalated = extract_escalations(result["content"])

            pending_dir = TASKS_DIR / "pending"
            decisions_dir = Path.home() / ".openclaw" / "workspace" / "decisions"

            for st in spawned:
                write_spawned_task(st, pending_dir, spawned_by=task.id)
            for esc in escalated:
                write_escalation(esc, task.id, decisions_dir)

            if spawned or escalated:
                log.info("Extracted %d spawned task(s), %d escalation(s)", len(spawned), len(escalated))
                _append_status_log(active_path, f"Spawned {len(spawned)} task(s), {len(escalated)} escalation(s)")

            report_payload["spawned_tasks"] = [s.id for s in spawned]
            report_payload["escalations"] = len(escalated)
        except Exception as exc:
            log.error("Spawn/escalation extraction failed (continuing): %s", exc)
            report_payload["spawned_tasks"] = []
            report_payload["escalations"] = 0

        # Validate
        validation_passed, validation_details = _run_validation(task, pre_status)
        _append_status_log(active_path, f"Validation: {'PASS' if validation_passed else 'FAIL'} — {validation_details}")

        # Post-validation: integrity verify, stagnation/oscillation, update history
        try:
            from agentic_scaffolding.hooks import post_validation as _post_validation
            state_dir = active_path.parent / ".agentic_state" / task.id
            post_result = _post_validation(
                workspace=Path(task.project).expanduser(),
                state_path=state_dir,
                success=validation_passed,
                error_text=result["content"][:500] if not validation_passed else "",
                strategy=task.objective or "",
                evidence=validation_details,
            )
            if not post_result.integrity_ok:
                log.warning("Integrity violation: %s", post_result.integrity_error)
                _append_status_log(active_path, f"Integrity violation: {post_result.integrity_error}")
            if post_result.stagnation:
                log.warning("Stagnation detected — same error repeating")
                _append_status_log(active_path, "Stagnation detected")
            if post_result.oscillation:
                log.warning("Oscillation detected — error pattern recurring")
                _append_status_log(active_path, "Oscillation detected")
        except ImportError:
            pass  # agentic_scaffolding not installed — skip hooks
        except Exception as exc:
            log.warning("Post-validation hook error (continuing): %s", exc)

        # Archive
        destination = "completed" if validation_passed else "failed"
        _move_task(active_path, destination)
        _record_decision_event(
            report_payload,
            decision_stage="routing",
            selected_action=f"route_to_{destination}",
            decision_reason=f"post-execution validation {'passed' if validation_passed else 'failed'}",
        )
        _log_cost(task.id, task.agent, result.get("model", ""),
                  result.get("cost_usd", 0), result.get("duration_s", 0),
                  "completed" if validation_passed else "failed")
        report_payload["status"] = "completed" if validation_passed else "failed"
        report_payload["destination"] = destination
        report_payload["validation"] = {
            "passed": validation_passed,
            "details": validation_details,
        }
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(task.id, report_payload)

        log.info("=== Task %s: %s ===", destination.upper(), task.title)
        return validation_passed

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        err_msg = str(e).strip()
        log.error("Task execution failed: %s: %s\n%s", type(e).__name__, e, tb)

        recovery_context = _postsuccess_recovery_context(
            task,
            type(e).__name__,
            err_msg,
            pre_status,
        )
        if recovery_context is not None:
            log.warning(
                "Recoverable post-success agent error: %s",
                recovery_context["reason"],
            )
            _record_decision_event(
                report_payload,
                decision_stage="error_handling",
                selected_action="treat_postsuccess_agent_error_as_recoverable",
                decision_reason=(
                    f"{recovery_context['reason']}; detected commit or meaningful "
                    "bounded changes, "
                    "running validation before routing"
                ),
            )
            if active_path is None:
                active_path = _move_task(task_path, "active")
            _append_status_log(
                active_path,
                f"Recovered post-success agent error: {type(e).__name__}: {e}",
            )
            if recovery_context["changed_lines"]:
                _append_status_log(
                    active_path,
                    "Recovery evidence — meaningful new changes:\n"
                    + "\n".join(recovery_context["changed_lines"]),
                )
            validation_passed, validation_details = _run_validation(task, pre_status)
            _append_status_log(active_path, f"Validation: {'PASS' if validation_passed else 'FAIL'} — {validation_details}")
            destination = "completed" if validation_passed else "failed"
            _move_task(active_path, destination)
            _record_decision_event(
                report_payload,
                decision_stage="routing",
                selected_action=f"route_to_{destination}",
                decision_reason=f"post-recovery validation {'passed' if validation_passed else 'failed'}",
            )
            _log_cost(task.id, task.agent, "", 0, 0,
                      "completed" if validation_passed else "failed")
            report_payload["status"] = "completed" if validation_passed else "failed"
            report_payload["destination"] = destination
            report_payload["validation"] = {
                "passed": validation_passed,
                "details": validation_details,
            }
            report_payload["recovered_exception"] = f"{type(e).__name__}: {e}"
            report_payload["recovery_reason"] = recovery_context["reason"]
            report_payload["recovery_signal"] = {
                "committed": recovery_context["committed"],
                "changed_lines": recovery_context["changed_lines"],
            }
            report_payload["primary_failure_class"] = report_payload.get("primary_failure_class") or "none"
            report_payload["failure_event_codes"] = report_payload.get("failure_event_codes") or []
            report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            _write_task_report(task.id, report_payload)
            return validation_passed

        target_path = active_path if active_path is not None else task_path
        if active_path is None:
            target_path = _move_task(task_path, "active")
            active_path = target_path
        _append_status_log(target_path, f"ERROR ({type(e).__name__}): {e}")

        # Record failure in agentic_scaffolding state even on exception
        try:
            from agentic_scaffolding.hooks import post_validation as _post_validation
            state_dir = target_path.parent / ".agentic_state" / task.id
            _post_validation(
                workspace=Path(task.project).expanduser(),
                state_path=state_dir,
                success=False,
                error_text=err_msg[:500],
                strategy=task.objective or "",
                enable_integrity=False,  # Skip integrity on crash
            )
        except Exception:
            pass  # Best-effort

        _move_task(target_path, "failed")
        _log_cost(task.id, task.agent, "", 0, 0, "failed")
        report_payload["status"] = "failed_exception"
        report_payload["destination"] = "failed"
        _record_decision_event(
            report_payload,
            decision_stage="error_handling",
            selected_action="route_to_failed_exception",
            decision_reason=f"flat task raised {type(e).__name__}",
            evidence_refs=["OPENCLAW_FLAT_RUNTIME_EXCEPTION"],
        )
        report_payload["primary_failure_class"] = "provider"
        report_payload["failure_event_codes"] = ["OPENCLAW_FLAT_RUNTIME_EXCEPTION"]
        report_payload["exception"] = f"{type(e).__name__}: {e}"
        report_payload["finished_at"] = datetime.now(timezone.utc).isoformat()
        _write_task_report(task.id, report_payload)
        return False


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


def _is_graph_file(path: Path) -> bool:
    return path.suffix in (".yaml", ".yml")


async def run_task(task_path: Path, *, parent_trace_id: str | None = None) -> bool:
    """Main entry — dispatches to flat or graph handler based on extension."""
    if _is_graph_file(task_path):
        return await _run_graph_task(task_path)
    else:
        return await _run_flat_task(task_path, parent_trace_id=parent_trace_id)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _list_pending() -> tuple[list[TaskSpec], list[Path]]:
    """List pending flat tasks and graph files."""
    pending_dir = TASKS_DIR / "pending"
    if not pending_dir.exists():
        return [], []

    flat_tasks: list[TaskSpec] = []
    for f in sorted(pending_dir.glob("*.md")):
        try:
            flat_tasks.append(TaskSpec.from_file(f))
        except Exception as e:
            log.warning("Skipping %s: %s", f.name, e)
    flat_tasks.sort(key=lambda t: t.sort_key())

    graph_files = sorted(pending_dir.glob("*.yaml")) + sorted(pending_dir.glob("*.yml"))

    return flat_tasks, graph_files


def main() -> None:
    """CLI entry point for the multi-agent task runner."""
    parser = argparse.ArgumentParser(description="Multi-agent task runner")
    parser.add_argument("task_file", nargs="?", help="Path to task file (default: pick from pending/)")
    parser.add_argument("--list", action="store_true", help="List pending tasks")
    parser.add_argument("--dry-run", action="store_true", help="Parse and show what would run")
    parser.add_argument(
        "--scan-model-gaps",
        action="store_true",
        help="Scan pending/active tasks for missing explicit model declarations.",
    )
    parser.add_argument(
        "--repair-flat-models",
        action="store_true",
        help="Plan explicit model patches for flat tasks missing `model:`.",
    )
    parser.add_argument(
        "--repair-default-model",
        default=None,
        help="Fallback model used for direct or unknown flat-task agents during repair.",
    )
    parser.add_argument(
        "--apply-repairs",
        action="store_true",
        help="Write flat-task model repairs in place. Without this, repair is dry-run only.",
    )
    parser.add_argument("--loop", action="store_true", help="Run continuously and drain queue")
    parser.add_argument(
        "--allow-legacy",
        action="store_true",
        help="Allow --loop to start even when the queue still has legacy model gaps.",
    )
    parser.add_argument("--poll-interval", type=float, default=30.0,
                        help="Seconds between queue checks in --loop mode (default: 30)")
    parser.add_argument("--max-idle-cycles", type=int, default=0,
                        help="Stop loop after N idle polls (0 = never stop)")
    parser.add_argument("--max-runs", type=int, default=0,
                        help="Stop loop after N task runs (0 = unlimited)")
    parser.add_argument("--recover-stale-after", type=int, default=6 * 60 * 60,
                        help="Recover tasks stuck in active/ older than this many seconds")
    parser.add_argument("--parent-trace-id", type=str, default=None,
                        help="Parent trace_id for hierarchical cost tracking (e.g. openclaw.morning_brief)")
    args = parser.parse_args()

    if args.apply_repairs and not args.repair_flat_models:
        log.error("--apply-repairs requires --repair-flat-models")
        sys.exit(2)
    if args.allow_legacy and not args.loop:
        log.error("--allow-legacy requires --loop")
        sys.exit(2)

    if args.list:
        flat_tasks, graph_files = _list_pending()
        if not flat_tasks and not graph_files:
            print("No pending tasks.")
            return
        for t in flat_tasks:
            print(f"  [{t.priority}] {t.id}: {t.title} (agent={t.agent}, project={t.project})")
        for g in graph_files:
            try:
                from scripts.meta.task_graph import load_graph
                graph = load_graph(g)
                print(f"  [graph] {graph.meta.id}: {graph.meta.description} "
                      f"({len(graph.tasks)} tasks, {len(graph.waves)} waves)")
            except Exception as e:
                print(f"  [graph] {g.name}: ERROR — {e}")
        return

    if args.scan_model_gaps:
        flat_gaps, graph_gaps = _collect_model_gaps()
        if not _print_model_gap_report(flat_gaps, graph_gaps):
            sys.exit(1)
        return

    if args.repair_flat_models:
        if args.task_file:
            log.error("--repair-flat-models cannot be combined with an explicit task_file")
            sys.exit(2)
        if args.loop:
            log.error("--repair-flat-models cannot be combined with --loop")
            sys.exit(2)

        flat_gaps = _scan_flat_model_gaps()
        if not flat_gaps:
            print("No flat model gaps found.")
            return

        try:
            repair_plan = _plan_flat_task_model_repairs(
                flat_gaps,
                default_model=args.repair_default_model,
            )
        except ValueError as exc:
            log.error(str(exc))
            sys.exit(2)

        print("Flat model repair plan:")
        for path, metadata, repaired_model in repair_plan:
            project = metadata.get("project", "unknown")
            agent = metadata.get("agent", "direct")
            print(f"  {path} -> model={repaired_model} (agent={agent}, project={project})")

        if not args.apply_repairs:
            print("Dry-run only. Re-run with --apply-repairs to write files.")
            return

        for path, _, repaired_model in repair_plan:
            _apply_flat_task_model_patch(path, repaired_model)
        print(f"Applied model patches to {len(repair_plan)} flat task(s).")
        return

    if args.loop:
        if args.task_file:
            log.error("--loop cannot be combined with an explicit task_file")
            sys.exit(2)
        flat_gaps, graph_gaps = _collect_model_gaps()
        if args.allow_legacy:
            if flat_gaps or graph_gaps:
                _append_supervisor_log(
                    "supervisor_model_gap_gate_bypassed",
                    flat_gap_count=len(flat_gaps),
                    graph_gap_count=len(graph_gaps),
                )
        elif not _print_model_gap_report(flat_gaps, graph_gaps):
            _append_supervisor_log(
                "supervisor_blocked_model_gaps",
                flat_gap_count=len(flat_gaps),
                graph_gap_count=len(graph_gaps),
            )
            print("Loop blocked: model gap checks must pass before starting --loop.")
            print(
                "Run with --scan-model-gaps to inspect gaps or "
                "--repair-flat-models to patch legacy flat tasks."
            )
            print("Use --allow-legacy only for an explicit transitional bypass.")
            sys.exit(1)
        try:
            with _SupervisorLock(SUPERVISOR_LOCK):
                rc = _run_supervisor_loop(
                    poll_interval_s=args.poll_interval,
                    max_idle_cycles=args.max_idle_cycles,
                    max_runs=args.max_runs,
                    stale_after_s=args.recover_stale_after,
                )
                sys.exit(rc)
        except RuntimeError as e:
            log.error(str(e))
            sys.exit(2)

    # Resolve task file
    if args.task_file:
        task_path = Path(args.task_file).resolve()
    else:
        flat_tasks, graph_files = _list_pending()
        if not flat_tasks and not graph_files:
            print("No pending tasks.")
            return
        # Flat tasks take priority; graphs picked if no flat tasks pending
        if flat_tasks:
            task_path = flat_tasks[0].source_path
        else:
            task_path = graph_files[0]
        log.info("Auto-selected: %s", task_path.name)

    if not task_path.exists():
        log.error("Task file not found: %s", task_path)
        sys.exit(1)

    if args.dry_run:
        if _is_graph_file(task_path):
            _dry_run_graph(task_path)
        else:
            task = TaskSpec.from_file(task_path)
            print(f"Title: {task.title}")
            print(f"Agent: {task.agent}")
            print(f"Model: {task.model or 'MISSING'}")
            print(f"Project: {task.project}")
            print(f"Priority: {task.priority}")
            print(f"Constraints: max_turns={task.constraints.max_turns}, budget=${task.constraints.max_budget_usd}")
            print(f"\n--- Prompt ---\n")
            print(_build_prompt(task))
        return

    success = asyncio.run(run_task(task_path, parent_trace_id=args.parent_trace_id))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
