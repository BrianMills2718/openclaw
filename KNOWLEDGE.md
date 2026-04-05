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

### 2026-04-04 — codex — bug-pattern

In `review_cycle.defaults.yaml`, any task that must write repo or workspace
files cannot pin a plain text model like `gemini/gemini-2.5-flash` while also
declaring `agent: codex`. The task-graph runner decides whether to use a
workspace agent from the resolved model family, not the `agent` label alone.

Measured failure:
- `context_init` resolved to `gemini/gemini-2.5-flash`
- task executed as a plain LLM call instead of a workspace agent
- file validator failed because no file was ever written

For file-writing review-cycle lanes, keep the resolved model agent-capable
(`codex`, `claude-code`, or another workspace-agent family).

### 2026-04-04 — codex — integration-issue

Workspace-agent review-cycle tasks cannot reliably write artifacts outside the
 target repo boundary. A cycle workspace rooted at `~/.openclaw/workspace/...`
 caused `context_init` to fail even after the model/agent mismatch was fixed,
 because the agent never produced the required file.

The current safe default is a repo-local workspace root:
- `workspace_dir: .openclaw/review-cycles`
- relative workspace roots resolve under the target `project_path`

That keeps context packs, implementation notes, review JSON, and synthesis
artifacts inside the repo tree the workspace agent can actually mutate.

### 2026-04-04 — codex — workaround

The task-graph runner can still report a workspace-agent task as failed after
the task already produced its declared outputs. This showed up in the
review-cycle proof when `context_init` wrote `context_pack.md` but the graph
stopped with `status=partial`.

Current local fix in `moltbot/scripts/meta/task_graph.py`:
- delegate to the canonical `project-meta` task-graph implementation
- re-run declared validators on a failed task result
- if validators now pass, recover that task to `COMPLETED` and continue

Keep this recovery narrow and validator-backed. Do not use it to mask tasks
whose declared outputs still fail validation.

### 2026-04-04 — codex — best-practice

If `moltbot` needs to locally own `scripts.meta.*` shims, `scripts/` and
`scripts/meta/` must be explicit local Python packages. Without local
`__init__.py` files, Python can keep resolving `scripts.meta.task_graph` to the
external `project-meta` namespace package, which makes local shims appear to be
ignored even when the files exist.

### 2026-04-04 — codex — integration-issue

The remaining review-cycle proof failure is not in `moltbot` orchestration. It
is in the Codex SDK text-execution path used by file-writing tasks.

Measured repro:
- a trivial direct `acall_llm("codex", ...)` call succeeds
- replaying the exact `implement_r1` prompt from the planner-generated review
  graph fails inside `openai_codex_sdk`
- concrete exception:
  `ValidationError: FileChangeItem.status Input should be 'completed' or 'failed'; input was 'in_progress'`

Operational consequence:
- the graph records `model_selected="codex"` but no `resolved_model`,
  `routing_trace`, or validator output
- `implement_r1` fails before llm_client can finalize a normal agent result

Treat this as an llm_client/Codex transport compatibility issue. The next fix
should be a durable fallback or transport-selection change, not another
orchestration-layer workaround in `moltbot`.

### 2026-04-04 — codex — bug-pattern

Planner-generated review-cycle graphs can still be deterministically wrong even
when the planner emits the correct `delivery_mode`.

Measured failure:
- planner was explicitly scoped to one target worktree
- generated graph still used a hallucinated nested repo path ending in
  `/openclaw`
- the readiness audit originally passed because graph preflight did not verify
  task `working_directory` paths

Current safe rule:
- when planning is explicitly scoped to one target repo, normalize generated
  task `project` paths to that exact repo root
- graph preflight must fail if any declared `working_directory` is missing

That keeps planner drift from silently entering the queue and makes
`--audit-delivery-readiness` a truthful gate for this class of bug.

### 2026-04-04 — codex — integration-issue

`launch_review_cycle` review lanes currently use `agent: direct` plus
file-based validators (`file_exists`, `json_schema`) on `review.json`.

Measured failure:
- `review_r1` returns valid text output from `gpt-5.2-pro`
- no `review.json` file exists because direct LLM calls cannot write files
- the graph fails in wave 2 even though the review content was produced

