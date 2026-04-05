# 24-Hour Runtime Sprint - 2026-04-05 Post-Merge

**Mission:** Merge the proven Plan #2 branches through dedicated integration worktrees, verify mainline truthfully, implement Plan #3 in a fresh post-merge worktree, and prove one fresh planner-generated non-doc code task through the real `python run_task.py <graph>` path with operator-readable task-level graph reports.

**Authority:** User explicitly approved continuous execution, worktree-only implementation between merges and pushes, frequent revertable commits, strong `CLAUDE.md` mandates, and autonomous continuation until every active phase is complete or a precisely documented blocker remains.

**Primary Plan:** `docs/plans/03_graph_report_task_result_observability.md`

**Dependency Checklist:** `docs/plans/post_merge_rollout_checklist_2026_04_05.md`

## Hard Stop Conditions

Only stop autonomous execution for:

1. An irreversible shared-state action not already authorized by this tracker
2. A new architectural decision that is not pre-made below and cannot be safely defaulted
3. A verified external dependency failure with no local workaround

If a hard stop occurs:

- commit every verified increment first
- record the blocker in this tracker and `KNOWLEDGE.md`
- leave the exact repro command, failing artifact path, and next restart step

## Mandatory Operating Rules

- Use dedicated git worktrees for every merge, verification, and implementation slice
- Keep canonical checkouts clean; they are integration roots, not scratchpads
- Commit every verified increment immediately before moving to the next phase
- Update this tracker whenever an uncertainty, blocker, or branch transition appears
- Do not declare completion from tests alone; completion requires the final real proof artifact

## Pre-Made Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Merge order | `llm_client` first, `openclaw` second | `openclaw` proof path depends on the isolated Codex home fix |
| Merge surface | dedicated integration worktrees only | Satisfies repo policy and preserves canonical checkouts as clean integration anchors |
| Post-merge implementation surface | fresh `openclaw` worktree from updated `main` | Avoids mixing pre-merge branch history with post-merge work |
| First post-merge feature | Plan #3 task-level graph report observability | Highest-leverage next gap after Plan #2 runtime proof |
| Proof target type | planner-generated non-doc code task | Must exercise the reviewed delivery lane on a real code change |
| Success evidence | tests + fresh report artifact + tracker entry + clean worktree | Prevents vague "looks good" merges |
| Report shape policy | additive schema only | Existing consumers must stay valid |
| Uncertainty handling | document immediately, continue with safer default | Matches nonstop execution mandate without hiding risk |

## Phase 1 - Lock Policy And Tracker

**Goal:** Commit the stronger execution mandate and this sprint tracker before changing repo state.

**Tasks:**

1. Commit the strengthened root `CLAUDE.md`
2. Add this tracker to the plan index
3. Commit the documentation checkpoint in the active worktree

**Acceptance Criteria:**

- `CLAUDE.md` explicitly requires worktree-only merge/implementation flow
- this tracker is committed and indexed

## Phase 2 - Merge `llm_client` Through Integration Worktree

**Goal:** Land the shared Codex isolation fix on mainline first.

**Tasks:**

1. Create a dedicated `llm_client` merge worktree from canonical `main`
2. Merge `codex/codex-transport-fallback`
3. Run:
   `python -m pytest -q tests/test_agents.py -k codex_mcp`
4. Commit the merge if needed, push mainline, and record exact verification

**Acceptance Criteria:**

- `llm_client/main` contains commit `44201fd` through a mainline merge
- selected `codex_mcp` test slice passes in the merge worktree
- merge worktree is clean after push

## Phase 3 - Merge `openclaw` Through Integration Worktree

**Goal:** Land the proven Plan #2 runtime path on mainline after the dependency is live.

**Tasks:**

1. Create a dedicated `openclaw` merge worktree from canonical `main`
2. Merge `codex/e2e-planner-review-commit`
3. Run:
   `python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py`
4. Reconfirm the fresh proof report:
   `/tmp/openclaw-proof-readme-fresh/reports/planner-2026-04-05-document-cli-default-readme_20260405T053153Z.json`
5. Push mainline and record exact verification

**Acceptance Criteria:**

- `openclaw/main` contains the Plan #2 branch through a mainline merge
- targeted runtime suite passes in the merge worktree
- the previously proven real report still satisfies:
  - `status = completed`
  - `review_gate.passed = true`
  - `commit_evidence.passed = true`
- merge worktree is clean after push

## Phase 4 - Create Post-Merge Implementation Worktree

**Goal:** Start Plan #3 from updated mainline, not from the historical feature branch.

**Tasks:**

1. Create a fresh implementation worktree from merged `openclaw/main`
2. Re-run the kickoff slice:
   `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`
3. Record any new mainline-only drift before editing

**Acceptance Criteria:**

- new implementation worktree exists on its own branch
- kickoff test slice is green before Plan #3 edits start

## Phase 5 - Implement Plan #3 In Verified Increments

**Goal:** Add additive task-level graph report observability without breaking current consumers.

**Tasks:**

1. Define the additive schema contract for `task_results`
2. Serialize bounded task-level summaries in `run_task.py`
3. Extend success-path and failure-path report tests
4. Update operator-facing docs if the normal report contract changes materially
5. Commit each verified increment separately

**Acceptance Criteria:**

- graph reports contain top-level `task_results` for graph runs
- failure reports expose the failing task id and error directly
- success reports expose all task statuses directly
- schema stays additive and validates

## Phase 6 - Fresh Post-Merge Non-Doc Code Proof

**Goal:** Prove the new report contract through the real runner on a fresh reviewed code task.

**Tasks:**

