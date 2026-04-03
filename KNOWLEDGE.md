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
