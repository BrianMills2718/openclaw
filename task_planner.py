#!/usr/bin/env python3
"""Goal-aware task planner — the core of beach mode.

Reads project goals from multiple sources and generates prioritized
task files for run_task.py to execute. This is an LLM-backed planner
that understands context, prioritizes by ecosystem goals, and generates
well-scoped tasks.

Goal sources (read in priority order):
1. ECOSYSTEM_STATUS.md — gaps + planned extensions per layer
2. Per-project CLAUDE.md — "In Progress", "Current State", roadmap
3. Active plans in docs/plans/ — incomplete steps in in-progress plans
4. PROJECTS.md — project priority ordering
5. Hygiene signals from ecosystem_sweep.py

Output: task .md files in ~/.openclaw/tasks/pending/

Usage:
    # Generate tasks (dry-run)
    python task_planner.py --dry-run

    # Generate and write to pending/
    python task_planner.py

    # Limit generation
    python task_planner.py --max-tasks 5
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _prepend_repo_root_if_present(path: Path) -> None:
    """Prepend a repo root to sys.path when it exists and is not already present."""

    if not path.is_dir():
        return
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def _bootstrap_shared_import_roots() -> None:
    """Expose shared editable repos through stable repo-root import paths."""

    projects_root = Path(
        os.environ.get("PROJECTS_ROOT", str(Path.home() / "projects"))
    ).expanduser().resolve()
    for repo_name in ("llm_client",):
        _prepend_repo_root_if_present(projects_root / repo_name)


_bootstrap_shared_import_roots()

# Paths
HOME = Path.home()
PROJECTS_DIR = Path(
    os.environ.get("OPENCLAW_PROJECTS_DIR", str(HOME / "projects"))
).expanduser().resolve()
PROJECT_META = Path(
    os.environ.get("PROJECT_META_ROOT", str(PROJECTS_DIR / "project-meta"))
).expanduser().resolve()
ECOSYSTEM_STATUS = PROJECT_META / "vision" / "ECOSYSTEM_STATUS.md"
PROJECTS_MD = Path(
    os.environ.get("OPENCLAW_PROJECTS_MD", str(HOME / ".openclaw" / "workspace" / "PROJECTS.md"))
).expanduser().resolve()
PROJECT_GRAPH = PROJECT_META / "PROJECT_GRAPH.json"
TASKS_DIR = Path(
    os.environ.get("OPENCLAW_TASKS_DIR", str(HOME / ".openclaw" / "tasks"))
).expanduser().resolve()
PENDING_DIR = TASKS_DIR / "pending"
ACTIVE_DIR = TASKS_DIR / "active"
COMPLETED_DIR = TASKS_DIR / "completed"
FAILED_DIR = TASKS_DIR / "failed"
PROMPT_PATH = Path(
    os.environ.get(
        "OPENCLAW_TASK_PLANNER_PROMPT",
        str(Path(__file__).resolve().parent / "prompts" / "task_planner.yaml"),
    )
).expanduser().resolve()
TARGET_PROJECTS = os.environ.get("OPENCLAW_MISSION_TARGET_PROJECTS", "")

# Default LLM model for planning (cheap, fast)
PLANNER_MODEL = "gemini/gemini-2.5-flash"
TASK_KINDS = {"code_change", "docs_only", "analysis_only", "queue_maintenance"}
DELIVERY_MODES = {"flat", "review_cycle"}


def _normalize_target_projects(raw_targets: list[str] | str | None) -> list[Path] | None:
    """Normalize optional target project overrides to absolute Path objects."""

    if raw_targets is None:
        return None
    if isinstance(raw_targets, str):
        if not raw_targets.strip():
            return None
        raw_values = [value.strip() for value in raw_targets.split("|") if value.strip()]
    else:
        raw_values = [str(value).strip() for value in raw_targets if str(value).strip()]
    if not raw_values:
        return None
    return [Path(value).expanduser().resolve() for value in raw_values]


def _get_target_projects() -> list[Path] | None:
    """Return resolved mission target projects, when provided."""

    return _normalize_target_projects(TARGET_PROJECTS)


def _is_target_project(path: Path) -> bool:
    """Check whether a project should be included in planning context."""

    targets = _get_target_projects()
    if not targets:
        return True
    normalized = path.expanduser().resolve()
    return any(normalized == target for target in targets)


def _read_file_safe(path: Path, max_chars: int = 8000) -> str:
    """Read a file, returning empty string if it doesn't exist."""
    if not path.is_file():
        return ""
    content = path.read_text()
    if len(content) > max_chars:
        content = content[:max_chars] + "\n... (truncated)"
    return content