1. Generate or select one fresh planner-produced non-doc code task
2. Run it through the real `python run_task.py <graph>` entrypoint
3. Confirm the final report shows:
   - `status = completed`
   - `review_gate.passed = true`
   - `commit_evidence.passed = true`
   - non-empty `task_results`
4. Record the artifact path in this tracker and in `KNOWLEDGE.md`

**Acceptance Criteria:**

- one fresh planner-generated non-doc code task completes through the real runner
- final report contains truthful task-level summaries

## Phase 7 - Merge Post-Merge Implementation Worktree

**Goal:** Land Plan #3 on mainline and leave the repos clean.

**Tasks:**

1. Create or reuse a dedicated `openclaw` merge worktree from updated `main`
2. Merge the Plan #3 implementation branch
3. Re-run the targeted report/runtime suites
4. Push mainline
5. Update tracker, docs, and residual-risk notes

**Acceptance Criteria:**

- Plan #3 branch is merged to `main`
- mainline verification passes after merge
- all involved worktrees are clean or intentionally removed

## Initial Uncertainties

1. The exact non-doc planner-generated code task chosen for the post-merge proof may affect runtime duration and review noise.
   Safe default:
   - choose the smallest code change that still exercises a real reviewed code path
2. Existing report consumers may assume graph reports have no per-task summary array.
   Safe default:
   - make the schema additive only and keep existing top-level fields untouched
3. Mainline may have moved since the proof branches were pushed.
   Safe default:
   - merge in dedicated integration worktrees, resolve conflicts there, and re-run the minimal truthful verification before any push

## 2026-04-05 06:41 PT - Merge Phases Completed Truthfully

Phase 2 and Phase 3 are complete.

Verified merge and verification results:

- `llm_client` merged to `main` from dedicated integration worktree
  `merge-codex-transport-main-20260405`
- `llm_client` selected verification passed:
  `python -m pytest -q tests/test_agents.py -k codex_mcp`
- `openclaw` merged to `main` from dedicated integration worktree
  `merge-e2e-planner-main-20260405`
- merge-time targeted verification passed:
  `python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py`
- prior fresh proof report reconfirmed:
  `/tmp/openclaw-proof-readme-fresh/reports/planner-2026-04-05-document-cli-default-readme_20260405T053153Z.json`
  with:
  - `status = completed`
  - `review_gate.passed = true`
  - `commit_evidence.passed = true`

Important integration finding:

- the branch merge surfaced one stale extraction assumption:
  `scripts.meta.task_graph` and `scripts.meta.analyzer` were still trying to
  load `project-meta/scripts/meta/*`
- merged mainline verification forced the truthful correction: both shims now
  load the repo-local top-level runtime modules instead

Operational caveat for next proof:

- use `~/projects/llm_client_worktrees/merge-codex-transport-main-20260405`
  as the `llm_client` source for live proofs
- do not use the canonical `~/projects/llm_client` checkout yet because it has
  unrelated local drift outside the approved merge

## 2026-04-05 06:49 PT - Phase 4 Baseline Confirmed

Phase 4 is complete.

Verified state:

- fresh implementation worktree created from merged `openclaw/main`:
  `plan-3-task-results-observability`
- kickoff suite passed on merged mainline before any Plan #3 edits:
  `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`

## 2026-04-05 07:02 PT - Plan #3 Implementation Slice Verified

Phase 5 implementation is in progress, with the first verified increment ready
to commit.

Implemented and verified:

- normal graph reports now carry additive bounded `task_results` summaries
- each task summary includes:
  - `task_id`
  - `status`
  - `wave`
  - `model_selected`
  - `requested_model`
  - `resolved_model`
  - `duration_s`
  - `error`
  - compact `validation_summary`
- report-path tests now assert both:
  - successful graph reports expose all task statuses
  - failed graph reports expose the failing task id and error directly

Verification:

- `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`
- `python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py`

## 2026-04-05 07:09 PT - First Live Plan #3 Proof Failed Truthfully

Phase 6 produced a real failed report artifact, not a transport or routing
stall.

Proof artifact:

- `/tmp/openclaw-proof-plan3-task-results-live/reports/planner-2026-04-05-add-failing-task-id-to-report_20260405T140726Z.json`

Observed truth:

- top-level report status was `failed`
- the report included the new bounded `task_results` summaries without any
  debug provenance sidecar
- the review artifact clearly rejected the code task with a specific finding
  about the failure-path test shape

Exact review finding:

- the proof task added `run.first_failed_task_id`, but its new test modeled a
  graph failure as `ExecutionReport.status="failed"`
- the real task-graph runtime uses `ExecutionReport.status="partial"` when a
  graph fails after at least one wave has already run
- that meant the new proof task was not actually validating the production
  failure path

Corrective action:

- normalize any non-completed graph execution to final operator-facing
  `status="failed"`
- keep the raw task-graph outcome under `run.graph_execution_status`
- update the failure-path report test to use the real `partial` execution state

Verification after the corrective patch:

- `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`
- `python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py`

## 2026-04-05 07:17 PT - Fresh Plan #3 Proof Completed

Phase 6 is complete.

Successful proof artifact:

- `/tmp/openclaw-proof-plan3-task-wave-live/reports/planner-2026-04-05-add-failing-task-wave-to-report-triage_20260405T141713Z.json`

Truth conditions verified from the final report:

- `status = completed`
- `destination = completed`
- `review_gate.passed = true`
- `commit_evidence.passed = true`
- `task_results` present with three bounded task summaries

Proof-specific code landed by the reviewed lane:

- `242b0ed` `[Plan #3] Add failing task wave triage to graph reports`
- `647c13d` `[Plan #3] Add round 1 failing-wave implementation note`

Post-proof branch verification:

- `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`
- `python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py`
