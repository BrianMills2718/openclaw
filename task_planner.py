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


VALID_TASK_KINDS = {"code_change", "docs_only", "analysis_only", "queue_maintenance"}
VALID_DELIVERY_MODES = {"flat", "review_cycle"}


def validate_task_delivery_contract(task: dict[str, Any]) -> list[str]:
    """Validate the delivery contract fields of a planner-generated task.

    Returns a list of error strings; empty list means valid.
    Enforced invariants (Plan #2 Phase 0):
    - task_kind must be one of VALID_TASK_KINDS
    - delivery_mode must be one of VALID_DELIVERY_MODES
    - delivery_mode=review_cycle requires task_kind=code_change
    - delivery_mode=review_cycle requires review_rounds to be a positive int
    - delivery_mode=flat must NOT have review_rounds set
    """
    errors: list[str] = []

    task_kind = task.get("task_kind", "")
    delivery_mode = task.get("delivery_mode", "")
    review_rounds = task.get("review_rounds")

    if task_kind not in VALID_TASK_KINDS:
        errors.append(
            f"task_kind='{task_kind}' invalid; must be one of {sorted(VALID_TASK_KINDS)}"
        )
    if delivery_mode not in VALID_DELIVERY_MODES:
        errors.append(
            f"delivery_mode='{delivery_mode}' invalid; must be one of {sorted(VALID_DELIVERY_MODES)}"
        )
    if delivery_mode == "review_cycle" and task_kind != "code_change":
        errors.append(
            f"delivery_mode='review_cycle' requires task_kind='code_change', got '{task_kind}'"
        )
    if delivery_mode == "review_cycle":
        if review_rounds is None or (isinstance(review_rounds, int) and review_rounds < 1):
            errors.append(
                "delivery_mode='review_cycle' requires review_rounds to be a positive integer"
            )
    if delivery_mode == "flat" and review_rounds is not None:
        errors.append(
            f"delivery_mode='flat' must not have review_rounds set (got {review_rounds})"
        )

    return errors


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
        # Delivery contract (Plan #2)
        task_kind: str = Field(
            description=(
                "Classify the work type: "
                "'code_change' for any change to production code, schemas, validators, CLI, or tests; "
                "'docs_only' for documentation, README, CLAUDE.md, or comment-only changes; "
                "'analysis_only' for investigations, research, or triage with no required repo changes; "
                "'queue_maintenance' for queue cleanup, stale-task repair, or runtime bookkeeping."
            )
        )
        delivery_mode: str = Field(
            description=(
                "How to deliver this task: "
                "'review_cycle' for code_change work (routes through implementation + review gate + commit); "
                "'flat' for docs_only, analysis_only, or queue_maintenance work."
            )
        )
        file_scope: list[str] = Field(
            default_factory=list,
            description=(
                "Optional list of repo-relative paths or globs scoping the change. "
                "Required for code_change tasks when scope is known. Empty list means unconstrained."
            ),
        )
        review_rounds: int | None = Field(
            default=None,
            description=(
                "Number of implementation-review rounds. "
                "Required when delivery_mode='review_cycle' (use 1 for first rollout slice). "
                "Must be null when delivery_mode='flat'."
            ),
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

    logger.info("Generated %d tasks (cost: $%.4f)", len(plan.tasks), meta.cost)
    tasks = [t.model_dump() for t in plan.tasks]
    for task in tasks:
        errors = validate_task_delivery_contract(task)
        if errors:
            raise ValueError(
                f"Task '{task['id']}' has invalid delivery contract: {'; '.join(errors)}"
            )
    return tasks


def _make_planner_task_id(task: dict[str, Any]) -> str:
    """Build a deterministic planner task id from the task slug and today's date.

    The id is stable across re-runs on the same calendar day, enabling
    deduplication in the queue without needing a UUID.
    """
    return f"planner-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{task['id']}"


def write_flat_task(task: dict[str, Any]) -> Path:
    """Write a flat .md task to pending/.

    For docs_only, analysis_only, and queue_maintenance work.
    Preserves the original flat-task format that run_task.py expects.
    """
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    task_id = _make_planner_task_id(task)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", task_id)

    frontmatter: dict[str, Any] = {
        "id": task_id,
        "priority": task["priority"],
        "agent": task["agent"],
        "model": task["model"],
        "project": task["project"],
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "constraints": {
            "max_turns": task["max_turns"],
            "max_budget_usd": task["max_budget_usd"],
        },
        # Delivery contract fields for observability
        "planner_lineage": {
            "task_kind": task.get("task_kind", ""),
            "delivery_mode": "flat",
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


def write_review_cycle_task(task: dict[str, Any]) -> Path:
    """Write a review-cycle graph YAML to pending/.

    For code_change work. Calls launch_review_cycle.build_graph() as a library
    function and writes the resulting graph YAML with a deterministic id derived
    from the planner task id. The graph YAML carries planner_metadata so
    run_task.py can find the final review artifact and perform semantic gating.
    """
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    task_id = _make_planner_task_id(task)
    cycle_id = re.sub(r"[^a-zA-Z0-9_-]", "_", task_id)

    # Import build_graph as a library function
    repo_root = Path(__file__).resolve().parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from launch_review_cycle import build_graph, _load_config  # type: ignore[import]

    config = _load_config(None)
    review_rounds = task.get("review_rounds") or 1
    project_path = Path(task["project"]).expanduser().resolve()

    graph = build_graph(
        cycle_id=cycle_id,
        project_path=project_path,
        objective=task["objective"],
        rounds=review_rounds,
        config=config,
    )

    # Inject planner metadata so run_task.py can gate on review result
    ws_dir = Path(str(config["workspace_dir"]).replace("~", str(Path.home()))).resolve()
    final_review_json = str(ws_dir / cycle_id / f"round_{review_rounds}" / "review.json")
    graph["planner_metadata"] = {
        "planner_task_id": task_id,
        "task_kind": task.get("task_kind", "code_change"),
        "delivery_mode": "review_cycle",
        "review_rounds": review_rounds,
        "file_scope": task.get("file_scope", []),
        "final_review_json": final_review_json,
        "target_repo": str(project_path),
        "created": datetime.now(timezone.utc).isoformat(),
    }

    try:
        import yaml
        graph_yaml = yaml.dump(graph, default_flow_style=False, sort_keys=False)
    except ImportError:
        graph_yaml = json.dumps(graph, indent=2)

    dest = PENDING_DIR / f"{cycle_id}.yaml"
    dest.write_text(graph_yaml)
    return dest


def write_task_file(task: dict[str, Any]) -> Path:
    """Write a task dict to pending/, routing to the correct path based on delivery_mode.

    Routes code_change tasks to write_review_cycle_task() and all other
    work to write_flat_task(). Falls back to flat if delivery_mode is missing
    (backward compatibility with pre-Plan-#2 task dicts).
    """
    delivery_mode = task.get("delivery_mode", "flat")
    if delivery_mode == "review_cycle":
        return write_review_cycle_task(task)
    return write_flat_task(task)


def audit_queue() -> None:
    """Classify pending queue tasks by delivery-mode readiness.

    Reads all pending tasks and categorizes them:
    - review_cycle_ready: has planner_metadata.delivery_mode=review_cycle
    - flat_legacy: has planner_lineage.delivery_mode=flat OR is a pre-Plan-#2 flat .md
    - stale: YAML frontmatter created > 48h ago
    - broken: cannot parse frontmatter

    Does NOT rewrite any tasks. For operator review only.
    """
    import time

    now = time.time()
    categories: dict[str, list[str]] = {
        "review_cycle_ready": [],
        "flat_legacy": [],
        "stale": [],
        "broken": [],
    }

    for task_file in sorted(PENDING_DIR.glob("*")):
        if task_file.suffix not in {".md", ".yaml", ".yml"}:
            continue
        try:
            content = task_file.read_text()
            # Try YAML frontmatter (--- ... --- for .md, or top-level dict for .yaml)
            try:
                import yaml
                if task_file.suffix == ".md":
                    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                    if fm_match:
                        fm = yaml.safe_load(fm_match.group(1))
                    else:
                        fm = {}
                else:
                    fm = yaml.safe_load(content) or {}
            except Exception:
                categories["broken"].append(task_file.name)
                continue

            # Check staleness
            created_str = fm.get("created") or (fm.get("graph", {}) or {}).get("created", "")
            planner_meta = fm.get("planner_metadata") or {}
            if not created_str:
                created_str = planner_meta.get("created", "")
            if created_str:
                try:
                    from datetime import datetime, timezone
                    created_dt = datetime.fromisoformat(created_str)
                    age_h = (now - created_dt.timestamp()) / 3600
                    if age_h > 48:
                        categories["stale"].append(f"{task_file.name} (age={age_h:.0f}h)")
                        continue
                except Exception:
                    pass

            # Classify
            if planner_meta.get("delivery_mode") == "review_cycle":
                categories["review_cycle_ready"].append(task_file.name)
            else:
                categories["flat_legacy"].append(task_file.name)

        except Exception as e:
            categories["broken"].append(f"{task_file.name} ({e})")

    print("=== Pending Queue Audit ===")
    for cat, items in categories.items():
        print(f"\n{cat} ({len(items)}):")
        for item in items:
            print(f"  {item}")
    total = sum(len(v) for v in categories.values())
    print(f"\nTotal: {total}")


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
    parser.add_argument(
        "--audit-queue",
        action="store_true",
        help="Audit pending queue and classify tasks by delivery-mode readiness (read-only).",
    )
    args = parser.parse_args()

    if args.audit_queue:
        audit_queue()
        return

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
