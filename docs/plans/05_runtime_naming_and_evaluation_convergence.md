# Plan #5: Runtime Naming and Evaluation Convergence

**Status:** Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Truthful runtime glossary adoption and future runtime-replacement decisions

---

## Gap

**Current:** The cross-project runtime evaluation lane already made two
important decisions:

1. naming:
   - generic category = `agent runtime / orchestration system`
   - named runtime instance/family = `OpenClaw`
   - current implementation repo = `moltbot`
2. evaluation verdict:
   - keep `moltbot` as the current implementation
   - keep Junior as the strongest customization/pattern reference
   - treat NanoClaw as disqualified for the governed coding-runtime proof

But this repo does not expose those conclusions cleanly. Top-level runtime docs
still mix `moltbot` and `OpenClaw` in ways that blur repo vs family vs
category, and the supporting evaluation evidence is not reachable through one
stable active truth surface.

**Target:** Make runtime naming and runtime-evaluation truth converge in the
runtime repo and the linked cross-project docs, with enforcement strong enough
to stop the same drift from recurring.

**Why:** Without this, the ecosystem keeps paying the same tax:
- people have to re-ask what `moltbot` means
- OpenClaw branding keeps leaking into category language
- competitor research looks lost even though it already produced a verdict
- future runtime debates restart from confusion instead of evidence

---

## Research

- `~/projects/project-meta/vision/06_GLOSSARY.md`
- `~/projects/project-meta/docs/ops/AGENT_RUNTIME_GUARDRAIL_LANDSCAPE_2026-04-02.md`
- `~/projects/project-meta/docs/plans/57_runtime-implementation-evaluation-lane.md`
- `~/projects/project-meta/docs/plans/70_runtime-empirical-proof.md`
- `~/projects/project-meta/docs/plans/71_runtime-empirical-proof-24h-sprint.md`
- `~/projects/project-meta/docs/ops/archive/sprint_trackers/RUNTIME_IMPLEMENTATION_EVALUATION_RECOMMENDATION_2026-04-02.md`
- `~/projects/project-meta/docs/ops/archive/sprint_trackers/RUNTIME_IMPLEMENTATION_PROOF_JUNIOR_2026-04-02.md`
- `~/projects/project-meta/docs/ops/archive/sprint_trackers/RUNTIME_IMPLEMENTATION_PROOF_NANOCLAW_2026-04-02.md`
- `README.md`
- `CLAUDE.md`
- `ISSUES.md`
- `~/projects/investigations/cross-project/2026-04-05-runtime-naming-and-research-incorporation.md`

---

## Files Affected

- `README.md` (modify)
- `CLAUDE.md` (modify)
- `ISSUES.md` (modify)
- `docs/plans/05_runtime_naming_and_evaluation_convergence.md` (create)
- `docs/plans/CLAUDE.md` (modify)
- `KNOWLEDGE.md` (modify)
- `~/projects/project-meta/docs/plans/57_runtime-implementation-evaluation-lane.md` (future modify)
- `~/projects/project-meta/docs/plans/70_runtime-empirical-proof.md` (future modify)
- `~/projects/project-meta/docs/plans/71_runtime-empirical-proof-24h-sprint.md` (future modify)
- `~/projects/project-meta/docs/ops/AGENT_RUNTIME_GUARDRAIL_LANDSCAPE_2026-04-02.md` (future modify)
- `~/projects/project-meta/docs/ops/AGENT_PLATFORM_TERMINOLOGY_GLOSSARY.md` (only if redirect handling changes)
- `~/projects/project-meta/scripts/check_terminology.py` or a sibling runtime-naming checker (future modify)

---

## Pre-Made Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Generic runtime label | `agent runtime / orchestration system` | Already settled by the canonical glossary. |
| Runtime family / brand label | `OpenClaw` | Keeps the upstream family name distinct from the repo and category. |
| Current repo label | `moltbot` | This is the current implementation repo name; do not hide or rewrite it. |
| Runtime verdict | Keep `moltbot` as the current implementation | Already settled by the evaluation lane. |
| Alternative summary | Junior = strongest pattern/customization reference; NanoClaw = disqualified for the governed proof; other candidates remain secondary references | Preserve the actual evaluation outcome instead of reopening the survey. |
| Evidence surfacing model | Provide one stable active pointer plus archived primary evidence | Prevent future broken references while keeping detailed proof notes archived. |
| Enforcement model | Deterministic lint/check, not memory or review culture | Naming drift must fail before merge, not be rediscovered later. |

