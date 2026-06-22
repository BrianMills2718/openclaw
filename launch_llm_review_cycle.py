#!/usr/bin/env python3
"""Create an OpenClaw wrapper task for `llm_client review-cycle`.

This adapter intentionally does not reimplement review semantics. It writes a
minimal graph artifact whose `delivery_mode` tells `run_task.py` to invoke
`python -m llm_client review-cycle --task-file ...` and link the resulting
llm_client artifact sidecar from the OpenClaw report.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _load_review_cycle_task(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("ReviewCycleTask file must contain a JSON object")
    for key in ("task_id", "workspace_path"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"ReviewCycleTask file missing required string field: {key}")
    return payload


def _default_artifacts_path(task_payload: dict[str, Any]) -> Path:
    raw_out_dir = task_payload.get("out_dir")
    if isinstance(raw_out_dir, str) and raw_out_dir.strip():
        return Path(raw_out_dir).expanduser() / "review_cycle_artifacts.json"
    workspace = Path(str(task_payload["workspace_path"])).expanduser()
    return workspace / "runs" / "review-cycle" / str(task_payload["task_id"]) / "review_cycle_artifacts.json"


def build_graph(
    *,
    cycle_id: str,
    review_cycle_task_file: Path,
    target_repo_path: Path | None = None,
    artifacts_path: Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal OpenClaw graph wrapper for one llm_client review cycle."""

    task_payload = _load_review_cycle_task(review_cycle_task_file)
    target_repo = target_repo_path or Path(str(task_payload["workspace_path"])).expanduser()
    sidecar_path = artifacts_path or _default_artifacts_path(task_payload)
    graph: dict[str, Any] = {
        "graph": {
            "id": cycle_id,
            "description": f"llm_client review-cycle adapter for {target_repo.name}",
            "timeout_minutes": 240,
            "checkpoint": "none",
        },
        "tasks": {},
        "metadata": {
            "delivery_mode": "llm_review_cycle",
            "task_kind": "review_cycle",
            "target_repo_path": str(target_repo.resolve()),
            "review_cycle_task_file": str(review_cycle_task_file.resolve()),
            "review_cycle_artifacts_path": str(sidecar_path.expanduser()),
        },
    }
    if metadata:
        graph["metadata"].update(metadata)
    return graph


def main() -> None:
    """CLI entry point for creating llm_client review-cycle wrapper graphs."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-file", required=True, help="Path to llm_client ReviewCycleTask JSON.")
    parser.add_argument("--cycle-id", default="", help="Graph id; default generated from task id and UTC time.")
    parser.add_argument("--queue-dir", default="~/.openclaw/tasks/pending", help="OpenClaw pending queue directory.")
    parser.add_argument("--target-repo", default="", help="Override target repo path; defaults to task.workspace_path.")
    parser.add_argument("--artifacts-path", default="", help="Override OpenClaw review-cycle sidecar path.")
    parser.add_argument("--print-only", action="store_true", help="Print graph YAML instead of queueing it.")
    args = parser.parse_args()

    task_file = Path(args.task_file).expanduser().resolve()
    task_payload = _load_review_cycle_task(task_file)
    if args.cycle_id:
        cycle_id = args.cycle_id
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        cycle_id = f"llm_review_cycle_{task_payload['task_id']}_{stamp}"
    graph = build_graph(
        cycle_id=cycle_id,
        review_cycle_task_file=task_file,
        target_repo_path=Path(args.target_repo).expanduser().resolve() if args.target_repo else None,
        artifacts_path=Path(args.artifacts_path).expanduser() if args.artifacts_path else None,
    )
    content = yaml.safe_dump(graph, sort_keys=False)
    if args.print_only:
        print(content)
        return

    queue_dir = Path(args.queue_dir).expanduser().resolve()
    queue_dir.mkdir(parents=True, exist_ok=True)
    out_path = queue_dir / f"{cycle_id}.yaml"
    if out_path.exists():
        raise FileExistsError(out_path)
    out_path.write_text(content, encoding="utf-8")
    print(f"enqueued: {out_path}")
    print(f"cycle_id: {cycle_id}")


if __name__ == "__main__":
    main()
