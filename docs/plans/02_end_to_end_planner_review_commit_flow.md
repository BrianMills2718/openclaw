# Plan #2: End-to-End Planner -> Review -> Commit Flow

**Status:** In Progress
**Type:** implementation
**Priority:** High
**Blocked By:** None
**Blocks:** Phase 6.2 completion, any truthful claim that the runtime has one default autonomous code-delivery path

---

## Gap

**Current:** `task_planner.py` emits only flat markdown tasks into `~/.openclaw/tasks/pending/`. `run_task.py` can execute both flat tasks and graph tasks, but the review-cycle graph path is a separate producer in `launch_review_cycle.py` and is not the default output of the planner. The flat path has deterministic preflight and post-run validation, but no mandatory semantic review gate. The graph path can produce implementation/review artifacts, but a graph currently counts as `completed` when graph execution succeeds, not when the final review explicitly passes and a commit is present.

**Target:** One explicit default path for autonomous code-changing work:

1. planner produces a queue item with an explicit delivery contract
2. queue item routes code-changing work into a one-round review-cycle graph
3. supervisor dispatches the graph
4. implementation step makes the bounded code change
5. review step produces machine-readable review output
6. runtime accepts the task only when the review result is `pass`
7. runtime accepts the task as fully complete only when commit evidence is present
8. structured reports surface planner lineage, review outcome, validation result, and commit evidence

Flat markdown tasks remain supported for bounded low-risk work that does not require a review gate.

**Why:** Phase 6.2 needs real data to flow through the whole system, not adjacent partial paths. The planner, queue, runtime runner, review gate, validation, reporting, and commit evidence need to behave as one coherent delivery pipeline.

---

## References Reviewed

- `run_task.py` - current supervisor loop, flat-task execution path, graph-task execution path, post-success recovery, preflight and validation behavior
- `task_planner.py` - planner schema, prompt call, flat-task writer, pending-queue contract
- `launch_review_cycle.py` - graph builder, review JSON schema, one-round review-cycle generation
- `review_cycle.defaults.yaml` - current implementation/review/context/synthesis defaults
- `README.md` - declared runtime contract and queue behavior
- `CLAUDE.md` - repo-local ownership and documentation expectations
- `schemas/flat_task_report.schema.json` - current flat report contract
- `schemas/graph_task_report.schema.json` - current graph report contract
- `~/.openclaw/tasks/completed/impl_review_ac10_pilot4.yaml` - example completed review-cycle graph artifact
- `~/.openclaw/tasks/reports/impl_review_ac10_pilot4_20260315T063342Z.json` - example completed graph report
- `~/.openclaw/tasks/reports/runtime-proof-2026-04-02-json-diff-summary-only-moltbot-rerun-2_20260403T060844Z.json` - proof that bounded runtime dispatch plus validation can reach a completed state
- `~/projects/project-meta/docs/ops/PHASE_6_3_PREREQUISITE_ASSESSMENT_2026-04-04.md` - current statement that the review gate is partial and auto-commit still needs proof
- `~/projects/project-meta/docs/ops/PHASE62_SIGNAL_QUALITY_2026_04_02.md` - current queue quality issues and stale pending-task risks

---

## Files Affected

- `task_planner.py` (modify)
- `prompts/task_planner.yaml` (modify)
- `launch_review_cycle.py` (modify)
- `run_task.py` (modify)
- `schemas/flat_task_report.schema.json` (modify)
- `schemas/graph_task_report.schema.json` (modify)
- `README.md` (modify)
- `tests/test_task_planner_delivery_modes.py` (create)
- `tests/test_launch_review_cycle_graph_contract.py` (create)
- `tests/test_run_task_review_gate.py` (create)
- `tests/test_run_task_reports.py` (create)
- `docs/plans/02_end_to_end_planner_review_commit_flow.md` (create)
- `docs/plans/CLAUDE.md` (modify)

---

