# 24-Hour Runtime Sprint - 2026-04-04

**Mission:** Make `moltbot` execute one truthful default autonomous code-delivery path from planner output through review gating to commit evidence, then prove it on a bounded real task.

**Authority:** User explicitly approved continuous execution, worktree-first execution, regular commits, and phase-by-phase autonomous progress.

**Primary Plan:** `docs/plans/02_end_to_end_planner_review_commit_flow.md`

**Start State:**

- Dedicated worktree: `codex/e2e-planner-review-commit`
- No active coordination claims detected
- Existing proof exists for bounded runtime execution, but not for planner -> review-cycle -> commit as one coherent default path

## Hard Stop Conditions

Only stop autonomous execution for:

1. An irreversible action affecting shared state outside the sprint worktree
2. A real architectural ambiguity not already pre-decided in Plan #2
3. A blocked external dependency that cannot be worked around locally

If a hard stop condition occurs:

- commit all verified work
- append the blocker to Plan #2 or `KNOWLEDGE.md`
- leave the tracker with the exact blocked phase and next command to run

## Operational Rules For This Sprint

- Work only in the dedicated branch worktree until merge/push time
- Commit every verified phase or sub-phase immediately
- Keep test evidence in commit messages and plan updates
- When an uncertainty appears, write it down before changing approach
- Do not bulk-migrate historical pending tasks during this sprint

## Phases

### Phase A - Planning And Repo Policy

**Goal:** Make the execution contract durable in repo docs before code changes expand.

**Tasks:**

1. Strengthen `CLAUDE.md` with worktree-first, frequent-commit, and continuous-execution requirements
2. Persist Plan #2 and mark it in progress
3. Write this tracker file

**Acceptance Criteria:**

- `CLAUDE.md` contains the strong execution mandate
- Plan #2 exists in the sprint worktree
- This tracker exists and names hard stop conditions

### Phase B - Planner Contract

**Goal:** Make planner output explicit enough to choose the correct execution path without prose inference.

**Tasks:**

1. Extend planner response models with delivery contract fields
2. Update planner prompts to emit those fields consistently
3. Add deterministic validation for invalid delivery-mode combinations
4. Add tests covering schema and validation behavior

**Acceptance Criteria:**

- Planner rejects invalid delivery contracts
- Planner defaults code tasks to `review_cycle`
- Tests for planner contract pass

### Phase C - Dual Queue Writer

**Goal:** Let the planner emit either flat tasks or review-cycle graphs via one explicit writer path.

**Tasks:**

1. Refactor planner queue writing into flat and review-cycle writers
2. Reuse `launch_review_cycle` as a library path for graph emission
3. Make graph ids and filenames deterministic from the planner task id
4. Add tests for deterministic graph emission

**Acceptance Criteria:**

- Flat markdown output remains backward compatible
- Planner can write review-cycle graphs directly into the queue
- Deterministic artifact naming is covered by tests

### Phase D - Truthful Review Gate

**Goal:** Make graph success depend on semantic review pass, not just graph execution.

**Tasks:**

1. Extend graph metadata with final review artifact and planner lineage
2. Add post-graph semantic review inspection in `run_task.py`
3. Route graphs to `failed` when the final review status is not `pass`
4. Add tests for pass and fail review outcomes

**Acceptance Criteria:**

- Graph completion requires review `status == "pass"`
- Missing or invalid review artifacts fail the task
- Review gate outcome is recorded in reports

### Phase E - Commit Gate And Reporting

**Goal:** Make graph success require commit evidence and surface that evidence in reports.

**Tasks:**

1. Add graph-level commit detection tied to task start time
2. Route review-passing/no-commit cases to `failed`
3. Extend graph and flat reports with lineage, delivery mode, and gate fields
4. Add tests for report fields and commit-gate behavior

**Acceptance Criteria:**

- Review pass without commit is not accepted
- Reports include commit evidence and gate outcomes
- Existing recovery tests still pass

### Phase F - End-To-End Proof

**Goal:** Prove the new path on one safe planner-generated code task.

**Tasks:**

1. Generate a bounded planner task for a safe target repo
2. Confirm planner emits `review_cycle`
3. Run the queued graph through the runtime
4. Verify completion, review pass, commit evidence, and final report fields
5. Document any runtime surprises in `KNOWLEDGE.md`

