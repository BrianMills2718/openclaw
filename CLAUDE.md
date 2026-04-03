# Moltbot / OpenClaw

This repo is the **canonical home** of the OpenClaw runtime: task runner,
task planner, review cycle launcher, and supporting assets.

Runtime code was imported from `project-meta/ops/openclaw/` on 2026-04-01
to make project-meta documentation-focused.

## Key Files

- `run_task.py` — Queue runner with `--loop` supervisor mode
- `task_planner.py` — Goal-aware task generator
- `launch_review_cycle.py` — Review cycle DAG launcher
- `prompts/task_planner.yaml` — System/user prompts for task generation
- `schemas/` — JSON schemas for task reports
- `review_cycle.defaults.yaml` — Conservative defaults

## Runtime Sync

The runtime path `$HOME/.openclaw/bin/run_task.py` should be a symlink
to this repo's `run_task.py`. Install/verify:
```bash
bash install_runtime_runner.sh
bash verify_runtime_runner.sh
```

`run_task.py` and `task_planner.py` bootstrap shared repo roots from
`${PROJECTS_ROOT:-$HOME/projects}` so `llm_client` resolves through its public
facade during local-first runs. `verify_runtime_runner.sh` must pass before
claiming the runtime path is usable on the current host.

## Working Rules

- OpenClaw is an orchestration layer, not the home of repo-local governance
- When runtime behavior changes, update tests and README in the same change
- This repo is canonical; `$HOME/.openclaw` paths are symlinks to here
