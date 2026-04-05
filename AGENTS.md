# Moltbot / OpenClaw

<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- generated_by: scripts/meta/render_agents_md.py -->
<!-- canonical_claude: CLAUDE.md -->
<!-- canonical_relationships: scripts/relationships.yaml -->
<!-- canonical_relationships_sha256: 840b164dcfa4 -->
<!-- sync_check: python scripts/meta/check_agents_sync.py --check -->

This file is a generated Codex-oriented projection of repo governance.
Edit the canonical sources instead of editing this file directly.

Canonical governance sources:
- `CLAUDE.md` — human-readable project rules, workflow, and references
- `scripts/relationships.yaml` — machine-readable ADR, coupling, and required-reading graph

## Purpose

This repo is the **canonical home** of the OpenClaw runtime: task runner,
task planner, review cycle launcher, and supporting assets.

Runtime code was imported from `project-meta/ops/openclaw/` on 2026-04-01
to make project-meta documentation-focused.

## Commands

```bash
# Install/verify runtime runner
bash install_runtime_runner.sh
bash verify_runtime_runner.sh

# Run OpenClaw task loop
python run_task.py --loop

# Generate tasks for a goal
python task_planner.py --goal "Goal description"

# Launch review cycle
python launch_review_cycle.py
```

## Operating Rules

This projection keeps the highest-signal rules in always-on Codex context.
For full project structure, detailed terminology, and any rule omitted here,
read `CLAUDE.md` directly.

### Principles

- OpenClaw is an orchestration layer, not the home of repo-local governance
- Runtime behavior changes require test and README updates in the same commit
- `$HOME/.openclaw` paths are symlinks here — this repo is canonical
- Fail loud on runtime errors; the queue runner should surface issues, not hide them

### Workflow

1. Verify runtime symlink is current: `bash verify_runtime_runner.sh`
2. Check queue: inspect `~/.openclaw/tasks/pending/`
3. Run loop: `python run_task.py --loop`
4. Generate new tasks: `python task_planner.py --goal "..."`

## Machine-Readable Governance

`scripts/relationships.yaml` is the source of truth for machine-readable governance in this repo: ADR coupling, required-reading edges, and doc-code linkage. This generated file does not inline that graph; it records the canonical path and sync marker, then points operators and validators back to the source graph. Prefer deterministic validators over prompt-only memory when those scripts are available.

## References

- `run_task.py` — Queue runner entry point
- `task_planner.py` — Goal-aware task generation
- `launch_review_cycle.py` — Review cycle DAG launcher
- `prompts/task_planner.yaml` — Task planner system/user prompts
- `review_cycle.defaults.yaml` — Conservative defaults for review cycles