**Acceptance Criteria:**

- One planner-generated code task completes through the full gated path
- Completed report carries the expected lineage and evidence
- Any new runtime issue is documented durably

### Phase G - Queue Hygiene Boundary

**Goal:** Make rollout operationally legible without rewriting the old queue.

**Tasks:**

1. Add an audit-only readiness classifier for pending tasks
2. Document how legacy flat tasks are treated during rollout
3. Update README or plan docs with the operational rule

**Acceptance Criteria:**

- There is a non-destructive audit command for pending tasks
- Rollout boundary between legacy tasks and new planner tasks is documented

## Progress Log

### 2026-04-04T00:00:00Z

- Sprint tracker created
- Dedicated worktree created
- Plan #2 moved to in-progress state
- Next phase: Phase A completion, then planner contract implementation

### 2026-04-04T01:00:00Z

- Phase A completed and committed
- Phase B completed: planner contract now includes `task_kind`, `delivery_mode`,
  `file_scope`, and `review_rounds`
- Phase C implementation completed: planner now emits either flat markdown tasks
  or review-cycle graph YAML via one deterministic writer path
- Added planner and graph contract tests; targeted suite passed
- Runtime workaround documented: execute `moltbot` worktrees from within
  `~/projects/` so the current shared-import bootstrap remains valid
- Next phase: review-pass and commit-evidence gating in `run_task.py`

### 2026-04-04T02:00:00Z

- Phase D implementation completed: `run_task.py` now reads graph metadata and
  applies a semantic review gate based on the final review JSON
- Phase E implementation completed: planner-generated review-cycle graphs now
  require commit evidence newer than task start and emit additive report fields
- Added runtime tests for graph review failure, missing commit failure, graph
  success with both gates satisfied, and flat/graph report metadata
- Targeted test suite passed across planner, graph-builder, runtime gate, and
  bounded recovery coverage
- Next phase: README truthfulness updates and one real end-to-end proof task

### 2026-04-04T03:00:00Z

- First proof attempt reached real graph dispatch and exposed two concrete
  blockers instead of speculative ones:
  - `run_task.py` still needed truthful bootstrap roots for `project-meta`
    `scripts.meta.*` imports
  - `review_cycle.defaults.yaml` pinned non-agent models for file-writing
    context/synthesis tasks, causing validator failure in wave 1
- Added a runtime import smoke test and fixed the bootstrap roots
- Changed default context/synthesis models to agent-capable `codex` resolution
  and added a regression test for that contract
- Next phase: regenerate the proof graph from the planner and rerun the
  end-to-end cycle

### 2026-04-04T04:00:00Z

- Second proof attempt proved the agent-capable model fix worked: wave 1 now
  dispatched `context_init` as `codex`
- The next concrete blocker was artifact locality: repo agents did not produce
  review-cycle workspace files under `~/.openclaw/workspace/...`
- Updated the review-cycle default workspace to repo-local
  `.openclaw/review-cycles` and taught `build_graph()` to resolve relative
  workspace roots under the target repo
- Added a regression test to keep relative cycle workspaces inside the repo
- Next phase: regenerate the proof graph again and continue the end-to-end run

### 2026-04-04T05:00:00Z

- Third proof attempt proved the repo-local workspace fix worked:
  `context_pack.md` was actually written inside `.openclaw/review-cycles/`
- The remaining blocker was a false-negative task-graph failure after validated
  outputs existed
- Added local `scripts/meta/task_graph.py` and `scripts/meta/analyzer.py` shims
  so `moltbot` owns the runtime import surface while still delegating to the
  canonical `project-meta` implementations
- Added narrow validator-backed post-success recovery for failed graph tasks and
  a regression test that locks the behavior down
- Next phase: rerun the exact proof graph against the local shim and continue
  through implementation/review/commit gating

### 2026-04-04T06:00:00Z

- The local shim initially did not take effect because `scripts.meta` was still
  resolving to the external namespace package
- Added local `scripts/__init__.py` and `scripts/meta/__init__.py` so `moltbot`
  definitively owns `scripts.meta.task_graph` and `scripts.meta.analyzer`
