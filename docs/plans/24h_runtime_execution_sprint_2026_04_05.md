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
- Exact root cause identified: `_run_graph_task(...)` imported
  `scripts.meta.analyzer` before the local `scripts.meta.task_graph` shim. That
  analyzer import pulled canonical `~/projects/llm_client` into `sys.modules`
  before the shim could promote the approved llm_client worktree override, so
  later graph execution stayed pinned to the stale Codex transport module.

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

## 2026-04-04 21:05 PT - Exact Entrypoint Divergence Isolated

Deterministic repro now exists for the remaining script-entrypoint import drift.

- Baseline setup that reproduces the bug:
  `PYTHONPATH=<llm_client-worktree>:$PYTHONPATH python run_task.py <graph>`
- If `_run_graph_task(...)` imports `scripts.meta.analyzer` first, that module
  resolves canonical `~/projects/llm_client` before the local
  `scripts.meta.task_graph` shim runs its bootstrap
- Once canonical `llm_client` is in `sys.modules`, the later shim import order
  no longer matters and the runtime remains pinned to the stale
  `agents_codex.py` without `subprocess`
- Importing `scripts.meta.task_graph` first reproduces the successful path:
  the worktree override becomes the loaded `llm_client`, and later analyzer
  imports reuse that already-loaded module

Immediate action:

- make graph runtime imports explicit and ordered (`task_graph` before
  `analyzer`)
- add regression coverage for the import-order boundary
- rerun the targeted bootstrap suite and the real script-entrypoint proof

## 2026-04-04 21:12 PT - Real Entrypoint Proof Completed Truthfully

The script-entrypoint path now completes the full review-cycle graph under the
approved llm_client worktree override.

Verified evidence:

- targeted regression suite passed:
  `python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py`
- real runner command completed:
  `PYTHONPATH=<llm_client-worktree>:$PYTHONPATH LLM_CLIENT_CODEX_TRANSPORT=cli OPENCLAW_DEBUG_RUNTIME_PROVENANCE=<path> OPENCLAW_TASKS_DIR=/tmp/openclaw-proof-cli-fresh python run_task.py <graph>`
- provenance now shows the correct imported modules:
  - `llm_client_file = <llm_client-worktree>/llm_client/__init__.py`
  - `agents_codex_file = <llm_client-worktree>/llm_client/sdk/agents_codex.py`
  - `agents_codex_has_subprocess = true`
- report `/tmp/openclaw-proof-cli-fresh/reports/planner-2026-04-05-add-planner-lineage-to-audit-fresh_20260405T041202Z.json`
  recorded:
  - `status = completed`
  - `destination = completed`
  - `review_gate.passed = true`
  - `commit_evidence.passed = true`
  - `commit_evidence.commit_sha = 49a738f2a44fff3ca4dfb7cf57b8f73465bd1648`

Remaining gaps before declaring the overnight slice fully closed:

- rerun one genuinely fresh graph id with fresh artifact paths, not only a
  replayed historical proof id
- decide whether the operator-truthful default should remain `auto` or be
  hardened to explicit `cli` for review-cycle runs when `TIMEOUT_POLICY=ban`

## 2026-04-04 21:20 PT - Auto Default Proven Unsafe For Current Runtime

The fresh graph-id proof answered the transport-policy question.

Command:

- `PYTHONPATH=<llm_client-worktree>:$PYTHONPATH OPENCLAW_DEBUG_RUNTIME_PROVENANCE=<path> OPENCLAW_TASKS_DIR=/tmp/openclaw-proof-auto-fresh python run_task.py <fresh-graph>`

Observed behavior:

- runtime defaulted `LLM_CLIENT_CODEX_TRANSPORT=auto`
- provenance confirmed `codex_transport_resolved = auto`
- live execution logged `CODEX_TRANSPORT_FALLBACK[sdk->cli]`
- despite that fallback, wave 1 still failed with `Task timed out after 300s`
- report status was only `partial`; no fresh implementation artifact existed to
  recover from validators

Decision:

- change the autonomous default in `run_task.py` from `auto` to explicit `cli`
- keep explicit operator overrides honored
- rerun the same fresh graph without any transport override to prove the new
  default completes truthfully

## 2026-04-04 21:36 PT - External Provider Limit Reached

The next remaining fresh-graph proofs are currently blocked by an external
Codex account/runtime limit, not by a local `moltbot` or `llm_client` code bug.

Verified evidence:

- direct llm_client SDK path (isolated worktree import) failed with:
  `You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 10:07 PM.`
- direct isolated CLI repro also failed with the same usage-limit message
  after startup:
  - `ERROR: You've hit your usage limit ... try again at 10:07 PM.`
- the same CLI stderr also still reports a broken external MCP auth surface:
  `mcp.linear.app ... invalid_token`

Local actions completed before stopping:

- committed `moltbot` import-precedence/runtime proof work
- committed `moltbot` transport-default documentation updates
- committed shared `llm_client` Codex-home isolation fix
- updated `README.md` to document the proven CLI default and override rule

Why this is a hard stop:

- further fresh review-cycle proofs require live Codex execution
- the provider is currently refusing new work for this account/runtime window
- there is no local code-only workaround for exhausted provider quota

Exact restart path once quota resets:

1. Ensure `PYTHONPATH=/home/brian/projects/llm_client_worktrees/codex-transport-fallback:$PYTHONPATH`
2. Re-run the fresh README graph from:
   `/tmp/openclaw-proof-readme-fresh/failed/planner-2026-04-05-document-cli-default-readme.yaml`
3. Confirm the resulting report lands in `/tmp/openclaw-proof-readme-fresh/reports/`
   with:
   - `status = completed`
   - `review_gate.passed = true`
   - `commit_evidence.passed = true`

## 2026-04-04 22:32 PT - Fresh README Graph Passed End To End

Quota reset removed the external provider stop condition, and the fresh README
graph now completes truthfully through the real script entrypoint.

Verified evidence:

- report:
  `/tmp/openclaw-proof-readme-fresh/reports/planner-2026-04-05-document-cli-default-readme_20260405T053153Z.json`
- final report fields:
  - `status = completed`
  - `destination = completed`
  - `review_gate.passed = true`
  - `commit_evidence.passed = true`
  - `commit_evidence.commit_sha = 7fd4ff833c430956a9589adc4e67c153d1aca20b`
- provenance still confirms the intended runtime path:
  - llm_client imported from the llm_client worktree
  - `codex_transport_resolved = cli`
  - script-entrypoint runner executed all 3 waves

Outcome:

- planner -> review -> commit is now proven through the real `python run_task.py <graph>` path
- import-precedence divergence is fixed
- operator-default Codex transport policy is documented and tested
- shared llm_client runtime now isolates Codex home by default to avoid leaking
  broken global MCP config into autonomous runs