## Pre-Made Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Queue formats | Keep both flat `.md` tasks and graph `.yaml` tasks | Flat tasks already exist and are useful for low-risk bounded work; this plan adds a truthful default path for code delivery rather than deleting compatibility surfaces |
| Default delivery mode for code-changing planner output | Planner-generated code-changing work goes through review-cycle graph tasks, not flat tasks | The whole-system target is planner -> review gate -> commit, so code changes cannot keep bypassing review by default |
| Default delivery mode for non-code work | Docs-only, analysis-only, and queue-maintenance work stays on the flat-task path | This keeps the graph path focused on work that genuinely benefits from implementation/review separation |
| Planner output contract | Extend planner output with explicit `task_kind`, `delivery_mode`, optional `file_scope`, and optional `review_rounds` | The queue writer needs an explicit execution contract instead of inferring everything from prose |
| Graph generation mechanism | Reuse `launch_review_cycle.build_graph()` instead of inventing a second graph format | Existing graph wiring already expresses implementation, review, context, and synthesis tasks and should be reused |
| Initial review depth | Use `review_rounds=1` for the first rollout slice | This is the smallest real proof of planner -> graph -> review -> commit flow; multi-round convergence can be a follow-on once the first gate is truthful |
| Review-gate truth condition | A review-cycle graph is only accepted when the final review JSON has `status == "pass"` | Schema-valid review output alone is not enough; the semantic result must gate acceptance |
| Commit truth condition | Planner-generated review-cycle tasks require new repo commit evidence to count as complete in the first rollout slice | The user goal is full-system flow through to landing verified work; “files changed but not committed” is not enough for this slice |
| Where to implement semantic review/commit gating | Implement in `run_task.py` after graph execution returns, not inside generic `task_graph` infrastructure | This keeps the change local to `moltbot` and avoids widening scope into shared task-graph infrastructure before the runtime contract is proven |
| Legacy queue handling | Do not bulk-migrate historical pending flat tasks in this slice | Bulk queue migration is separate operational cleanup; the first goal is to prove the new path with newly planned work |
| Review defaults | Keep the current review default (`agent: direct`, `model: gpt-5.2-pro`) unless this plan explicitly proves a better alternative | Avoid mixing flow wiring with model-policy changes |
| Graph artifact naming | Derive planner-produced review graphs deterministically from the planner task id | Reports, queue entries, and completed/failed artifacts need stable lineage for deduplication and observability |

---

## Target Execution Contract

### Queue item kinds

| Kind | Meaning | Default delivery mode |
|------|---------|-----------------------|
| `code_change` | Changes production code, schemas, validators, CLI behavior, or tests | `review_cycle` |
| `docs_only` | Bounded doc, README, CLAUDE.md, AGENTS.md, or comments-only work | `flat` |
| `analysis_only` | Investigation, triage, inventory, research notes, or queue analysis with no required repo changes | `flat` |
| `queue_maintenance` | Queue cleanup, stale-task repair, model-name repair, or runtime bookkeeping | `flat` |

### Planner output additions

Every planner-emitted task item must include:

- `task_kind`: one of `code_change | docs_only | analysis_only | queue_maintenance`
- `delivery_mode`: one of `flat | review_cycle`
- `file_scope`: optional list of repo-relative paths or globs when the scope is known
- `review_rounds`: optional integer, required when `delivery_mode == review_cycle`

### Acceptance semantics

For `delivery_mode == flat`:

- existing flat-task behavior stays intact
- task may complete on validation pass
- report must record planner lineage when the task came from the planner

For `delivery_mode == review_cycle`:

- queue writer emits one graph YAML into `pending/`
- graph must include implementation, review, and synthesis outputs
- final review JSON must be machine-readable and semantically `pass`
- repo must show commit evidence newer than task start
- only then may the graph route to `completed`
- otherwise it routes to `failed`

---

## Plan

### Phase 0 - Lock the delivery contract

1. Extend the planner response model in `task_planner.py` with `task_kind`, `delivery_mode`, `file_scope`, and `review_rounds`.
2. Update `prompts/task_planner.yaml` so the LLM uses the new fields consistently.
3. Add a deterministic validation layer in `task_planner.py` that rejects invalid combinations:
   - `delivery_mode=review_cycle` without `task_kind=code_change`
   - `delivery_mode=review_cycle` without `review_rounds`
   - `delivery_mode=flat` with `review_rounds`
4. Add unit tests for the planner contract.

### Phase 1 - Build one queue writer that supports both paths

