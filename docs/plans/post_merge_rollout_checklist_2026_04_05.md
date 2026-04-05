# Post-Merge Rollout Checklist - 2026-04-05

**Purpose:** Merge the proven Plan #2 work in the correct dependency order, rerun the minimum truthful verification on mainline branches, and start the first post-merge non-doc proof target without ambiguity.

## Branches

- `llm_client`: `codex/codex-transport-fallback`
- `openclaw`: `codex/e2e-planner-review-commit`

## Merge Order

1. Merge `llm_client` first.
   Why:
   - `openclaw` proof runs now depend on `llm_client` commit `44201fd`
   - that commit isolates Codex home by default so broken global MCP config does not leak into autonomous runs
2. Merge `openclaw` second.
   Why:
   - the runtime import-precedence fix and CLI-default policy assume the shared `llm_client` behavior above

## PRs

- `llm_client`: `https://github.com/BrianMills2718/llm_client/pull/new/codex/codex-transport-fallback`
- `openclaw`: `https://github.com/BrianMills2718/openclaw/pull/new/codex/e2e-planner-review-commit`

## Mainline Verification

### Step 1 - Update mainline checkouts

1. In the canonical `llm_client` checkout, merge the approved branch and pull latest `main`.
2. In the canonical `openclaw` checkout, merge the approved branch and pull latest `main`.

### Step 2 - Verify shared dependency first

Run in `llm_client` mainline checkout:

```bash
python -m pytest -q tests/test_agents.py -k codex_mcp
```

Pass condition:
- all selected tests pass

### Step 3 - Verify openclaw runtime contract

Run in `openclaw` mainline checkout:

```bash
python -m pytest -q tests/test_runtime_bootstrap_imports.py tests/test_run_task_delivery_audit.py tests/test_run_task_reports.py tests/test_task_planner_delivery_modes.py
```

Pass condition:
- all selected tests pass

### Step 4 - Reconfirm the proven real-run artifact

Reference proof report:

- `/tmp/openclaw-proof-readme-fresh/reports/planner-2026-04-05-document-cli-default-readme_20260405T053153Z.json`

Truth conditions to confirm:
- `status = completed`
- `review_gate.passed = true`
- `commit_evidence.passed = true`

## First Post-Merge Non-Doc Proof Target

Target plan:
- [Plan #3: Graph Report Task-Result Observability](03_graph_report_task_result_observability.md)

Reason this is next:
- Plan #2 still relied on `OPENCLAW_DEBUG_RUNTIME_PROVENANCE` to inspect per-task graph failures cleanly
- operator-facing reports still summarize the graph outcome more than they expose task-level failure detail
- the next code proof should improve the runtime’s normal observability surface, not another doc-only slice

## Start Condition For Plan #3

Only start after:
- `llm_client` merge verification is green
- `openclaw` merge verification is green

## Plan #3 Kickoff Commands

```bash
python -m pytest -q tests/test_run_task_reports.py tests/test_run_task_review_gate.py
```

Then implement the additive report contract in Plan #3 and prove it with one fresh planner-generated code task.
