# Moltbot / OpenClaw

This repo is the **canonical home** of the OpenClaw runtime: task runner,
task planner, review cycle launcher, and supporting assets.

Runtime code was imported from `project-meta/ops/openclaw/` on 2026-04-01
to make project-meta documentation-focused.

## Key Files

- `run_task.py` — Queue runner with `--loop` supervisor mode
- `task_planner.py` — Goal-aware task generator
- `launch_review_cycle.py` — Review cycle DAG launcher
- `launch_llm_review_cycle.py` — OpenClaw wrapper for `llm_client review-cycle`
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

## Principles

- OpenClaw is an orchestration layer, not the home of repo-local governance
- Runtime behavior changes require test and README updates in the same commit
- `$HOME/.openclaw` paths are symlinks here — this repo is canonical
- Fail loud on runtime errors; the queue runner should surface issues, not hide them

## Workflow

1. Verify runtime symlink is current: `bash verify_runtime_runner.sh`
2. Check queue: inspect `~/.openclaw/tasks/pending/`
3. Run loop: `python run_task.py --loop`
4. Generate new tasks: `python task_planner.py --goal "..."`

## References

- `run_task.py` — Queue runner entry point
- `task_planner.py` — Goal-aware task generation
- `launch_review_cycle.py` — Review cycle DAG launcher
- `prompts/task_planner.yaml` — Task planner system/user prompts
- `review_cycle.defaults.yaml` — Conservative defaults for review cycles

## Execution Mandates

- **Worktree-only execution is mandatory between merges and pushes.**
  For any non-trivial runtime change, planning slice, proof run, or debugging
  session, use a dedicated branch worktree. Do not continue implementation on a
  primary checkout "just for one quick fix." If the work is worth keeping, it
  is worth isolating in a worktree first.
- **Commit verified increments immediately and often.**
  Every completed phase or sub-phase with passing verification must be committed
  before moving on. Small, frequent commits are mandatory so the runtime can be
  reverted to the last known-good state without reconstructing work from
  conversation history.
- **When the user authorizes continuous execution, treat the active plan as
  standing authorization to continue phase-to-phase without pausing.**
  Do not stop at a green test, a completed subtask, or a single landed commit.
  Continue until all active plan acceptance criteria are met or a real blocker
  is reached.
- **A blocker or uncertainty must be written down immediately and precisely.**
  Record it in the active execution tracker, implementation plan, or
  `KNOWLEDGE.md` before changing direction.
- **Never merge on vague confidence.**
  Before any merge into mainline, the active tracker must name the exact tests,
  proof report, and residual risks that justify the merge.
