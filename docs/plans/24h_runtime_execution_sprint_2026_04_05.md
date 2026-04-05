# 24-Hour Runtime Sprint - 2026-04-05

**Mission:** Eliminate the remaining `python run_task.py <graph>` runner-entrypoint divergence, prove one fresh planner-generated code task through `planner -> review -> commit` under truthful gating, and leave merge-ready committed checkpoints.

**Authority:** User explicitly approved continuous overnight execution, worktree-only implementation, frequent revertable commits, and phase-by-phase autonomous continuation until acceptance criteria are met or a documented blocker remains.

**Primary Plan:** `docs/plans/02_end_to_end_planner_review_commit_flow.md`

**Current Proven State:**

- Dedicated worktree: `codex/e2e-planner-review-commit`
- Cross-repo llm_client worktree: `codex/codex-transport-fallback`
- In-process debug execution of `_run_graph_task(...)` can now complete
  `implement_r1`, `review_r1`, and `synthesize`
- The latest truthful review finding exposed and then fixed a namespace-package
  bootstrap false positive in `run_task.py` and `scripts/meta/task_graph.py`
- The exact bootstrap/audit/report/planner contract suite now passes

**Current Blocker:**

- Executing the same graph via `python run_task.py <graph>` still diverges from
  the successful in-process path
- The divergence is specific to the script-entrypoint runner path, not to the
  planner contract, review graph shape, or direct `acall_llm(...)` viability

## Hard Stop Conditions

Only stop autonomous execution for:

1. An irreversible action affecting shared state outside the active worktree
2. A new architectural ambiguity not already decided in Plan #2
3. A verified external dependency failure with no local workaround

If a hard stop occurs:

- commit every verified local increment first
- write the blocker precisely in this tracker and `KNOWLEDGE.md`
- leave the exact next command or repro path for restart

## Mandatory Operating Rules

- Work only in dedicated worktrees until merge/push time
- Commit each verified phase or sub-phase immediately
- Prefer the smallest truthful proof slice over broad speculative changes
- Every uncertainty or blocker must be written down before changing approach
- Do not leave generated artifacts or uncommitted drift ambiguous at handoff

## Phases

### Phase A - Lock Policy And Tracker

**Goal:** Make the overnight execution contract explicit and durable in-repo.

**Tasks:**

1. Strengthen `CLAUDE.md` with stronger worktree-only, frequent-commit, and
   continuous-execution language
2. Create this tracker and add it to the plan index
3. Commit the policy/tracker checkpoint

**Acceptance Criteria:**

- `CLAUDE.md` strongly states worktree-only implementation and nonstop
  phase-to-phase execution
- This tracker is committed and indexed

### Phase B - Runner-Entrypoint Divergence Instrumentation

**Goal:** Reduce the remaining failure from a symptom to one exact code-path
difference.

**Tasks:**

1. Capture the imported module locations and transport settings for:
   - `python run_task.py <graph>`
   - imported `run_task._run_graph_task(...)`
2. Add temporary or durable observability around per-task failures so the
   outer report no longer hides the underlying `TaskResult.error`
3. Produce one deterministic repro showing where script-entrypoint behavior
   diverges from the successful in-process path

**Acceptance Criteria:**

- One exact runner-entrypoint divergence is named in code terms
- The divergence is documented in the tracker and/or `KNOWLEDGE.md`

### Phase C - Entrypoint Parity Fix

**Goal:** Make script execution and in-process execution use the same truthful
runtime path.

**Tasks:**

1. Fix the identified divergence at the smallest correct boundary
2. Add regression tests covering the exact script-vs-import failure mode
3. Commit the fix once the targeted tests pass

**Acceptance Criteria:**

- `python run_task.py <graph>` no longer fails for the previously isolated
  divergence reason
- Regression coverage exists for the concrete failure mode

### Phase D - Truthful Codex Runtime Policy

**Goal:** Lock a truthful default for Codex transport/runtime settings during
review-cycle execution.

**Tasks:**

1. Decide whether the truthful short-term default is `codex_transport=cli`,
   `auto`, or another explicit operator/runtime setting
2. Encode that policy in code or runtime bootstrap, not only in shell usage
3. Document the rule and add tests for defaulting/preservation behavior

**Acceptance Criteria:**

- The runtime uses one explicit truthful Codex transport policy by default or
  by graph metadata for review-cycle tasks
- That policy is documented and regression-tested

### Phase E - Fresh End-To-End Proof

**Goal:** Prove the full path on a fresh planner-generated graph with fresh
artifact paths, no stale-output contamination, and final gated completion.

**Tasks:**

1. Generate or clone a fresh graph task with a new graph id and clean output
   paths
2. Run it through the real script entrypoint
3. Verify:
   - implementation note written
   - review JSON written
   - synthesis artifact written
   - final review gate `status == "pass"`
   - commit evidence present
   - final report routes to `completed`

**Acceptance Criteria:**

- One fresh planner-generated code task completes end-to-end through the real
  script entrypoint
- Final report includes planner lineage, review gate pass, and commit evidence

### Phase F - Merge-Readiness And Rollout Notes

**Goal:** Leave the branch ready for review/merge with clear rollout guidance.

**Tasks:**

1. Update README or plan docs with the truthful default runtime path
2. Ensure no undocumented operator-only shell tricks remain required
3. Commit final docs/tests/implementation changes

**Acceptance Criteria:**

- Branch is clean
- Docs state the truthful default behavior
- Residual uncertainties, if any remain, are documented precisely

## Documented Uncertainties At Start

1. The script-entrypoint runner still diverges from the in-process path even
   when both load the llm_client worktree and explicit CLI transport
2. It is not yet proven whether the remaining divergence is transport-policy
   state, event-loop/process state, or task-runner integration state
3. The long-term truthful default may still be `auto` if the llm_client
   fallback path is repaired, but the short-term truthful default may need to
   be explicit CLI transport until then
