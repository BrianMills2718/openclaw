# Implementation Plans

Track all implementation work here.

## Gap Summary

| # | Name | Priority | Status | Blocks |
|---|------|----------|--------|--------|
| 1 | [Example Plan](01_example.md) | Medium | 📋 Planned | - |
| 2 | [End-to-End Planner -> Review -> Commit Flow](02_end_to_end_planner_review_commit_flow.md) | High | 🚧 In Progress | - |

## Active Execution Tracker

- [24-Hour Runtime Sprint](24h_runtime_execution_sprint_2026_04_04.md)
- [24-Hour Runtime Sprint](24h_runtime_execution_sprint_2026_04_05.md)

## Status Key

| Status | Meaning |
|--------|---------|
| `📋 Planned` | Ready to implement |
| `🚧 In Progress` | Being worked on |
| `⏸️ Blocked` | Waiting on dependency |
| `✅ Complete` | Implemented and verified |

## Creating a New Plan

1. Copy `TEMPLATE.md` to `NN_name.md`
2. Fill in gap, steps, required tests
3. Add to this index
4. Commit with `[Plan #N]` prefix

## Trivial Changes

Not everything needs a plan. Use `[Trivial]` for:
- Less than 20 lines changed
- No changes to `src/` (production code)
- No new files created

```bash
git commit -m "[Trivial] Fix typo in README"
```

## Completing Plans

```bash
python scripts/meta/complete_plan.py --plan N
```

This verifies tests pass and records completion evidence.
