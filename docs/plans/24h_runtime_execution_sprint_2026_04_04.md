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
