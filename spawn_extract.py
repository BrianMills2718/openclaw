"""Extract spawned tasks and escalated decisions from agent output.

Agents running in the OpenClaw task system can embed structured markers in
their responses to request follow-up work or flag uncertain decisions.
This module parses those markers and writes them to the appropriate queues.

Markers are HTML comments containing YAML bodies:

    <!-- SPAWN_TASK
    id: fix-retry-tests
    priority: medium
    ...
    -->

    <!-- ESCALATE
    project: llm_client
    confidence: 0.4
    ...
    -->

The orchestrator (run_task.py) calls extract functions after each agent run,
then writes results to pending/ and decisions/ respectively. Parse failures
are logged loudly but never raise — extraction must not break the task lifecycle.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("spawn_extract")

MAX_SPAWNED_TASKS = 3

# Regex: match <!-- SPAWN_TASK ... --> or <!-- ESCALATE ... -->
# Uses DOTALL so the body can span multiple lines.
_SPAWN_RE = re.compile(r"<!--\s*SPAWN_TASK\s*\n(.*?)-->", re.DOTALL)
_ESCALATE_RE = re.compile(r"<!--\s*ESCALATE\s*\n(.*?)-->", re.DOTALL)

_SPAWN_REQUIRED = {"id", "priority", "project", "agent", "title", "objective"}
_ESCALATE_REQUIRED = {"project", "confidence", "category", "decision"}


@dataclass
class SpawnedTask:
    """A follow-up task extracted from agent output."""

    id: str
    priority: str
    project: str
    agent: str
    title: str
    objective: str
    max_turns: int = 30
    max_budget_usd: float = 2.0
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class EscalatedDecision:
    """An uncertainty escalation extracted from agent output."""

    project: str
    confidence: float
    category: str
    decision: str
    alternatives: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)


def extract_spawned_tasks(text: str) -> list[SpawnedTask]:
    """Parse all SPAWN_TASK markers from agent output text.

    Returns at most MAX_SPAWNED_TASKS tasks. Malformed markers are logged
    and skipped — never raises.
    """
    matches = _SPAWN_RE.findall(text)
    if not matches:
        return []

    if len(matches) > MAX_SPAWNED_TASKS:
        log.warning(
            "Agent produced %d SPAWN_TASK markers but max is %d — truncating",
            len(matches),
            MAX_SPAWNED_TASKS,
        )
        matches = matches[:MAX_SPAWNED_TASKS]

    tasks: list[SpawnedTask] = []
    for i, body in enumerate(matches):
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            log.error("SPAWN_TASK #%d: YAML parse error: %s", i, exc)
            continue

        if not isinstance(data, dict):
            log.error("SPAWN_TASK #%d: expected mapping, got %s", i, type(data).__name__)
            continue

        missing = _SPAWN_REQUIRED - set(data.keys())
        if missing:
            log.error("SPAWN_TASK #%d: missing required fields: %s", i, missing)
            continue

        criteria_raw = data.get("acceptance_criteria", [])
        if isinstance(criteria_raw, str):
            criteria_raw = [criteria_raw]

        tasks.append(SpawnedTask(
            id=str(data["id"]),
            priority=str(data["priority"]),
            project=str(data["project"]),
            agent=str(data["agent"]),
            title=str(data["title"]),
            objective=str(data["objective"]),
            max_turns=int(data.get("max_turns", 30)),
            max_budget_usd=float(data.get("max_budget_usd", 2.0)),
            acceptance_criteria=[str(c) for c in criteria_raw],
        ))

    return tasks


def extract_escalations(text: str) -> list[EscalatedDecision]:
    """Parse all ESCALATE markers from agent output text.

    Malformed markers are logged and skipped — never raises.
    """
    matches = _ESCALATE_RE.findall(text)
    if not matches:
        return []

    escalations: list[EscalatedDecision] = []
    for i, body in enumerate(matches):
        try:
            data = yaml.safe_load(body)
        except yaml.YAMLError as exc:
            log.error("ESCALATE #%d: YAML parse error: %s", i, exc)
            continue

        if not isinstance(data, dict):
            log.error("ESCALATE #%d: expected mapping, got %s", i, type(data).__name__)
            continue

        missing = _ESCALATE_REQUIRED - set(data.keys())
        if missing:
            log.error("ESCALATE #%d: missing required fields: %s", i, missing)
            continue

        alts = data.get("alternatives", [])
        if isinstance(alts, str):
            alts = [alts]
        tradeoffs = data.get("tradeoffs", [])
        if isinstance(tradeoffs, str):
            tradeoffs = [tradeoffs]

        escalations.append(EscalatedDecision(
            project=str(data["project"]),
            confidence=float(data["confidence"]),
            category=str(data["category"]),
            decision=str(data["decision"]),
            alternatives=[str(a) for a in alts],
            tradeoffs=[str(t) for t in tradeoffs],
        ))

    return escalations


def write_spawned_task(
    task: SpawnedTask,
    pending_dir: Path,
    *,
    spawned_by: str = "agent",
) -> Path:
    """Write a SpawnedTask as a flat .md file matching TaskSpec format.

    Creates the pending_dir if it doesn't exist. The filename includes the
    date and 'spawned' prefix so it's visually distinct from planner tasks.

    Returns the path to the written file.
    """
    pending_dir.mkdir(parents=True, exist_ok=True)

    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{date_prefix}-spawned-{task.id}.md"

    criteria_lines = "\n".join(f"- [ ] {c}" for c in task.acceptance_criteria)

    frontmatter: dict[str, Any] = {
        "id": f"{date_prefix}-spawned-{task.id}",
        "priority": task.priority,
        "agent": task.agent,
        "project": task.project,
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
        "spawned_by": spawned_by,
        "constraints": {
            "max_turns": task.max_turns,
            "max_budget_usd": task.max_budget_usd,
            "mcp_servers": [],
        },
    }

    body_parts = [
        f"# {task.title}",
        "",
        "## Objective",
        "",
        task.objective,
        "",
        "## Acceptance Criteria",
        "",
        criteria_lines or "- [ ] Task completed successfully",
        "",
        "## Context",
        "",
        f"Spawned by {spawned_by} during task execution.",
    ]

    content = "---\n" + yaml.dump(frontmatter, default_flow_style=False, sort_keys=False) + "---\n\n" + "\n".join(body_parts) + "\n"
    dest = pending_dir / filename
    dest.write_text(content)
    log.info("Wrote spawned task: %s", dest)
    return dest


def write_escalation(
    escalation: EscalatedDecision,
    task_id: str,
    decisions_dir: Path,
) -> Path:
    """Write an EscalatedDecision as a YAML file matching decision_log.py schema.

    Sets review_status=pending and source=agent_escalation so the escalation
    inbox picks it up. Creates the decisions_dir if it doesn't exist.

    Returns the path to the written file.
    """
    decisions_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    ts_slug = ts.strftime("%Y-%m-%dT%H-%M-%S-%f")
    decision_id = f"{ts_slug}_{escalation.project}_{escalation.category}"

    record: dict[str, Any] = {
        "id": decision_id,
        "timestamp": ts.isoformat(),
        "project": escalation.project,
        "task_id": task_id,
        "category": escalation.category,
        "confidence": escalation.confidence,
        "decision": escalation.decision,
        "alternatives": [
            {"option": alt, "chosen": False, "rationale": ""}
            for alt in escalation.alternatives
        ],
        "tradeoffs": escalation.tradeoffs,
        "goal_advanced": "",
        "review_status": "pending",
        "source": "agent_escalation",
        "correction": None,
    }

    dest = decisions_dir / f"{decision_id}.yaml"
    dest.write_text(yaml.dump(record, default_flow_style=False, sort_keys=False))
    log.info("Wrote escalation: %s", dest)
    return dest