Current local fix in `moltbot/scripts/meta/task_graph.py`:
- when a failed direct task has exactly one declared output path and non-empty
  `agent_output`, materialize that text to the output path
- then replay validators and recover only if they now pass

Keep this rule narrow. It is a bridge between direct text-generation lanes and
the graph's file-oriented validator contract, not a general excuse to mask
other validator failures.

### 2026-04-04 — codex — best-practice

The default review-cycle graph cannot truthfully use a direct review lane if
the prompt only passes local artifact paths (`implementation.md`, `review.json`)
instead of injecting file contents. A direct model cannot read those paths.

Measured consequence:
- review JSON becomes semantically `needs_changes` because the reviewer could
  not access the implementation note or repo diff
- the commit gate is also impossible to satisfy if the implementation prompt
  never explicitly instructs the agent to create a commit

Current safe default:
- review lane should be a workspace agent (`codex` in the current runtime)
- implementation prompt must explicitly require a descriptive commit before
  finishing

Without those two rules, the planner -> review -> commit path can execute but
cannot satisfy its own semantic acceptance criteria.

### 2026-04-04 — codex — integration-issue

The local `moltbot/scripts/meta/task_graph.py` bootstrap must not blindly
prepend canonical repo roots when a higher-priority module path is already
present on `PYTHONPATH`.

Measured failure:
- the proof run was started with an llm_client worktree override that contains
  the Codex transport fallback fix
- the local task-graph shim prepended `~/projects/llm_client` anyway
- that shadowed the worktree override and reintroduced the unfixed Codex SDK
  parser failure on `FileChangeItem.status="in_progress"`

Current safe rule:
- only prepend fallback repo roots when the target module is not already
  importable
- treat explicit `PYTHONPATH`/worktree overrides as intentional operator
  routing, not something bootstrap code is allowed to clobber

### 2026-04-04 — codex — integration-issue

The same import-precedence rule also applies in `run_task.py` before any graph
loading begins. Fixing only the local task-graph shim is insufficient.

Measured failure:
- the proof run still logged the old Codex SDK parse error after the shim fix
- llm_client observability showed the runner was still executing against the
  unfixed import path
- root cause: `run_task.py` prepended canonical `~/projects/llm_client` before
  importing shared modules, so the worktree override never reached `acall_llm`

Current safe rule:
- both bootstrap surfaces (`run_task.py` and `scripts/meta/task_graph.py`)
  must respect explicit earlier repo roots on `sys.path`
- if a caller wants a worktree override, bootstrap code may fill missing roots
  but must not reorder that override behind canonical repos

### 2026-04-04 — codex — bug-pattern

For this ecosystem layout, a parent directory that merely contains a repo named
`llm_client/` does not count as already exposing the `llm_client` package
facade.

Measured failure:
- `sys.path` contained a parent directory like `~/projects`
- bootstrap helpers saw `~/projects/llm_client` and assumed the module root was
  already present
- but `from llm_client import acall_llm` still failed because the real facade is
  `~/projects/llm_client/llm_client/__init__.py`

Current safe rule:
- only treat a path as already satisfying the bootstrap requirement when it
  exposes `module/__init__.py` or `module.py`
- repo-root presence alone is not enough in a repo-that-contains-a-package
  layout

### 2026-04-04 — codex — integration-issue

The remaining `python run_task.py <graph>` divergence turned out to be import
order inside `_run_graph_task(...)`, not generic `sys.path` corruption.

Measured repro:
- runtime launched with an approved llm_client worktree first on `PYTHONPATH`
- `_run_graph_task(...)` imported `scripts.meta.analyzer` before the local
  `scripts.meta.task_graph` shim
- that analyzer import resolved canonical `~/projects/llm_client` first and
  pinned it in `sys.modules`
- later task-graph bootstrap moved the worktree root to the front of
  `sys.path`, but it was too late because `llm_client` was already loaded

Current safe rule:
- import `scripts.meta.task_graph` before `scripts.meta.analyzer` in the graph
  runner path
- once the shim has loaded the intended llm_client module, later analyzer
  imports will reuse that same module instead of reintroducing the canonical
  repo