1. Refactor task emission in `task_planner.py` into one internal writer interface:
   - `write_flat_task(...)`
   - `write_review_cycle_task(...)`
2. Keep the existing flat markdown format for `delivery_mode=flat`.
3. For `delivery_mode=review_cycle`, call into `launch_review_cycle` as a library function rather than shelling out.
4. Ensure graph ids, queue filenames, and planner lineage are deterministic and derived from the planner task id.
5. Preserve existing pending/active/completed/failed directories and supervisor behavior.

### Phase 2 - Make the review-cycle graph truthful as a gate

1. Extend `launch_review_cycle.py` so planner-generated graphs carry enough metadata for `run_task.py` to identify:
   - planner lineage
   - final review JSON path
   - target repo path
   - delivery contract (`review_cycle`)
2. Keep the one-round graph structure for this slice, but make the runtime inspect the final review JSON after graph execution.
3. In `run_task.py`, after a graph reports `completed`, read the final review JSON and fail the graph if:
   - the JSON file is missing
   - the JSON is invalid
   - `status != "pass"`
4. Record explicit decision provenance events for:
   - review semantic gate pass
   - review semantic gate fail

### Phase 3 - Add commit evidence to the graph path

1. Add graph-level post-run repo inspection in `run_task.py`.
2. Define commit evidence as: at least one new git commit in the target repo newer than task start time.
3. For planner-generated `review_cycle` tasks:
   - route to `completed` only when review gate passes and commit evidence exists
   - route to `failed` when review gate passes but commit evidence is absent
4. Record commit evidence fields in the graph report:
   - `commit_detected`
   - `commit_sha` when available
   - `commit_timestamp` when available
5. Record failure provenance explicitly when the graph produced artifacts but did not land a commit.

### Phase 4 - Tighten reporting and observability

1. Extend report schemas so both flat and graph reports can carry:
   - planner lineage
   - delivery mode
   - review gate outcome
   - commit evidence
2. Keep backward compatibility for old reports by making new fields additive.
3. Update README examples to show how planner-generated code tasks now flow through graph reports rather than only flat reports.

### Phase 5 - Prove the end-to-end slice on one safe planner-generated task

1. Generate planner output scoped to one safe repo with a bounded code task.
2. Confirm the planner emits `delivery_mode=review_cycle`.
3. Confirm queue writer writes a graph YAML to `pending/`.
4. Run the supervisor or direct runner on that graph.
5. Verify the graph:
   - enters `active/`
   - produces implementation/review/synthesis artifacts
   - records a `pass` review result
   - records commit evidence
   - routes to `completed/`
   - emits a graph report with all expected lineage and gate fields

### Phase 6 - Queue hygiene boundary for rollout

1. Add an audit-only command that classifies pending tasks by delivery-mode readiness:
   - planner-generated flat legacy tasks
   - planner-generated review-cycle-ready tasks
   - stale tasks
   - broken tasks
2. Do not rewrite historical queue items automatically.
3. Document the operational rule: only newly generated planner tasks participate in the new review-cycle delivery path until a separate migration plan exists.

---

## Required Tests

