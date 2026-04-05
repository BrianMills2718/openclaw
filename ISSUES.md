# Issues

Observed problems, concerns, and technical debt. Items start as **unconfirmed**
observations and get triaged through investigation into confirmed issues, plans,
or dismissed.

**Last reviewed:** 2026-04-05

---

## Status Key

| Status | Meaning | Next Step |
|--------|---------|-----------|
| `unconfirmed` | Observed, needs investigation | Investigate to confirm/dismiss |
| `monitoring` | Confirmed concern, watching for signals | Watch for trigger conditions |
| `confirmed` | Real problem, needs a fix | Create a plan |
| `planned` | Has a plan (link to plan) | Implement |
| `resolved` | Fixed | Record resolution |
| `dismissed` | Investigated, not a real problem | Record reasoning |

---

## Unconfirmed

(Add observations here with enough context to investigate later)

## Monitoring

(Items confirmed as real but not yet urgent. Include trigger conditions.)

---

## Confirmed

(Items that need a fix but don't have a plan yet.)

---

## Planned

### ISSUE-001: Runtime Naming Drift Between Glossary And Runtime Repo

**Observed:** 2026-04-05
**Status:** `planned`
**Plan:** [Plan #5: Runtime Naming and Evaluation Convergence](docs/plans/05_runtime_naming_and_evaluation_convergence.md)

The canonical glossary in `project-meta` already distinguishes:
- generic category: `agent runtime / orchestration system`
- named runtime instance: `OpenClaw`
- current implementation repo: `moltbot`

But this repo still presents a mixed `Moltbot / OpenClaw` identity across
top-level docs. That keeps the runtime layer harder to reason about and makes
the repo look like the category, the brand, and the implementation all at once.

**What must be fixed:**
- repo-local docs must mirror the canonical runtime naming split exactly
- runtime docs must explain the difference between category, family, and repo
- terminology enforcement must catch this drift before merge

---

### ISSUE-002: Runtime Evaluation Verdict Is Not Converged Into Active Runtime Truth Surfaces

**Observed:** 2026-04-05
**Status:** `planned`
**Plan:** [Plan #5: Runtime Naming and Evaluation Convergence](docs/plans/05_runtime_naming_and_evaluation_convergence.md)

The runtime competitor work was done and the verdict is real: keep `moltbot`,
keep Junior as a pattern/customization reference, and treat NanoClaw as
disqualified for the governed coding-runtime proof. But that conclusion is only
partially visible from active runtime docs, and some `project-meta` plan
surfaces still point at non-existent non-archive paths for the underlying
recommendation/proof notes.

**What must be fixed:**
- runtime repo docs must link to a stable canonical recommendation surface
- active docs must not point at archived evidence through broken paths
- the current runtime repo should state which alternatives were evaluated and
  what the current verdict means operationally

---

## Resolved

| ID | Description | Resolution | Date |
|----|-------------|------------|------|
| - | - | - | - |

---

## Dismissed

| ID | Description | Why Dismissed | Date |
|----|-------------|---------------|------|
| - | - | - | - |

---

## How to Use This File

1. **Observe something off?** Add under Unconfirmed with context and investigation steps
2. **Investigating?** Update the entry with findings, move to appropriate status
3. **Confirmed and needs a fix?** Create a plan, link it, move to Confirmed/Planned
4. **Not actually a problem?** Move to Dismissed with reasoning
5. **Watching a concern?** Move to Monitoring with trigger conditions
