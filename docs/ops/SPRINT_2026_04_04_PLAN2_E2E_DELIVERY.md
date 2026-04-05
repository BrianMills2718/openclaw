# Sprint — Plan #2: End-to-End Planner → Review → Commit Flow (2026-04-04)

doc_role: ops
mutable_facts_allowed: yes

**Status**: ✅ COMPLETE
**Started**: 2026-04-04 (evening)

**Operator instruction**: NEVER STOP. Execute all phases. Commit every verified slice.
Work in worktrees. Small trivial changes may go direct to main.

**Sprint source plan**: `docs/plans/02_end_to_end_planner_review_commit_flow.md`
**Worktree**: `~/projects/moltbot_worktrees/plan-2-e2e-delivery` (branch: `plan-2-e2e-delivery`)

---

## Mission

Wire the full autonomous code-delivery pipeline:
planner → queue → review-cycle graph → semantic review gate → commit evidence → completed

---

## Acceptance Criteria

- [ ] Planner schema includes `task_kind`, `delivery_mode`, `file_scope`, `review_rounds`; rejects invalid combos
- [ ] Planner can emit flat markdown tasks OR review-cycle graph YAMLs through one writer path
- [ ] Code-changing planner output defaults to `delivery_mode=review_cycle`
- [ ] Review-cycle graphs NOT accepted solely on graph execution status — final review JSON `status == "pass"` required
- [ ] Planner-generated review-cycle graphs NOT accepted without commit evidence
- [ ] Graph reports record planner lineage, review-gate outcome, commit evidence
- [ ] Flat reports remain valid and backward-compatible
- [ ] README documents the new delivery path
- [ ] New tests pass (10 tests across 4 test files)
- [ ] Existing recovery tests still pass (6 tests)
- [ ] Phase 5 dry-run: planner emits review_cycle for code task; queue writer produces graph YAML; graph loads cleanly

---

## Phase Stack

### Phase 0 — Lock delivery contract
**Status**: ✅ COMPLETE
`TaskItem` extended with `task_kind`, `delivery_mode`, `file_scope`, `review_rounds`; `validate_task_delivery_contract()` rejects 5 invalid combos; 8 unit tests pass

### Phase 1 — Queue writer (both paths)
**Status**: ✅ COMPLETE
`write_flat_task()` + `write_review_cycle_task()` + `write_task_file()` router; graph YAML has deterministic id + planner_metadata; 9 unit tests pass

### Phase 2 — Review gate in run_task.py
**Status**: ✅ COMPLETE
`_check_review_gate()` reads final review JSON, fails on missing/invalid/needs_changes; wired into `_run_graph_task()` after graph execution; 6 unit tests pass

### Phase 3 — Commit evidence
**Status**: ✅ COMPLETE
`_check_commit_evidence()` inspects target repo for new commits since task start; routes to failed if absent; 4 unit tests pass

### Phase 4 — Report schema tightening
**Status**: ✅ COMPLETE
Graph reports carry `planner_lineage`, `review_gate`, `commit_evidence`; flat reports remain backward-compatible; 5 unit tests pass

### Phase 5 — Dry-run proof
**Status**: ✅ COMPLETE
Dry-run smoke test: planner emits `delivery_mode=review_cycle`, graph YAML loads with 5 tasks (context_init/implement_r1/review_r1/context_update_r1/synthesize), planner_metadata correct

### Phase 6 — Queue hygiene audit command
**Status**: ✅ COMPLETE
`python task_planner.py --audit-queue` classifies pending tasks into 4 categories: review_cycle_ready, flat_legacy, stale, broken

---

## Progress Log

| Time | Phase | What |
|------|-------|------|
| 2026-04-04 | setup | Sprint tracker created; worktree created |
| 2026-04-04 | 0+1 | TaskItem extended; validate_task_delivery_contract(); write_flat_task/write_review_cycle_task/write_task_file router; prompt updated |
| 2026-04-04 | 2+3 | _check_review_gate(); _check_commit_evidence(); _load_graph_yaml_raw(); wired into _run_graph_task() |
| 2026-04-04 | 4 | planner_lineage/review_gate/commit_evidence in graph reports; backward-compat flat reports |
| 2026-04-04 | 5 | Dry-run smoke test PASS — 5-task graph YAML with correct planner_metadata |
| 2026-04-04 | 6 | audit_queue() + --audit-queue CLI flag |
| 2026-04-04 | done | 38/38 tests pass; README updated; sync_plan_status fix committed |

---

## Open Uncertainties

| ID | Uncertainty | Current State |
|----|-------------|---------------|
| U1 | Planner classification accuracy for `task_kind` | Will validate in Phase 5 dry-run |
| U3 | Commit detection from task start time | Using `_agent_committed()` as base — will extend with start-time comparison |
| U4 | Graph metadata exposes final review JSON path | Will add explicit `planner_metadata` block to graph YAML |
