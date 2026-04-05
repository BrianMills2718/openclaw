# Plan #3: Phase 6.3 Autonomous Daily Cycle

**Status:** Planned
**Priority:** High
**Blocked By:** Phase 6.2 (≥7/10 useful tasks dispatched and confirmed)
**Blocks:** Phase 6.4 (7-day sustained run)
**Date:** 2026-04-04

**Done when:**
1. The 6am cron fires daily and completes `recommender → moltbot dispatch → review gate → commit` without manual intervention
2. 3 consecutive calendar days each produce ≥1 commit in a target repo that passes the review gate
3. Each cycle's outcome is visible in `make review-gate-log` without manual querying

**Open uncertainties:**
- Whether `task_planner.py` needs changes to generate valid `code_change`/`review_cycle` tasks reliably without human prompting
- Whether the recommender's top tasks will consistently hit `code_change` (vs `docs_only` or `analysis_only`) at the required frequency
- Cron environment variable availability (OPENCLAW_TASKS_DIR etc.) has not been dry-run tested

---

## Gap

Phase 6.2 proved the pipeline works for manually-triggered tasks. Phase 6.3 requires the
full cycle to run autonomously on a fixed schedule: cron triggers recommender, recommender
writes tasks, moltbot picks them up, executes, gates on review, commits.

The current state: cron is wired (`0 6 * * *`), but end-to-end autonomous proof run has
not been completed. Human approval is NOT in the critical path (moltbot Plan #2 removed it).

---

## Pre-Made Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Task source | ecosystem-ops recommender (`python ~/projects/ecosystem-ops/recommender.py`) | Already integrated; generates ranked task list |
| Cycle trigger | 6am PDT daily cron | Fixed in place 2026-04-04 |
| Review gate | `_check_review_gate()` + `_check_commit_evidence()` in `run_task.py` | Already implemented (Plan #2) |
| Success metric | ≥1 review-cycle task commits per day for 3 days | Phase 6.3 gate definition from ROADMAP |
| Observability | `make review-gate-log` renders outcome table | Implemented (Plan #3 Phase 1) |
| Backlog minimum | ≥3 high-priority non-duplicate tasks/day from recommender | If backlog is thin, task quality degrades before quantity |

---

## Acceptance Criteria

| Criterion | Done? |
|-----------|-------|
| Cron fires at 6am and completes full cycle without manual trigger | ⬜ |
| 3 consecutive days each produce ≥1 committed task | ⬜ |
| `make review-gate-log` shows 3+ completed review-cycle tasks with commit evidence | ⬜ |
| No human approval step in the critical path (verify by reading cron log) | ⬜ |
| Recommender backlog stays ≥3 non-duplicate high-priority tasks after each dispatch | ⬜ |

---

## Failure Modes

| Failure | Detect | Fix |
|---------|--------|-----|
| Cron fires but recommender returns empty list | `make review-gate-log` shows 0 tasks in window | Expand recommender scope or lower priority threshold |
| Tasks dispatched but none are `code_change` | Gate log shows 0 review-cycle tasks | Tune recommender weights to surface more `code_change` work |
| Review gate passes but no commit detected | Log shows `commit_detected: false` | Check workspace_dir path; verify Codex committed before timeout |
| Cron env vars missing (OPENCLAW_TASKS_DIR etc.) | Tasks written to wrong path | Add env exports to cron entry |

---

## Plan

### Steps

| Step | What | Status |
|------|------|--------|
| 1 | Verify cron entry includes required env vars and correct path to recommender | Not started |
| 2 | Dry-run: manually invoke cron script and confirm tasks appear in `~/.openclaw/tasks/pending/` | Not started |
| 3 | Monitor first autonomous 6am cycle; check `make review-gate-log` output | Not started |
| 4 | Repeat for 3 days; confirm ≥1 committed review-cycle task per day | Not started |
| 5 | Document cron log location and monitoring workflow in `KNOWLEDGE.md` | Not started |