- Extended tests now pass against the explicit local package boundary
- Next phase: rerun the end-to-end proof on the now-localized graph runtime

### 2026-04-04T07:00:00Z

- Phase G completed: `run_task.py` now exposes `--audit-delivery-readiness` as
  a non-destructive operator path before queue execution
- Added audit coverage for flat tasks, graph tasks, graph-load failure
  observability, and CLI early exit without dispatch
- Updated the README rollout boundary section so the readiness audit is part of
  the documented operator workflow
- Next phase: rerun the planner-generated proof task and isolate the remaining
  `implement_r1` workspace-agent failure from the already-fixed orchestration
  seams

### 2026-04-04T08:00:00Z

- The remaining proof blocker is now pinned to one concrete Codex SDK parsing
  defect during file-writing tasks, not to `moltbot` graph orchestration
- A trivial direct `acall_llm(\"codex\", ...)` call succeeds in this
  environment, so the general transport path is healthy
- Replaying the exact `implement_r1` prompt fails inside `openai_codex_sdk`
  with:
  `ValidationError: FileChangeItem.status Input should be 'completed' or 'failed'; input was 'in_progress'`
- This means the next phase must patch the llm_client/Codex transport boundary
  or opt graph tasks into a durable CLI fallback path before rerunning the full
  proof

### 2026-04-04T09:00:00Z

- OpenClaw now defaults `LLM_CLIENT_CODEX_TRANSPORT=auto` inside `run_task.py`
  unless an operator already set a transport explicitly
- Under the current timeout policy (`LLM_CLIENT_TIMEOUT_POLICY=ban`), that
  means Codex lanes route directly to the CLI path with a hard timeout instead
  of re-entering the SDK parser that fails on `FileChangeItem.status="in_progress"`
- Added runtime bootstrap tests that lock down both behaviors:
  default to `auto`, but do not override an explicit operator transport
- The direct implementation-lane replay also landed two truthful improvements
  now kept in the branch:
  - clearer README documentation for `--audit-delivery-readiness`
  - one extra CLI success-path audit test
- Next phase: rerun the planner-generated proof on the clean queue and confirm
  review pass, commit evidence, and completed reporting on the CLI-backed Codex
  path

### 2026-04-04T10:00:00Z

- A fresh planner-generated proof task exposed one more deterministic contract
  bug before execution:
  the planner emitted a hallucinated nested repo path ending in `/openclaw`
  instead of the explicitly targeted worktree root
- Fixed the planner boundary so a single explicit `--target-project` now
  normalizes generated tasks to that exact repo path
- Fixed graph preflight so missing task `working_directory` paths fail the
  readiness audit with `OPENCLAW_PREFLIGHT_WORKDIR_MISSING`
- Added regression tests for both contracts
- Next phase: regenerate the proof graph using the corrected planner boundary,
  audit it, and run the full planner -> review -> commit path again

### 2026-04-04T11:00:00Z

- Running the proof with the llm_client Codex fallback patch on `PYTHONPATH`
  advanced the graph past implementation and into the review lane
- `implement_r1` is now no longer the blocker:
  the local shim recovered it after validators passed and the implementation
  note was written successfully
- The new blocker is the direct review lane itself:
  `review_r1` produced model output but no `review.json`, so file-based review
  validators failed in wave 2
- Fixed the local task-graph shim to materialize direct single-output task text
  to the declared output path before validator replay, with regression coverage
- Next phase: commit the shim fix, then resume the same proof task so it can
  proceed beyond the review lane and test synthesis plus commit gating

### 2026-04-04T12:00:00Z

- The resumed proof advanced through implementation, review JSON materialization,
  and synthesis artifact creation, which exposed the next semantic blockers
- Direct review remained non-truthful even after file materialization because
  the reviewer only received local file paths, not artifact contents
- The implementation prompt also never explicitly required a commit, so the
  commit gate was not satisfiable by construction
- Fixed the graph producer defaults:
  - default review lane is now a workspace Codex agent
  - implementation prompts now explicitly require a descriptive commit before
    finishing and note the commit SHA in the implementation note
- Added graph-contract tests that lock down both requirements
- Next phase: commit the default review/commit policy change, regenerate the
  proof task under the corrected graph defaults, and rerun the full path
