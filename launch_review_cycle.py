#!/usr/bin/env python3
"""Generate and enqueue an implementation-review task graph.

The graph alternates implementation/review rounds and can optionally maintain
an auto-updated rolling context pack:
  context_init -> implement_r1 -> review_r1 -> context_update_r1 -> ...
  -> synthesize

This is a queue producer only. Execution is handled by run_task.py --loop.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).with_name("review_cycle.defaults.yaml")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_config(path: Path | None) -> dict[str, Any]:
    base = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text())
    if not isinstance(base, dict):
        raise ValueError(f"Invalid default config: {DEFAULT_CONFIG_PATH}")
    if path is None:
        return base
    user = yaml.safe_load(path.read_text())
    if not isinstance(user, dict):
        raise ValueError(f"Invalid user config: {path}")
    return _deep_merge(base, user)


def _json_review_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["status", "summary", "critical_issues", "next_objective"],
        "properties": {
            "status": {"type": "string", "enum": ["pass", "needs_changes"]},
            "summary": {"type": "string"},
            "critical_issues": {"type": "array", "items": {"type": "string"}},
            "next_objective": {"type": "string"},
            "recommended_tests": {"type": "array", "items": {"type": "string"}},
        },
    }


def _resolve_model_for_agent(agent: str, configured_model: Any, fallback_model: str) -> str:
    """Resolve an explicit model value for generated graph tasks."""

    if isinstance(configured_model, str) and configured_model.strip():
        return configured_model.strip()
    if agent == "direct":
        return fallback_model
    if agent in {"codex", "claude-code", "claude"}:
        return "claude-code" if agent == "claude" else agent
    return fallback_model


def _impl_prompt(
    *,
    project_path: Path,
    objective: str,
    round_num: int,
    review_ref: str | None,
    context_ref: str | None,
    impl_note_path: Path,
) -> str:
    lines = [
        f"Round {round_num} implementation task.",
        f"Project: {project_path}",
        "",
        "Primary objective:",
        objective,
        "",
    ]
    if context_ref:
        lines.extend([
            "Read the rolling context pack first and use it as the authoritative cycle state:",
            context_ref,
            "",
        ])
    if review_ref:
        lines.extend([
            "Use the previous review JSON as mandatory input:",
            review_ref,
            "",
            "If previous status is 'pass', do not make unnecessary edits.",
            "If previous status is 'needs_changes', address all critical issues first.",
            "",
        ])
    lines.extend([
        "Execution requirements:",
        "1. Implement the required changes in the repo.",
        "2. Run relevant tests for changed code paths.",
        "3. Write a concise implementation note file at the required path.",
        "4. Include: changed files, tests run, residual risks.",
        "",
        f"Write implementation note to: {impl_note_path}",
    ])
    return "\n".join(lines)


def _review_prompt(
    *,
    project_path: Path,
    round_num: int,
    impl_ref: str,
    context_ref: str | None,
    review_path: Path,
) -> str:
    lines = [
        f"Round {round_num} review task.",
        f"Project: {project_path}",
        "",
    ]
    if context_ref:
        lines.extend([
            f"Read rolling context pack: {context_ref}",
            "",
        ])
    lines.extend([
        f"Read implementation note: {impl_ref}",
        "Perform a strict code-review style assessment focused on regressions, correctness, and missing tests.",
        "",
        "Write JSON output with this schema:",
        json.dumps(_json_review_schema(), indent=2),
        "",
        "Set status='pass' only when no blocking issues remain.",
        "Otherwise set status='needs_changes' and provide precise next_objective.",
        "",
        f"Write review JSON to: {review_path}",
    ])
    return "\n".join(lines)


def _synthesis_prompt(
    *,
    cycle_id: str,
    rounds: int,
    final_review_ref: str,
    context_ref: str | None,
    output_path: Path,
) -> str:
    lines = [
        f"Synthesize cycle results for {cycle_id}.",
        f"Total rounds: {rounds}",
        f"Read final review: {final_review_ref}",
        "",
    ]
    if context_ref:
        lines.extend([
            f"Also read rolling context pack: {context_ref}",
            "",
        ])
    lines.extend([
        "Write a final decision markdown with:",
        "1. Final status",
        "2. Blockers remaining (if any)",
        "3. Recommended next action",
        "",
        f"Output path: {output_path}",
    ])
    return "\n".join(lines)


def _context_init_prompt(
    *,
    cycle_id: str,
    project_path: Path,
    objective: str,
    context_path: Path,
) -> str:
    return "\n".join([
        f"Initialize rolling context pack for cycle: {cycle_id}",
        f"Project: {project_path}",
        "",
        "Create a concise markdown context pack that downstream tasks can reuse.",
        "Keep it factual and focused on execution context.",
        "",
        "Required sections:",
        "1. Objective",
        "2. Project Scope",
        "3. Baseline Assumptions",
        "4. Open Questions",
        "5. Next Round Focus",
        "",
        f"Write to: {context_path}",
    ])


def _context_update_prompt(
    *,
    round_num: int,
    project_path: Path,
    prior_context_ref: str,
    impl_ref: str,
    review_ref: str,
    context_path: Path,
) -> str:
    return "\n".join([
        f"Update rolling context pack after round {round_num}.",
        f"Project: {project_path}",
        "",
        f"Read previous context pack: {prior_context_ref}",
        f"Read implementation note: {impl_ref}",
        f"Read review JSON: {review_ref}",
        "",
        "Rewrite the context pack at the same path so it remains a single rolling file.",
        "Preserve prior context that is still valid and add a new section for this round.",
        "",
        "Required sections:",
        "1. Current Objective",
        "2. Completed Round Summaries",
        "3. Outstanding Issues",
        "4. Next Round Focus (must align with review next_objective)",
        "",
        f"Write updated context pack to: {context_path}",
    ])


def build_graph(
    *,
    cycle_id: str,
    project_path: Path,
    objective: str,
    rounds: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Build a YAML task graph for an implementation-review cycle."""
    ws_dir = Path(str(config["workspace_dir"]).replace("~", str(Path.home()))).resolve()
    cycle_dir = ws_dir / cycle_id

    graph: dict[str, Any] = {
        "graph": {
            "id": cycle_id,
            "description": f"Automated implementation-review cycle for {project_path.name}",
            "timeout_minutes": int(config["cycle"]["timeout_minutes"]),
            "checkpoint": config["cycle"]["checkpoint"],
        },
        "tasks": {},
    }

    impl_cfg = config["agents"]["implement"]
    review_cfg = config["agents"]["review"]
    context_cfg = config["agents"].get("context", impl_cfg)
    synth_cfg = config["agents"]["synthesis"]
    context_pack_cfg = config.get("context_pack", {}) or {}
    context_enabled = bool(context_pack_cfg.get("enabled", False))
    context_filename = str(context_pack_cfg.get("filename", "context_pack.md"))
    context_path = Path(context_filename)
    if not context_path.is_absolute():
        context_path = cycle_dir / context_path

    last_review_task = None
    last_context_task: str | None = None
    if context_enabled:
        context_task = "context_init"
        context_entry: dict[str, Any] = {
            "difficulty": int(context_cfg["difficulty"]),
            "agent": context_cfg.get("agent") or "direct",
            "prompt": _context_init_prompt(
                cycle_id=cycle_id,
                project_path=project_path,
                objective=objective,
                context_path=context_path,
            ),
            "working_directory": str(project_path),
            "validate": [{"type": "file_exists", "path": str(context_path)}],
            "outputs": {"context_pack": str(context_path)},
        }
        context_entry["model"] = _resolve_model_for_agent(
            context_entry["agent"],
            context_cfg.get("model"),
            fallback_model="codex",
        )
        if context_cfg.get("mcp_servers"):
            context_entry["mcp_servers"] = context_cfg["mcp_servers"]

        graph["tasks"][context_task] = context_entry
        last_context_task = context_task

    for i in range(1, rounds + 1):
        impl_task = f"implement_r{i}"
        review_task = f"review_r{i}"

        impl_note = cycle_dir / f"round_{i}" / "implementation.md"
        review_json = cycle_dir / f"round_{i}" / "review.json"

        review_ref = None
        impl_deps: list[str] = []
        context_ref = None
        if last_review_task is not None:
            review_ref = "{" + f"{last_review_task}.outputs.review_json" + "}"
        if context_enabled:
            if last_context_task is None:
                raise ValueError("context_pack.enabled requires an initialized context task")
            impl_deps = [last_context_task]
            context_ref = "{" + f"{last_context_task}.outputs.context_pack" + "}"
        elif last_review_task is not None:
            impl_deps = [last_review_task]

        impl_entry: dict[str, Any] = {
            "difficulty": int(impl_cfg["difficulty"]),
            "agent": impl_cfg.get("agent") or "direct",
            "prompt": _impl_prompt(
                project_path=project_path,
                objective=objective,
                round_num=i,
                review_ref=review_ref,
                context_ref=context_ref,
                impl_note_path=impl_note,
            ),
            "working_directory": str(project_path),
            "validate": [{"type": "file_exists", "path": str(impl_note)}],
            "outputs": {"impl_note": str(impl_note)},
        }
        impl_entry["model"] = _resolve_model_for_agent(
            impl_entry["agent"],
            impl_cfg.get("model"),
            fallback_model="codex",
        )
        if impl_deps:
            impl_entry["depends_on"] = impl_deps
        if impl_cfg.get("mcp_servers"):
            impl_entry["mcp_servers"] = impl_cfg["mcp_servers"]

        review_validate: list[dict[str, Any]] = [{"type": "file_exists", "path": str(review_json)}]
        if bool(config["validation"].get("require_json_review", True)):
            review_validate.append({
                "type": "json_schema",
                "path": str(review_json),
                "schema": _json_review_schema(),
            })

        review_entry: dict[str, Any] = {
            "difficulty": int(review_cfg["difficulty"]),
            "agent": review_cfg.get("agent") or "direct",
            "depends_on": [impl_task],
            "prompt": _review_prompt(
                project_path=project_path,
                round_num=i,
                impl_ref="{" + f"{impl_task}.outputs.impl_note" + "}",
                context_ref=context_ref,
                review_path=review_json,
            ),
            "working_directory": str(project_path),
            "validate": review_validate,
            "outputs": {"review_json": str(review_json)},
        }
        review_entry["model"] = _resolve_model_for_agent(
            review_entry["agent"],
            review_cfg.get("model"),
            fallback_model="claude-code",
        )
        if review_cfg.get("reasoning_effort"):
            review_entry["reasoning_effort"] = review_cfg["reasoning_effort"]
        if review_cfg.get("mcp_servers"):
            review_entry["mcp_servers"] = review_cfg["mcp_servers"]

        graph["tasks"][impl_task] = impl_entry
        graph["tasks"][review_task] = review_entry
        if context_enabled:
            context_update_task = f"context_update_r{i}"
            review_ref_current = "{" + f"{review_task}.outputs.review_json" + "}"
            impl_ref_current = "{" + f"{impl_task}.outputs.impl_note" + "}"
            prior_context_ref = context_ref or str(context_path)
            context_update_entry: dict[str, Any] = {
                "difficulty": int(context_cfg["difficulty"]),
                "agent": context_cfg.get("agent") or "direct",
                "depends_on": [review_task],
                "prompt": _context_update_prompt(
                    round_num=i,
                    project_path=project_path,
                    prior_context_ref=prior_context_ref,
                    impl_ref=impl_ref_current,
                    review_ref=review_ref_current,
                    context_path=context_path,
                ),
                "working_directory": str(project_path),
                "validate": [{"type": "file_exists", "path": str(context_path)}],
                "outputs": {"context_pack": str(context_path)},
            }
            context_update_entry["model"] = _resolve_model_for_agent(
                context_update_entry["agent"],
                context_cfg.get("model"),
                fallback_model="codex",
            )
            if context_cfg.get("mcp_servers"):
                context_update_entry["mcp_servers"] = context_cfg["mcp_servers"]
            graph["tasks"][context_update_task] = context_update_entry
            last_context_task = context_update_task

        last_review_task = review_task

    final_report = cycle_dir / "final_decision.md"
    synth_task = "synthesize"
    synth_entry: dict[str, Any] = {
        "difficulty": int(synth_cfg["difficulty"]),
        "agent": synth_cfg.get("agent") or "direct",
        "depends_on": (
            [last_context_task]
            if context_enabled and last_context_task
            else ([last_review_task] if last_review_task else [])
        ),
        "prompt": _synthesis_prompt(
            cycle_id=cycle_id,
            rounds=rounds,
            final_review_ref="{" + f"{last_review_task}.outputs.review_json" + "}",
            context_ref=(
                "{" + f"{last_context_task}.outputs.context_pack" + "}"
                if context_enabled and last_context_task
                else None
            ),
            output_path=final_report,
        ),
        "working_directory": str(project_path),
        "validate": [{"type": "file_exists", "path": str(final_report)}],
        "outputs": {"final_report": str(final_report)},
    }
    synth_entry["model"] = _resolve_model_for_agent(
        synth_entry["agent"],
        synth_cfg.get("model"),
        fallback_model="codex",
    )
    if synth_cfg.get("mcp_servers"):
        synth_entry["mcp_servers"] = synth_cfg["mcp_servers"]

    graph["tasks"][synth_task] = synth_entry
    return graph


