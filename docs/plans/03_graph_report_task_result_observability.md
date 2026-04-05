# Plan #3: Graph Report Task-Result Observability

**Status:** Planned
**Type:** implementation
**Priority:** High
**Blocked By:** Merge of Plan #2 branches into canonical `llm_client` and `openclaw`
**Blocks:** Faster diagnosis of post-merge runtime failures without ad hoc provenance files

---

## Gap

**Current:** Graph-task reports surface overall run status, review-gate outcome, and commit evidence, but they do not expose a compact task-by-task execution record. During Plan #2, debugging the real runner path required `OPENCLAW_DEBUG_RUNTIME_PROVENANCE` to inspect which task failed, what error it carried, whether validators passed, and which model/runtime path actually ran.

**Target:** Make normal graph reports sufficient for first-line diagnosis.

1. Graph reports include additive `task_results` summaries for each graph task
2. Each task summary includes enough information to diagnose failure without the debug provenance sidecar
3. Report payload stays bounded and operator-readable
4. Schema remains backward-compatible
5. One planner-generated non-doc code task proves the new report contract on the real script-entrypoint path

**Why:** Plan #2 proved the delivery path, but the next weakest seam is observability. If the next code proof fails, operators should not have to enable a bespoke provenance file to understand which task failed and why.

---

## References Reviewed

- `run_task.py`
- `schemas/graph_task_report.schema.json`
- `tests/test_run_task_reports.py`
- `tests/test_run_task_review_gate.py`
- `docs/plans/02_end_to_end_planner_review_commit_flow.md`
- `docs/plans/24h_runtime_execution_sprint_2026_04_05.md`

---

## Files Affected

- `run_task.py` (modify)
- `schemas/graph_task_report.schema.json` (modify)
- `README.md` (modify if operator-facing report contract changes materially)
- `tests/test_run_task_reports.py` (modify)
- `tests/test_run_task_review_gate.py` (modify if needed)
- `docs/plans/03_graph_report_task_result_observability.md` (create)
- `docs/plans/CLAUDE.md` (modify)

---

## Pre-Made Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Report field name | `task_results` | Matches existing internal terminology and report payload shape |
| Compatibility | Additive only | Existing reports and consumers must remain valid |
| Per-task payload | Include compact summaries, not full agent output | Operator reports should aid diagnosis without ballooning into transcript dumps |
| Included fields | `task_id`, `status`, `wave`, `model_selected`, `requested_model`, `resolved_model`, `duration_s`, `error`, `validation_summary` | This is the minimum set that explained Plan #2 failures |
| Validation shape | Collapse validator results into compact summaries | Full validator payloads belong in deep debug artifacts, not every normal report |
| Provenance sidecar | Keep optional `OPENCLAW_DEBUG_RUNTIME_PROVENANCE` support | It remains useful for deep incidents, but should not be required for first-pass diagnosis |
| Proof target type | Code-changing planner-generated graph, not docs-only | The next proof must exercise the reviewed delivery lane on a real non-doc change |

---

## Acceptance Criteria

- Graph report JSON includes a top-level `task_results` array for graph tasks
- Each task result summary carries the agreed compact fields
- A failed graph report shows the failing task and its error directly in the report
- A completed graph report shows all task statuses directly in the report
- Schema validation passes for updated reports
- Existing graph-report and review-gate tests pass
- One fresh planner-generated code task completes through the real `python run_task.py <graph>` path and emits the new task-level report data

---

## Plan

### Phase 0 - Lock the report contract

1. Define the compact `task_results` report shape in `schemas/graph_task_report.schema.json`
2. Decide which validator information is summarized into `validation_summary`
3. Add or update tests that assert the field is present on both success and failure paths

### Phase 1 - Implement report serialization

1. Add a report-only serializer in `run_task.py` that converts internal graph task results into bounded summaries
2. Attach those summaries to the graph report payload before writing the report
3. Keep debug provenance separate and optional

### Phase 2 - Verify failure-path usefulness

1. Extend a failing graph-path test so the report records the failing task id and error
2. Extend a passing graph-path test so the report records all task statuses

### Phase 3 - Real proof on a non-doc code task

1. Generate one fresh planner-produced code task
2. Run it through the real script entrypoint
3. Confirm the final graph report includes task-level summaries in addition to review and commit gates

---

## Required Tests

- `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`
- existing targeted runtime suite from Plan #2 remains green

---

## Completion Evidence

Plan #3 is complete only when:

- the code and schema are committed
- the targeted tests pass
- one fresh planner-generated non-doc code proof report contains the new `task_results` summaries
