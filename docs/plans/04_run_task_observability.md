# Plan #4: run_task.py Observability and Cost Tracking

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None (Phase 6.3 concurrent or following)
**Blocks:** Phase 6.5 (governance effectiveness audit)
**Date:** 2026-04-04

**Done when:**
1. `make cost` shows per-task LLM spend without requiring manual SQL queries
2. `make errors` shows recent task failures with reason, gate outcome, and cost
3. `make summary` shows task success rate, review gate pass rate, and commit rate for the last 7 days

**Open uncertainties:**
- Whether `llm_client`'s observability DB is queryable from moltbot (requires `OPENCLAW_OBSERVABILITY_DB` env or shared path convention)
- Whether Codex sub-agent cost is attributable to the parent moltbot task (depends on trace_id threading)
- Cost-by-task may require `task=` kwarg to be threaded through all `llm_client` calls in `run_task.py` — not verified

---

## Gap

After Phase 6.3, we need <30 min/day dashboard oversight (Phase 6 gate). Currently:
- Task success rate requires manual inspection of `reports/` JSON files
- Review gate pass rate requires `make review-gate-log` + mental math
- LLM cost per task is not surfaced without SQL
- No standard `make cost` / `make errors` / `make summary` targets

This plan wires moltbot into the standard make target glossary defined in the root CLAUDE.md.

---

## Pre-Made Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cost source | `llm_client` observability DB (`~/projects/data/llm_observability.db`) | Already tracks per-call cost with task= kwarg |
| Task attribution | Filter by `project="moltbot"` in observability queries | Consistent with root CLAUDE.md cost target convention |
| Summary data source | `reports/` JSON files (scan + aggregate) | No additional infrastructure needed |
| Target names | `cost`, `errors`, `summary` | Standard make glossary from CLAUDE.md |
| Review gate summary | Delegate to `scripts/review_gate_log.py` | Already implemented in Plan #3 Phase 1 |

---

## Acceptance Criteria

| Criterion | Done? |
|-----------|-------|
| `make cost DAYS=7` shows LLM spend per task in the last 7 days | ⬜ |
| `make errors DAYS=7` shows recent failures with gate outcome and failure reason | ⬜ |
| `make summary` shows: total tasks dispatched, completed, failed, review gate pass rate, commit rate | ⬜ |
| All three targets work from `~/projects/moltbot/` without manual SQL | ⬜ |

---

## Failure Modes

| Failure | Detect | Fix |
|---------|--------|-----|
| Cost query returns 0 rows | `make cost` output empty | Verify `task="moltbot"` kwarg is set on llm_client calls in run_task.py |
| Trace IDs not threaded to sub-agent calls | Cost shows moltbot orchestration only, not Codex runs | Thread trace_id into spawning prompt; verify in observability DB |
| Reports dir doesn't exist yet | `make summary` errors | Add `REPORTS_DIR.mkdir()` guard in script |

---

## Plan

### Steps

| Step | What | Status |
|------|------|--------|
| 1 | Audit `run_task.py` — verify `task=` kwarg is set on all llm_client calls | Not started |
| 2 | Write `scripts/task_summary.py` — scan reports/, aggregate success/fail/gate/commit rates | Not started |
| 3 | Write `scripts/task_cost.py` — query llm_observability.db filtered by project=moltbot | Not started |
| 4 | Add `cost`, `errors`, `summary` targets to Makefile | Not started |
| 5 | Verify all three work on real data after ≥1 completed cycle | Not started |
