# Round 1 Implementation

Changed files:
- `run_task.py`
- `schemas/graph_task_report.schema.json`
- `tests/test_run_task_reports.py`
- `.openclaw/review-cycles/planner-2026-04-05-add-failing-task-wave-to-report-triage/round_1/implementation.md`

Tests run:
- `python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py`
- `python -m pytest -q tests/test_run_task_delivery_audit.py`

Residual risks:
- `run.failing_task_waves` currently treats only task summaries with `status == "failed"` as failing waves. If the graph runtime later introduces another terminal non-success status that should count toward wave triage, the helper will need a deliberate widening.
- The new triage section is intentionally minimal for this round and only reports count plus wave indices; it does not yet explain why a wave failed.

Commit sha:
- `242b0ed`