### New Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_task_planner_delivery_modes.py` | `test_generate_task_contract_rejects_invalid_delivery_mode_combo` | Planner contract rejects invalid field combinations |
| `tests/test_task_planner_delivery_modes.py` | `test_write_flat_task_keeps_existing_markdown_format` | Flat-task compatibility is preserved |
| `tests/test_task_planner_delivery_modes.py` | `test_write_review_cycle_task_emits_graph_yaml_with_deterministic_id` | Planner-generated review-cycle tasks become deterministic graph artifacts |
| `tests/test_launch_review_cycle_graph_contract.py` | `test_build_graph_includes_final_review_json_reference` | Graph generation exposes the final review artifact needed for gating |
| `tests/test_launch_review_cycle_graph_contract.py` | `test_build_graph_rounds_one_still_emits_review_and_synthesis_tasks` | One-round delivery graph still has the required review and synthesis stages |
| `tests/test_run_task_review_gate.py` | `test_graph_routes_to_failed_when_final_review_status_is_needs_changes` | Semantic review result gates acceptance |
| `tests/test_run_task_review_gate.py` | `test_graph_routes_to_failed_when_commit_missing_after_review_pass` | Review pass alone is not enough without commit evidence |
| `tests/test_run_task_review_gate.py` | `test_graph_routes_to_completed_when_review_pass_and_commit_present` | End-to-end graph acceptance path works |
| `tests/test_run_task_reports.py` | `test_graph_report_records_delivery_mode_review_gate_and_commit_evidence` | New graph report fields are emitted |
| `tests/test_run_task_reports.py` | `test_flat_report_records_planner_lineage_when_present` | Flat path keeps additive observability fields without breaking compatibility |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_run_task_postsuccess_recovery.py` | Existing bounded recovery logic must remain correct |

---

## Acceptance Criteria

- [ ] Planner schema includes explicit delivery contract fields and rejects invalid combinations
- [ ] Planner can emit both flat markdown tasks and review-cycle graph tasks through one deterministic writer path
- [ ] Code-changing planner output defaults to `delivery_mode=review_cycle`
- [ ] Review-cycle graphs are not accepted solely because all graph tasks executed; final review status must be `pass`
- [ ] Planner-generated review-cycle graphs are not accepted without commit evidence
- [ ] Graph reports record planner lineage, review-gate outcome, and commit evidence
- [ ] Flat reports remain valid and backward-compatible
- [ ] README documents the new planner -> review-cycle -> commit path truthfully
- [ ] New tests pass
- [ ] Existing recovery tests still pass
- [ ] One planner-generated safe code task completes end-to-end through `pending -> active -> completed` with review pass and commit evidence

---

## Failure Modes

| Failure | Detection | Mitigation |
|---------|-----------|------------|
| Planner emits wrong delivery mode for a code task | Generated task contract says `flat` for `task_kind=code_change` | Reject at planner validation layer before writing queue artifacts |
| Graph finishes but review did not really approve the work | Final review JSON exists but `status != pass` | Post-graph semantic gate in `run_task.py` routes to `failed` |
| Review passes but no commit landed | Repo has no new commit after graph run | Post-graph commit gate routes to `failed` and records explicit evidence |
| Planner-generated graph artifact is malformed or missing metadata | Queue writer emits graph without final review path or repo path | Graph build tests fail and queue writer rejects the artifact before enqueue |
| Report schema drift breaks older report consumers | Existing report readers reject new additive fields | Keep schema additions additive and verify old minimal reports still validate |

---

## Uncertainty Register

| ID | Uncertainty | Current Default | Why It Is Safe Enough To Proceed |
|----|-------------|-----------------|----------------------------------|
| U1 | Planner may misclassify some bounded tasks as `docs_only` vs `code_change` | Default to `code_change` whenever the task requires test changes, schema changes, CLI changes, or code edits | This biases toward the safer gated path |
| U2 | One review round may be insufficient for some repos | First rollout stays at one round and treats follow-up convergence as a separate optimization problem | The objective is truthful gating, not maximal autonomous convergence in this slice |
| U3 | Graph-level commit detection may be tricky for repos with unrelated concurrent commits | Detect commits in the task target repo and require commit timestamp newer than the task start timestamp | This is precise enough for the first bounded proof task |
| U4 | Final review artifact path may not be exposed cleanly from current graph metadata | Extend graph metadata explicitly rather than inferring it from filenames | Explicit metadata avoids fragile inference |
| U5 | Some docs-only tasks may still benefit from review-cycle graphs | Keep docs-only on the flat path unless there is a demonstrated need for graph review later | This contains scope and keeps the gate attached to code delivery first |
| U6 | Historical pending tasks may have ambiguous lineage fields | Leave legacy tasks untouched and apply the new contract only to newly planned tasks | This avoids queue migration risk during the proof slice |
| U7 | `launch_review_cycle.py` may contain more machinery than needed for planner-generated graphs | Reuse the existing builder first and simplify later only if the tests show unnecessary coupling | Reuse is lower risk than introducing a second graph definition now |
| U8 | The runtime may reach review pass but fail to create a commit due to repo policy or agent behavior | Treat that as a real failure, record it explicitly, and keep the graph out of `completed/` | The whole-system contract requires commit evidence |