---

## Plan

### Steps

| Step | What | Status |
|------|------|--------|
| 1 | Converge runtime repo docs on the canonical naming split | Planned |
| 2 | Surface the runtime evaluation verdict and candidate outcomes in one stable active location | Planned |
| 3 | Repair active cross-project references so archived runtime proof notes still resolve truthfully | Planned |
| 4 | Extend terminology enforcement to catch runtime naming/category drift | Planned |
| 5 | Prove the enforcement with tests or deterministic check coverage | Planned |

### Step 1: Runtime repo naming convergence

| Sub-step | What | Status |
|----------|------|--------|
| 1a | Rewrite the opening sections of `README.md` and `CLAUDE.md` so they distinguish category, family, and repo explicitly | Planned |
| 1b | Remove mixed identity phrases like `Moltbot / OpenClaw` where they collapse distinct concepts | Planned |
| 1c | Add a short runtime identity section explaining `moltbot` vs `OpenClaw` vs the generic category | Planned |

### Step 2: Runtime evaluation convergence

| Sub-step | What | Status |
|----------|------|--------|
| 2a | Add a stable runtime-evaluation summary pointer from the runtime repo | Planned |
| 2b | Summarize evaluated alternatives and current verdict in the runtime repo docs | Planned |
| 2c | State which candidate patterns remain worth borrowing so future work starts from evidence | Planned |

### Step 3: Active reference repair

| Sub-step | What | Status |
|----------|------|--------|
| 3a | Identify every active `project-meta` doc that points at moved runtime evaluation/proof notes | Planned |
| 3b | Replace broken active paths with stable active paths, redirect stubs, or explicit archive links | Planned |
| 3c | Make the recommendation note discoverable without requiring archive spelunking | Planned |

### Step 4: Enforcement

| Sub-step | What | Status |
|----------|------|--------|
| 4a | Determine whether `check_terminology.py` can enforce this directly or needs a dedicated runtime-naming rule | Planned |
| 4b | Add deterministic checks for category/family/repo misuse on active runtime docs | Planned |
| 4c | Wire the check into the existing enforcement path | Planned |

### Step 5: Verification

| Sub-step | What | Status |
|----------|------|--------|
| 5a | Add tests or fixtures proving the runtime naming drift now fails loud | Planned |
| 5b | Verify active runtime docs and plan refs pass the new checks | Planned |
| 5c | Record the convergence outcome in `KNOWLEDGE.md` and close linked issues | Planned |

---

## Acceptance Criteria

- [ ] `README.md` and `CLAUDE.md` describe `moltbot`, `OpenClaw`, and the generic runtime category without collapsing them
- [ ] The runtime repo exposes the current evaluation verdict and candidate outcomes through one stable canonical pointer
- [ ] Active `project-meta` docs no longer point at non-existent runtime recommendation/proof paths
- [ ] A deterministic enforcement check fails when runtime docs misuse category, family, and repo labels
- [ ] The enforcement check is wired into the normal doc/governance validation path
- [ ] At least one test or deterministic fixture proves the new enforcement behavior

---

## Failure Modes

| Failure | How to detect | How to fix |
|---------|--------------|-----------|
| Naming cleanup turns into repo renaming | docs start proposing new repo names instead of clarifying current ones | keep this plan strictly about terminology convergence, not rename execution |
| Competitor research gets re-opened instead of summarized | new docs restart broad framework surveys | keep the candidate verdict fixed unless a new explicit evaluation plan reopens it |
| Broken links are hidden by archive moves again | active docs point at historical notes through paths that no longer exist | add stable redirect stubs or active summary notes rather than direct fragile links |
| Enforcement remains advisory | docs drift again but checks still pass | add deterministic failures for the specific runtime naming misuse patterns |

---

## Notes

This plan is intentionally about truth-surface convergence, not runtime feature
implementation. The runtime-evaluation work already happened; the missing work
is to make the decision easy to find, easy to state correctly, and hard to
drift away from.
