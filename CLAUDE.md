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

## Execution Mandates

- **Worktree-only execution is mandatory between merges and pushes.**
  For any non-trivial runtime change, planning slice, proof run, or debugging
  session, use a dedicated branch worktree. Do not continue implementation on a
  primary checkout "just for one quick fix." If the work is worth keeping, it
  is worth isolating in a worktree first.
- **Always use a dedicated git worktree for non-trivial implementation work.**
  Do not make runtime changes directly on the primary checkout between merges
  and pushes. Create a named branch worktree first, do the work there, and
  keep the main checkout clean enough to remain a reliable integration point.
- **Commit verified increments immediately and often.**
  Every completed phase or sub-phase with passing verification must be committed
  before moving on. Small, frequent commits are mandatory so the runtime can be
  reverted to the last known-good state without reconstructing work from
  conversation history. If a proof run reveals a real fixed sub-problem, commit
  that sub-problem before chasing the next one.
- **When the user authorizes continuous execution, treat the active plan as
  standing authorization to continue phase-to-phase without pausing.**
  Do not stop at a green test, a completed subtask, or a single landed commit.
  Continue until all active plan acceptance criteria are met or a real blocker
  is reached. Overnight execution should continue phase-by-phase without
  requesting confirmation for ordinary implementation choices already settled in
  the active plan.
- **A blocker or uncertainty must be written down immediately and precisely.**
  Record it in the active execution tracker, implementation plan, or
  `KNOWLEDGE.md` before changing direction. Never keep operational uncertainty
  only in chat context, and never let a discovered blocker remain implicit.
- **Never end a long-running session with ambiguous state.**
  Leave either a commit that captures the verified increment or a precise note
  explaining what remains unverified and why execution could not safely
  continue.
- **Do not stop just because one proof run failed.**
  If a run fails, extract the exact failure signature, write it down, fix the
  highest-leverage root cause in the current worktree, commit when verified, and
  continue to the next phase. The only valid stop is a documented blocker or
  completed acceptance criteria.
