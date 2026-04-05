# Sprint — Plan #2: End-to-End Planner → Review → Commit Flow (2026-04-04)

doc_role: ops
mutable_facts_allowed: yes

**Status**: 🚧 IN PROGRESS
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
**Status**: 🔲 PENDING
**Pass when**: `TaskItem` has `task_kind`, `delivery_mode`, `file_scope`, `review_rounds`; validation rejects bad combos; unit tests pass

### Phase 1 — Queue writer (both paths)
**Status**: 🔲 PENDING
**Pass when**: `write_flat_task()` + `write_review_cycle_task()` both work; graph YAML has deterministic id from planner task id

### Phase 2 — Review gate in run_task.py
**Status**: 🔲 PENDING
**Pass when**: Post-graph semantic gate reads review JSON, fails graph if `status != "pass"` or JSON missing/invalid

### Phase 3 — Commit evidence
**Status**: 🔲 PENDING
**Pass when**: Post-graph commit detection inspects repo; routes to failed if commit absent for planner review_cycle tasks

### Phase 4 — Report schema tightening
**Status**: 🔲 PENDING
**Pass when**: Graph reports carry `delivery_mode`, `review_gate_outcome`, `commit_detected`, `planner_lineage`; backward compatible

### Phase 5 — Dry-run proof
**Status**: 🔲 PENDING
**Pass when**: `task_planner.py --dry-run` on a code task produces review_cycle delivery_mode; `build_graph()` produces valid graph YAML that loads

### Phase 6 — Queue hygiene audit command
**Status**: 🔲 PENDING
**Pass when**: `python task_planner.py --audit-queue` classifies pending tasks by delivery-mode readiness

---

## Progress Log

| Time | Phase | What |
|------|-------|------|
| 2026-04-04 | setup | Sprint tracker created; worktree created |

---

## Open Uncertainties

| ID | Uncertainty | Current State |
|----|-------------|---------------|
| U1 | Planner classification accuracy for `task_kind` | Will validate in Phase 5 dry-run |
| U3 | Commit detection from task start time | Using `_agent_committed()` as base — will extend with start-time comparison |
| U4 | Graph metadata exposes final review JSON path | Will add explicit `planner_metadata` block to graph YAML |
