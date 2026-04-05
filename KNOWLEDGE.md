# Operational Knowledge — moltbot

Shared findings from all agent sessions. Any agent brain can read and append.
Human-reviewed periodically.

## Findings

<!-- Append new findings below this line. Do not overwrite existing entries. -->
<!-- Format: ### YYYY-MM-DD — {agent} — {category}                          -->
<!-- Categories: bug-pattern, performance, schema-gotcha, integration-issue, -->
<!--             workaround, best-practice                                   -->
<!-- Agent names: claude-code, codex, openclaw                               -->

### 2026-04-02 — codex — integration-issue

`run_task.py` and `task_planner.py` cannot rely on the shared runtime
interpreter exposing the `llm_client` public facade correctly through the
editable install alone. In the shared `~/projects/.venv`, `import llm_client`
can resolve to the repo-root namespace instead of the inner package facade,
which breaks `from llm_client import acall_llm`. The current local-first fix is:

- prepend `${PROJECTS_ROOT:-$HOME/projects}/llm_client` before root imports
- verify the runtime environment with `bash verify_runtime_runner.sh`
- ensure the runtime interpreter has `llm_client[agents]` installed so
  `claude_agent_sdk` is importable

This gets `moltbot` past the runner/bootstrap seam and back to the governed
proof-task behavior instead of failing at import time.

### 2026-04-03 — codex — bug-pattern

The Claude agent runtime can leave a false-negative `LLMError` after a bounded
task has already completed successfully.

Measured pattern:
- proof worktree landed a real commit
- post-task validation passed
- the Claude SDK path still surfaced
  `Command failed with exit code 1 ... Check stderr output for details`

`run_task.py` now treats only that narrow generic post-success error family as
recoverable, and only when either:

- commit detection plus post-validation support success, or
- meaningful bounded source-file changes (excluding `.claude/hook_log.jsonl`)
  plus post-validation support success

Keep the rule narrow; do not widen it to arbitrary runtime exceptions.

### 2026-04-04 — codex — workaround

`run_task.py` currently bootstraps `scripts.meta.*` imports by prepending
`Path(__file__).resolve().parent.parent.parent` to `sys.path`. That means
`moltbot` worktrees must live under `~/projects/...` if they need the shared
`project-meta/scripts/meta` modules to resolve correctly during runtime
execution. A worktree under `/home/brian/worktrees/...` breaks that assumption.

Until the bootstrap logic is made path-agnostic, keep `moltbot` worktrees under
`~/projects/` when executing the runtime from a worktree.