def main() -> None:
    """CLI entry point for creating and enqueuing review cycle graphs."""
    parser = argparse.ArgumentParser(description="Create and enqueue an implementation-review cycle graph")
    parser.add_argument("--project", required=True, help="Target project path")
    parser.add_argument("--objective", required=True, help="Implementation objective")
    parser.add_argument("--cycle-id", default=None, help="Graph id; default auto-generated")
    parser.add_argument("--rounds", type=int, default=None, help="Number of impl/review rounds")
    parser.add_argument("--config", type=str, default=None, help="Override config YAML path")
    parser.add_argument("--print-only", action="store_true", help="Print graph YAML instead of writing to queue")
    parser.add_argument("--run-now", action="store_true", help="After enqueue, execute the graph immediately")
    parser.add_argument(
        "--runner",
        default="~/.openclaw/bin/run_task.py",
        help="Path to run_task.py used with --run-now",
    )
    parser.add_argument(
        "--parent-trace-id",
        default=None,
        help="Optional parent trace id for hierarchical observability",
    )
    args = parser.parse_args()

    cfg = _load_config(Path(args.config).expanduser().resolve() if args.config else None)
    max_rounds = int(cfg["cycle"].get("max_rounds", 8))
    rounds = int(args.rounds if args.rounds is not None else cfg["cycle"]["rounds"])
    if rounds < 1 or rounds > max_rounds:
        raise ValueError(f"rounds must be between 1 and {max_rounds}")

    project_path = Path(args.project).expanduser().resolve()
    if not project_path.exists():
        raise FileNotFoundError(project_path)

    if args.cycle_id:
        cycle_id = args.cycle_id
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        cycle_id = f"impl_review_{project_path.name}_{stamp}"

    graph = build_graph(
        cycle_id=cycle_id,
        project_path=project_path,
        objective=args.objective,
        rounds=rounds,
        config=cfg,
    )

    content = yaml.safe_dump(graph, sort_keys=False)
    if args.print_only:
        print(content)
        return

    queue_dir = Path(str(cfg["queue_dir"]).replace("~", str(Path.home()))).resolve()
    queue_dir.mkdir(parents=True, exist_ok=True)
    out_path = queue_dir / f"{cycle_id}.yaml"
    if out_path.exists():
        raise FileExistsError(out_path)
    out_path.write_text(content)

    print(f"enqueued: {out_path}")
    print(f"cycle_id: {cycle_id}")
    print(f"rounds: {rounds}")

    if args.run_now:
        runner = Path(args.runner).expanduser().resolve()
        if not runner.exists():
            raise FileNotFoundError(runner)
        parent_trace = args.parent_trace_id or f"openclaw.review_cycle.{cycle_id}"
        cmd = [
            "python3",
            str(runner),
            str(out_path),
            "--parent-trace-id",
            parent_trace,
        ]
        print("run_now:", " ".join(cmd))
        subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