def _extract_section(content: str, heading: str) -> str:
    """Extract a markdown section by heading (## level)."""
    pattern = rf"^## {re.escape(heading)}.*?$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^## ", content[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(content)
    return content[start:end].strip()


def read_project_goals() -> str:
    """Read "In Progress" and roadmap sections from active project CLAUDE.md files.

    Scans PROJECT_GRAPH.json for active projects, reads each CLAUDE.md,
    and extracts goal-relevant sections.
    """
    if not PROJECT_GRAPH.is_file():
        return "PROJECT_GRAPH.json not found"

    raw = json.loads(PROJECT_GRAPH.read_text())
    nodes: list[dict[str, Any]] = raw if isinstance(raw, list) else raw.get("nodes", [])

    goals: list[str] = []
    for node in nodes:
        path_str = node.get("path", "")
        if not path_str:
            continue
        path = Path(path_str).expanduser()
        if not _is_target_project(path):
            continue
        claude_md = path / "CLAUDE.md"
        if not claude_md.is_file():
            continue

        content = claude_md.read_text()
        name = node.get("name", node.get("id", path.name))

        # Look for goal-relevant sections
        sections_to_find = ["In Progress", "Current State", "Roadmap", "Next Steps", "Planned"]
        found: list[str] = []
        for section in sections_to_find:
            extracted = _extract_section(content, section)
            if extracted:
                found.append(f"### {section}\n{extracted[:500]}")

        if found:
            goals.append(f"## {name} ({path})\n" + "\n".join(found))

    if not goals:
        return "No project goals found in CLAUDE.md files"

    # Limit total size
    combined = "\n\n".join(goals)
    if len(combined) > 6000:
        combined = combined[:6000] + "\n... (truncated)"
    return combined


def read_ecosystem_gaps() -> str:
    """Read gaps and planned extensions from ECOSYSTEM_STATUS.md."""
    content = _read_file_safe(ECOSYSTEM_STATUS, max_chars=4000)
    if not content:
        return "ECOSYSTEM_STATUS.md not found"

    # Extract the most relevant sections
    sections = []
    for heading in ["Ecosystem Layer Status", "Centralization Buckets", "Prioritized Next Steps"]:
        section = _extract_section(content, heading)
        if section:
            sections.append(f"### {heading}\n{section[:1500]}")

    return "\n\n".join(sections) if sections else content[:4000]


def read_active_plans() -> str:
    """Read incomplete steps from active plans across projects.

    Scans docs/plans/ in active projects for plans with status
    'in-progress' or 'active'.
    """
    if not PROJECT_GRAPH.is_file():
        return "No active plans found"

    raw = json.loads(PROJECT_GRAPH.read_text())
    nodes: list[dict[str, Any]] = raw if isinstance(raw, list) else raw.get("nodes", [])

    plans: list[str] = []
    for node in nodes:
        path_str = node.get("path", "")
        if not path_str:
            continue
        path = Path(path_str).expanduser()
        if not _is_target_project(path):
            continue
        plans_dir = path / "docs" / "plans"
        if not plans_dir.is_dir():
            continue

        for plan_file in plans_dir.glob("*.md"):
            if plan_file.name in ("CLAUDE.md", "TEMPLATE.md", "README.md"):
                continue
            content = plan_file.read_text()
            # Check if plan is active/in-progress
            lower = content.lower()
            if "status: in-progress" in lower or "status: active" in lower or "in progress" in lower[:500]:
                # Extract incomplete checklist items
                incomplete = [
                    line.strip() for line in content.splitlines()
                    if line.strip().startswith("- [ ]")
                ]
                if incomplete:
                    name = node.get("name", node.get("id", path.name))
                    plans.append(
                        f"**{name}** — {plan_file.name}:\n"
                        + "\n".join(incomplete[:5])
                    )

    if not plans:
        return "No active plans with incomplete steps"

    combined = "\n\n".join(plans)
    if len(combined) > 3000:
        combined = combined[:3000] + "\n... (truncated)"
    return combined


def read_existing_tasks() -> str:
    """Read pending, active, completed, and failed task IDs to avoid duplication."""
    tasks: list[str] = []
    for d in [PENDING_DIR, ACTIVE_DIR]:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.suffix in (".md", ".yaml", ".yml"):
                tasks.append(f"- {f.stem} ({d.name})")

    return "\n".join(tasks) if tasks else "No pending or active tasks"


def read_completed_tasks() -> str:
    """Read completed and failed task IDs so the planner knows what's done.

    This is the key mechanism preventing task regeneration: the planner sees
    what was already completed (or failed permanently) and generates only
    new work.
    """
    tasks: list[str] = []
    for d, label in [(COMPLETED_DIR, "completed"), (FAILED_DIR, "failed")]:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix in (".md", ".yaml", ".yml"):
                # Extract title from frontmatter if available
                title = f.stem
                try:
                    content = f.read_text(encoding="utf-8")
                    for line in content.splitlines():
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break
                except Exception:
                    pass
                tasks.append(f"- {f.stem}: {title} ({label})")

    return "\n".join(tasks) if tasks else "No completed or failed tasks yet"


def run_hygiene_sweep(target_projects: list[Path] | None = None) -> str:
    """Run ecosystem_sweep and return summarized results.

    When target_projects is set, passes them directly to the sweep to avoid
    scanning all 70+ projects.
    """
    sweep_script = PROJECT_META / "scripts" / "ecosystem_sweep.py"
    if not sweep_script.is_file():
        return "ecosystem_sweep.py not found"

    sys.path.insert(0, str(sweep_script.parent))
    try:
        import ecosystem_sweep
        result = ecosystem_sweep.run_sweep(target_paths=target_projects)
    except Exception as e:
        return f"Sweep failed: {e}"

    lines: list[str] = []
    for proj in result.results:
        if proj.issues:
            lines.append(f"- **{proj.name}**: {', '.join(proj.issues)}")

    scope = ""
    if target_projects:
        scope = f" (scoped to {', '.join(p.name for p in target_projects)})"

    if not lines:
        return f"All projects clean{scope} — no hygiene issues found"

    return f"{len(lines)}/{result.projects_scanned} projects have issues{scope}:\n" + "\n".join(lines)


def _planner_task_id(task: dict[str, Any], created_at: datetime) -> str:
    """Return the deterministic queue task id for one planner-emitted task."""

    return f"planner-{created_at.strftime('%Y-%m-%d')}-{task['id']}"


def _coerce_file_scope(raw_scope: Any) -> list[str]:
    """Normalize optional planner file scope to a clean string list."""

    if raw_scope is None:
        return []
    if isinstance(raw_scope, str):
        normalized = raw_scope.strip()
        return [normalized] if normalized else []
    if isinstance(raw_scope, list):
        return [str(item).strip() for item in raw_scope if str(item).strip()]
    raise ValueError(f"file_scope must be a list of strings or null, got {type(raw_scope).__name__}")


def _validate_generated_task(task: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize the planner delivery contract for one task."""

    normalized = dict(task)
    task_kind = str(normalized.get("task_kind", "")).strip()
    delivery_mode = str(normalized.get("delivery_mode", "")).strip()
    review_rounds = normalized.get("review_rounds")
    file_scope = _coerce_file_scope(normalized.get("file_scope"))

    if task_kind not in TASK_KINDS:
        raise ValueError(f"task_kind must be one of {sorted(TASK_KINDS)}, got {task_kind!r}")
    if delivery_mode not in DELIVERY_MODES:
        raise ValueError(
            f"delivery_mode must be one of {sorted(DELIVERY_MODES)}, got {delivery_mode!r}"
        )

    if task_kind == "code_change" and delivery_mode != "review_cycle":
        raise ValueError("code_change tasks must use delivery_mode=review_cycle")
    if task_kind != "code_change" and delivery_mode != "flat":
        raise ValueError(f"{task_kind} tasks must use delivery_mode=flat")

    if delivery_mode == "review_cycle":
        if not isinstance(review_rounds, int) or review_rounds < 1:
            raise ValueError("review_cycle tasks require review_rounds >= 1")
    elif review_rounds is not None:
        raise ValueError("flat tasks must not define review_rounds")

    normalized["task_kind"] = task_kind
    normalized["delivery_mode"] = delivery_mode
    normalized["file_scope"] = file_scope
    normalized["review_rounds"] = review_rounds
    targets = _get_target_projects()
    if targets and len(targets) == 1:
        normalized["project"] = str(targets[0])
    else:
        project_path = Path(str(normalized.get("project", ""))).expanduser().resolve()
        if targets and all(project_path != target for target in targets):
            raise ValueError(
                "planner task project must match one of the explicit target projects, "
                f"got {project_path}"
            )
        if not project_path.is_dir():
            raise ValueError(f"planner task project path does not exist: {project_path}")
        normalized["project"] = str(project_path)
    return normalized


def _planner_lineage(task: dict[str, Any], *, task_id: str, created_at: datetime) -> dict[str, Any]:
    """Return planner lineage metadata embedded into queue artifacts."""

    return {
        "planner_task_id": task_id,
        "planner_task_slug": task["id"],
        "goal_advanced": task["goal_advanced"],
        "generated_at": created_at.isoformat(),
    }


def _review_cycle_runtime_model(task: dict[str, Any]) -> str:
    """Map planner-selected workspace agents to graph-runtime model aliases."""

    agent = str(task["agent"]).strip()
    if agent == "claude":
        return "claude-code"
    if agent in {"codex", "claude-code"}:
        return agent
    raise ValueError(f"review_cycle tasks require workspace agents, got {agent!r}")


def write_flat_task_file(
    task: dict[str, Any],
    *,
    task_id: str,
    created_at: datetime,
) -> Path:
    """Write one planner task to the flat markdown queue format."""

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", task_id)

    frontmatter = {
        "id": task_id,
        "priority": task["priority"],
        "agent": task["agent"],
        "model": task["model"],
        "project": task["project"],
        "created": created_at.isoformat(),
        "status": "pending",
        "task_kind": task["task_kind"],
        "delivery_mode": task["delivery_mode"],
        "planner_lineage": _planner_lineage(task, task_id=task_id, created_at=created_at),
        "constraints": {
            "max_turns": task["max_turns"],
            "max_budget_usd": task["max_budget_usd"],
            "file_scope": task["file_scope"],
        },
    }

    try:
        import yaml
        fm_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    except ImportError:
        fm_str = json.dumps(frontmatter, indent=2)

    body = f"""# {task['title']}

## Objective
{task['objective']}

Advances: {task['goal_advanced']}

## Acceptance Criteria
"""
    for criterion in task["acceptance_criteria"]:
        body += f"- [ ] {criterion}\n"

    content = f"---\n{fm_str}---\n{body}"
    dest = PENDING_DIR / f"{safe_name}.md"
    dest.write_text(content)
    return dest


def write_review_cycle_task_file(
    task: dict[str, Any],
    *,
    task_id: str,
    created_at: datetime,
    config: dict[str, Any] | None = None,
) -> Path:
    """Write one planner task as a review-cycle graph YAML artifact."""

    import yaml

    from launch_review_cycle import _load_config, build_graph

    cfg = dict(config) if config is not None else _load_config(None)
    cfg = {
        **cfg,
        "agents": {
            **cfg["agents"],
            "implement": {
                **cfg["agents"]["implement"],
                "agent": task["agent"],
                "model": _review_cycle_runtime_model(task),
            },
            "synthesis": {
                **cfg["agents"]["synthesis"],
                "agent": task["agent"],
                "model": _review_cycle_runtime_model(task),
            },
        },
    }
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    project_path = Path(task["project"]).expanduser().resolve()
    graph = build_graph(
        cycle_id=task_id,
        project_path=project_path,
        objective=task["objective"],
        rounds=task["review_rounds"],
        config=cfg,
        metadata={
            "task_kind": task["task_kind"],
            "delivery_mode": task["delivery_mode"],
            "review_rounds": task["review_rounds"],
            "file_scope": task["file_scope"],
            "planner_lineage": _planner_lineage(task, task_id=task_id, created_at=created_at),
        },
    )
    dest = PENDING_DIR / f"{re.sub(r'[^a-zA-Z0-9_-]', '_', task_id)}.yaml"
    dest.write_text(yaml.safe_dump(graph, sort_keys=False))
    return dest


def generate_tasks(max_tasks: int = 8) -> list[dict[str, Any]]:
    """Generate prioritized tasks by sending context to the LLM planner.

    Gathers context from all sources, sends to LLM with structured output,
    and returns parsed task list.
    """
    # Gather context
    logger.info("Reading project goals...")
    project_goals = read_project_goals()

    logger.info("Reading ecosystem gaps...")
    ecosystem_gaps = read_ecosystem_gaps()

    logger.info("Reading active plans...")
    active_plans = read_active_plans()

    logger.info("Running hygiene sweep...")
    target_projects = _normalize_target_projects(TARGET_PROJECTS)
    hygiene_signals = run_hygiene_sweep(target_projects=target_projects)

    existing_tasks = read_existing_tasks()

    logger.info("Reading completed tasks...")
    completed_tasks = read_completed_tasks()

    # Render prompt
    try:
        from llm_client import render_prompt, call_llm_structured
    except ImportError:
        logger.error(
            "llm_client not installed. Install with: "
            'pip install -e "${PROJECTS_ROOT:-$HOME/projects}/llm_client"'
        )
        raise

    from pydantic import BaseModel, Field

    class TaskItem(BaseModel):
        """A single generated task."""

        id: str = Field(description="Short slug like 'llm-client-add-gpt52pro'")
        priority: str = Field(description="high | medium | low")
        agent: str = Field(description="codex | claude-code")
        model: str = Field(
            description="Exact model to execute this task (for example codex or claude-code)."
        )
        project: str = Field(description="Full path to project directory")
        goal_advanced: str = Field(description="Which specific goal this advances")
        max_budget_usd: float = Field(ge=0.5, le=5.0, description="Budget ceiling")
        max_turns: int = Field(ge=10, le=40, description="Agent turn limit")
        title: str = Field(description="Concise task title")
        objective: str = Field(description="2-3 sentences on what to do")
        acceptance_criteria: list[str] = Field(description="List of testable criteria")
        task_kind: str = Field(
            description="code_change | docs_only | analysis_only | queue_maintenance"
        )
        delivery_mode: str = Field(description="flat | review_cycle")
        file_scope: list[str] | None = Field(
            default=None,
            description="Optional repo-relative file or glob scope for the work",
        )
        review_rounds: int | None = Field(
            default=None,
            description="Required when delivery_mode=review_cycle; null for flat tasks",
        )

    class TaskPlan(BaseModel):
        """The full plan output from the LLM."""

        tasks: list[TaskItem] = Field(max_length=max_tasks)

    messages = render_prompt(
        PROMPT_PATH,
        project_goals=project_goals,
        ecosystem_gaps=ecosystem_gaps,
        active_plans=active_plans,
        hygiene_signals=hygiene_signals,
        existing_tasks=existing_tasks,
        completed_tasks=completed_tasks,
        mission_objective=os.environ.get("OPENCLAW_MISSION_OBJECTIVE", "No explicit mission objective provided."),
        remaining_budget_usd=os.environ.get("OPENCLAW_REMAINING_BUDGET_USD", ""),
    )

    logger.info("Calling LLM planner (%s)...", PLANNER_MODEL)
    plan, meta = call_llm_structured(
        PLANNER_MODEL,
        messages,
        response_model=TaskPlan,
        task="task_planning",
        trace_id=f"beach_mode.planner.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}",
        max_budget=1.0,
    )

    normalized_tasks = [_validate_generated_task(t.model_dump()) for t in plan.tasks]
    logger.info("Generated %d tasks (cost: $%.4f)", len(normalized_tasks), meta.cost)
    return normalized_tasks


def write_task_file(
    task: dict[str, Any],
    *,
    created_at: datetime | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Write a planner task to the appropriate queue artifact type."""

    normalized = _validate_generated_task(task)
    timestamp = created_at or datetime.now(timezone.utc)
    task_id = _planner_task_id(normalized, timestamp)
    if normalized["delivery_mode"] == "flat":
        return write_flat_task_file(normalized, task_id=task_id, created_at=timestamp)
    return write_review_cycle_task_file(
        normalized,
        task_id=task_id,
        created_at=timestamp,
        config=config,
    )


def main() -> None:
    """CLI entry point."""
    global PLANNER_MODEL
    parser = argparse.ArgumentParser(description="Goal-aware task planner for beach mode")
    parser.add_argument("--dry-run", action="store_true", help="Print tasks without writing")
    parser.add_argument("--max-tasks", type=int, default=8, help="Max tasks to generate")
    parser.add_argument("--model", default=PLANNER_MODEL, help="LLM model for planning")
    parser.add_argument(
        "--target-project",
        action="append",
        dest="target_projects",
        help="Restrict planning context to one or more project paths (repeatable).",
    )
    parser.add_argument(
        "--mission-objective",
        help="Optional mission objective to inject into the planning prompt.",
    )
    args = parser.parse_args()

    PLANNER_MODEL = args.model
    if args.target_projects:
        global TARGET_PROJECTS
        TARGET_PROJECTS = "|".join(str(Path(value).expanduser().resolve()) for value in args.target_projects)
    if args.mission_objective:
        os.environ["OPENCLAW_MISSION_OBJECTIVE"] = args.mission_objective

    tasks = generate_tasks(max_tasks=args.max_tasks)

    if args.dry_run:
        print(json.dumps(tasks, indent=2))
        return

    for task in tasks:
        path = write_task_file(task)
        logger.info("Wrote task: %s", path)

    logger.info("Generated %d tasks in %s", len(tasks), PENDING_DIR)


if __name__ == "__main__":
    main()
