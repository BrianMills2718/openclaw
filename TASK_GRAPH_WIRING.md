# OpenClaw Task Graph Wiring Spec

**Date**: 2026-02-16
**Status**: Design — not yet implemented
**Depends on**: `llm_client` Phase 1 (task_graph.py, validators.py, difficulty.py, analyzer.py) — all committed and pushed.

## Overview

This document specifies how `run_task.py` (the OpenClaw task runner at `~/.openclaw/bin/run_task.py`) evolves to support YAML task graphs via `llm_client.task_graph`. The new system runs alongside the existing flat-task format — no breaking changes.

## 1. Task Format Detection

`run_task.py` currently only handles `.md` files with YAML frontmatter. It needs to handle two formats:

| Extension | Format | Handler |
|-----------|--------|---------|
| `.md` | Flat task (existing) | `TaskSpec.from_file()` → `_execute_task()` |
| `.yaml` | Task graph DAG | `load_graph()` → `run_graph()` |

### Changes to `run_task.py`

```python
from llm_client.task_graph import load_graph, run_graph, ExecutionReport
from llm_client.analyzer import analyze_run

async def run_task(task_path: Path) -> bool:
    """Main entry — dispatches to flat or graph handler based on extension."""
    if task_path.suffix in (".yaml", ".yml"):
        return await _run_graph_task(task_path)
    else:
        return await _run_flat_task(task_path)  # existing logic, renamed
```

The existing `run_task()` function becomes `_run_flat_task()`. No other changes to the flat-task path.

### `_run_graph_task()` — new function (~60 lines)

```python
async def _run_graph_task(task_path: Path) -> bool:
    """Execute a YAML task graph."""
    # Budget check (same as flat tasks)
    budget_ok, spent_today = _check_daily_budget()
    if not budget_ok:
        log.warning("Daily budget exceeded ($%.2f of $%.2f). Skipping.",
                     spent_today, DAILY_BUDGET_USD)
        return False

    graph = load_graph(task_path)
    log.info("=== Running task graph: %s (%d tasks, %d waves) ===",
             graph.meta.id, len(graph.tasks), len(graph.waves))

    # Move to active
    active_path = _move_task(task_path, "active")

    # Load MCP server configs from registry
    mcp_configs = _load_mcp_registry()

    # Execute
    report = await run_graph(
        graph,
        mcp_server_configs=mcp_configs,
        experiment_log=EXPERIMENT_LOG,
    )

    # Log costs to OpenClaw cost_log (existing format)
    for tr in report.task_results:
        _log_cost_from_task_result(tr, graph.meta.id)

    # Run self-improvement analyzer
    analysis = analyze_run(
        report,
        experiment_log=EXPERIMENT_LOG,
        proposals_log=PROPOSALS_LOG,
        floors_path=FLOORS_PATH,
    )
    if analysis.proposals:
        log.info("%d improvement proposals generated", len(analysis.proposals))

    # Archive
    destination = "completed" if report.status == "completed" else "failed"
    _move_task(active_path, destination)

    log.info("=== Graph %s: %s (cost=$%.4f, duration=%.1fs) ===",
             report.status.upper(), graph.meta.id,
             report.total_cost_usd, report.total_duration_s)

    return report.status == "completed"
```

### New constants

```python
EXPERIMENT_LOG = Path(os.environ.get(
    "OPENCLAW_EXPERIMENT_LOG",
    Path.home() / "projects" / "data" / "task_graph" / "experiments.jsonl",
))
PROPOSALS_LOG = Path(os.environ.get(
    "OPENCLAW_PROPOSALS_LOG",
    Path.home() / "projects" / "data" / "task_graph" / "proposals.jsonl",
))
FLOORS_PATH = Path(os.environ.get(
    "OPENCLAW_MODEL_FLOORS",
    Path.home() / "projects" / "data" / "task_graph" / "model_floors.json",
))
```

## 2. MCP Server Config Registry

`run_graph()` expects `mcp_server_configs: dict[str, dict[str, Any]]` — a dict mapping server names to `{command, args, env?, cwd?}`. This matches the format both Codex SDK and Claude Agent SDK expect.

### Source: `~/.codex/config.toml`

The existing Codex config already has all 18 MCP servers defined. Example entry:

```toml
[[mcp_servers]]
name = "digimon-kgrag"
command = "/home/brian/projects/Digimon_for_KG_application/.venv/bin/python"
args = ["-u", "/home/brian/projects/Digimon_for_KG_application/digimon_mcp_stdio_server.py"]
cwd = "/home/brian/projects/Digimon_for_KG_application"
env = { PYTHONPATH = "/home/brian/projects/Digimon_for_KG_application" }
```

### Registry file: `~/.openclaw/mcp_registry.toml`

Rather than re-parsing `~/.codex/config.toml` (which is Codex's config and may diverge), create a dedicated registry that `run_task.py` reads. Same TOML format, just the MCP entries:

```toml
# ~/.openclaw/mcp_registry.toml
# MCP server configs for the task graph runner.
# Each entry maps a server name to its startup command.
# Paths use ~ — expanded at load time.

[[servers]]
name = "digimon-kgrag"
command = "~/projects/Digimon_for_KG_application/.venv/bin/python"
args = ["-u", "~/projects/Digimon_for_KG_application/digimon_mcp_stdio_server.py"]
cwd = "~/projects/Digimon_for_KG_application"
env = { PYTHONPATH = "~/projects/Digimon_for_KG_application" }

[[servers]]
name = "sam-gov-government"
command = "~/projects/sam_gov/.venv/bin/python"
args = ["-u", "~/projects/sam_gov/integrations/mcp/government_mcp.py"]
cwd = "~/projects/sam_gov"

[[servers]]
name = "sam-gov-social"
command = "~/projects/sam_gov/.venv/bin/python"
args = ["-u", "~/projects/sam_gov/integrations/mcp/social_mcp.py"]
cwd = "~/projects/sam_gov"

[[servers]]
name = "sam-gov-research"
command = "~/projects/sam_gov/.venv/bin/python"
args = ["-u", "~/projects/sam_gov/integrations/mcp/research_mcp.py"]
cwd = "~/projects/sam_gov"

[[servers]]
name = "onto-canon"
command = "~/projects/onto-canon/.venv/bin/python"
args = ["-u", "~/projects/onto-canon/canon_mcp_server.py"]
cwd = "~/projects/onto-canon"

[[servers]]
name = "twitter"
command = "~/projects/twitter_explorer/.venv/bin/python"
args = ["-u", "~/projects/twitter_explorer/twitter_mcp_server.py"]
cwd = "~/projects/twitter_explorer"

[[servers]]
name = "dodaf"
command = "~/projects/dodaf/.venv/bin/python"
args = ["-u", "~/projects/dodaf/dodaf_mcp_server.py"]
cwd = "~/projects/dodaf"

[[servers]]
name = "process-tracing"
command = "~/projects/process_tracing/.venv/bin/python"
args = ["-u", "~/projects/process_tracing/pt_mcp_server.py"]
cwd = "~/projects/process_tracing"

[[servers]]
name = "theory-forge"
command = "~/projects/theory-forge/.venv/bin/python"
args = ["-u", "~/projects/theory-forge/tf_mcp_server.py"]
cwd = "~/projects/theory-forge"

[[servers]]
name = "qualitative-coding"
command = "~/projects/qualitative_coding/.venv/bin/python"
args = ["-u", "~/projects/qualitative_coding/qc_mcp_server.py"]
cwd = "~/projects/qualitative_coding"

[[servers]]
name = "conspiracy-epistemics"
command = "~/projects/conspiracy_epistemics/.venv/bin/python"
args = ["-u", "~/projects/conspiracy_epistemics/ce_mcp_server.py"]
cwd = "~/projects/conspiracy_epistemics"

[[servers]]
name = "intelligent-reddit-research"
command = "~/projects/mcp-servers/intelligent-reddit-research/.venv/bin/python"
args = ["-u", "~/projects/mcp-servers/intelligent-reddit-research/server.py"]
cwd = "~/projects/mcp-servers/intelligent-reddit-research"

# npx servers — no venv, just npx
[[servers]]
name = "fetch"
command = "uvx"
args = ["mcp-server-fetch"]

[[servers]]
name = "filesystem"
command = "npx"
args = ["@modelcontextprotocol/server-filesystem", "~/projects"]

[[servers]]
name = "sqlite"
command = "npx"
args = ["@modelcontextprotocol/server-sqlite"]

[[servers]]
name = "puppeteer"
command = "npx"
args = ["@modelcontextprotocol/server-puppeteer"]

[[servers]]
name = "youtube-transcript"
command = "npx"
args = ["@emit-ia/youtube-transcript-mcp"]
```

### Loader function (in `run_task.py`)

```python
import tomllib  # Python 3.11+

MCP_REGISTRY = Path(os.environ.get(
    "OPENCLAW_MCP_REGISTRY",
    Path.home() / ".openclaw" / "mcp_registry.toml",
))

def _load_mcp_registry() -> dict[str, dict[str, Any]]:
    """Load MCP server configs from TOML registry.

    Returns dict mapping server_name -> {command, args, env?, cwd?}
    with ~ expanded in all paths.
    """
    if not MCP_REGISTRY.exists():
        log.warning("MCP registry not found: %s", MCP_REGISTRY)
        return {}

    with open(MCP_REGISTRY, "rb") as f:
        data = tomllib.load(f)

    home = str(Path.home())
    configs: dict[str, dict[str, Any]] = {}

    for server in data.get("servers", []):
        name = server["name"]
        entry: dict[str, Any] = {
            "command": server["command"].replace("~", home),
        }
        if "args" in server:
            entry["args"] = [a.replace("~", home) for a in server["args"]]
        if "cwd" in server:
            entry["cwd"] = server["cwd"].replace("~", home)
        if "env" in server:
            entry["env"] = {
                k: v.replace("~", home) for k, v in server["env"].items()
            }
        configs[name] = entry

    log.info("Loaded %d MCP server configs from %s", len(configs), MCP_REGISTRY)
    return configs
```

### Why a separate registry (not reusing config.toml)?

1. **Codex config.toml is Codex's concern.** It may gain Codex-specific fields (permissions, model overrides) that don't apply here.
2. **Path portability.** The registry uses `~` which expands correctly on both WSL2 (`/home/brian`) and Mac Mini (`/Users/brian`). The path substitution script in `MAC_MINI_TOOLING_SETUP.md` only needs to handle the few hardcoded paths, not this file.
3. **Subset control.** Not all 18 servers need to be available to the task graph runner. The registry is what's actually offered.

### Sync with config.toml

A one-time script can generate the initial `mcp_registry.toml` from `config.toml`:

```python
# generate_mcp_registry.py (run once)
import tomllib, tomli_w
from pathlib import Path

with open(Path.home() / ".codex" / "config.toml", "rb") as f:
    codex = tomllib.load(f)

home = str(Path.home())
servers = []
for s in codex.get("mcp_servers", []):
    entry = {"name": s["name"]}
    for key in ("command", "args", "cwd", "env"):
        if key in s:
            val = s[key]
            if isinstance(val, str):
                val = val.replace(home, "~")
            elif isinstance(val, list):
                val = [v.replace(home, "~") if isinstance(v, str) else v for v in val]
            elif isinstance(val, dict):
                val = {k: v.replace(home, "~") if isinstance(v, str) else v for k, v in val.items()}
            entry[key] = val
    servers.append(entry)

output = Path.home() / ".openclaw" / "mcp_registry.toml"
with open(output, "wb") as f:
    tomli_w.dump({"servers": servers}, f)
```

## 3. Cost Integration

The task graph runner tracks costs internally via `ExecutionReport.total_cost_usd`. But OpenClaw's existing budget system reads `~/.openclaw/cost_log.jsonl`. These need to be bridged.

### Approach: write to both logs

`run_graph()` writes experiment records to `experiments.jsonl` (for the analyzer). `_run_graph_task()` in `run_task.py` also writes to `cost_log.jsonl` (for OpenClaw budget tracking):

```python
def _log_cost_from_task_result(tr: "TaskResult", graph_id: str) -> None:
    """Write a task result to OpenClaw's cost_log.jsonl."""
    entry = {
        "task_id": f"{graph_id}/{tr.task_id}",
        "agent": tr.model_selected or "scripted",
        "model": tr.model_selected or "",
        "cost_usd": tr.cost_usd,
        "duration_s": tr.duration_s,
        "status": tr.status.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(COST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

The existing `_check_daily_budget()` function works unchanged — it sums all entries for today regardless of whether they came from flat tasks or graph tasks.

### Budget check before each wave (future enhancement)

Currently `run_graph()` doesn't check budgets mid-graph. For Phase 1, the budget check at task pickup time is sufficient. If a graph runs over budget, the cost_log records it and the next task gets blocked.

For Phase 2, `run_graph()` could accept a `budget_remaining_usd` parameter and check before each wave dispatch. Low priority — the $20/day cap is a soft guard, not a hard limit.

## 4. Proposal Feedback Loop

The analyzer writes proposals to `proposals.jsonl`. OpenClaw needs to read and act on them.

### Read path (OpenClaw heartbeat)

On each heartbeat (every 30m), OpenClaw should:

1. Read `proposals.jsonl` — filter to `applied == false`
2. Auto-apply `risk == "low"` proposals (model downgrades):
   - Update `model_floors.json` with the new floor
   - Mark proposal as `applied: true`
3. Queue `risk == "medium"` and `risk == "high"` for morning brief
4. Include proposal summary in the morning brief markdown

### Proposal reading (OpenClaw prompt snippet)

This goes in OpenClaw's heartbeat instructions (not in run_task.py):

```
Check ~/projects/data/task_graph/proposals.jsonl for unapplied proposals.
For each proposal with risk="low" and auto_apply=true:
  - Update model_floors.json to reflect the proposed tier change
  - Mark the proposal as applied
For proposals with risk="medium" or "high":
  - Add to morning brief for human review
```

### model_floors.json location

Default: `~/projects/data/task_graph/model_floors.json`

This file is the system's cumulative learning. It persists across runs and across machine transfers. **Must be included in MAC_MINI_TRANSFER_NOTES.md** — it's learned knowledge, not regenerable.

## 5. First Real Task Graph

A minimal but real task graph for testing the wiring on Mac Mini. This exercises all three layers (runner, difficulty router, analyzer) without depending on external APIs.

### `~/.openclaw/tasks/templates/smoke_test.yaml`

```yaml
graph:
  id: smoke_test
  description: "Verify task graph runner is working on this machine"
  timeout_minutes: 10
  checkpoint: none

tasks:
  check_environment:
    difficulty: 0
    prompt: "n/a"
    validate:
      - type: file_exists
        path: ~/.secrets/api_keys.env
      - type: command
        command: "python3 -c 'import llm_client; print(llm_client.__file__)'"
    outputs:
      llm_client_ok: "true"

  simple_extraction:
    difficulty: 1
    agent: codex
    depends_on: [check_environment]
    prompt: |
      Read the file ~/.openclaw/workspace/SOUL.md and extract a JSON
      summary with keys: name, role, core_values (list of strings).
      Write the result to /tmp/openclaw_smoke_test.json.
    working_directory: ~/.openclaw
    validate:
      - type: file_exists
        path: /tmp/openclaw_smoke_test.json
      - type: json_schema
        path: /tmp/openclaw_smoke_test.json
        schema:
          type: object
          required: [name, role, core_values]
          properties:
            name: { type: string }
            role: { type: string }
            core_values: { type: array, items: { type: string } }
    outputs:
      summary: /tmp/openclaw_smoke_test.json
```

### Expected behavior

1. **Wave 0**: `check_environment` — tier 0 (scripted), runs validators only
   - Checks `api_keys.env` exists and `llm_client` is importable
   - No LLM call, no cost
2. **Wave 1**: `simple_extraction` — tier 1, routes to `deepseek/deepseek-chat` or `ollama/llama3.1` if available
   - Codex agent reads a local file and writes JSON
   - Validated: file exists + JSON schema match
   - Cost: ~$0.001

After both succeed, the analyzer writes an experiment record. On subsequent runs, if `simple_extraction` keeps succeeding at tier 1, no proposals are generated (already at a cheap tier).

## 6. `_list_pending()` Update

The existing `_list_pending()` only globs `*.md`. Needs to also find `*.yaml`:

```python
def _list_pending() -> list[TaskSpec | TaskGraph]:
    pending_dir = TASKS_DIR / "pending"
    if not pending_dir.exists():
        return []
    tasks = []
    for f in sorted(pending_dir.glob("*.md")):
        try:
            tasks.append(TaskSpec.from_file(f))
        except Exception as e:
            log.warning("Skipping %s: %s", f.name, e)
    # Task graphs listed separately (no priority sorting — they run as-is)
    graphs = sorted(pending_dir.glob("*.yaml")) + sorted(pending_dir.glob("*.yml"))
    # ... display logic for --list
```

For `--list`, graphs display differently:
```
  [graph] smoke_test: 2 tasks, 2 waves (smoke_test.yaml)
  [high]  task_042: Fix auth bug (agent=claude-code, project=~/projects/sam_gov)
```

For auto-pick (no args), flat tasks still take priority by sort key. Graphs are picked only if no flat tasks are pending (or a `--prefer-graphs` flag is passed).

## 7. Dry-Run Support

The existing `--dry-run` flag works for flat tasks. Extend for graphs:

```python
if args.dry_run:
    if task_path.suffix in (".yaml", ".yml"):
        graph = load_graph(task_path)
        mcp_configs = _load_mcp_registry()
        report = await run_graph(graph, mcp_server_configs=mcp_configs, dry_run=True)
        print(f"Graph: {graph.meta.id} ({len(graph.tasks)} tasks, {len(graph.waves)} waves)")
        for wave_idx, wave in enumerate(graph.waves):
            print(f"\nWave {wave_idx + 1}:")
            for tid in wave:
                tr = next(r for r in report.task_results if r.task_id == tid)
                task = graph.tasks[tid]
                print(f"  {tid}: tier={task.difficulty} model={tr.model_selected} agent={task.agent}")
                if task.mcp_servers:
                    available = [s for s in task.mcp_servers if s in mcp_configs]
                    missing = [s for s in task.mcp_servers if s not in mcp_configs]
                    print(f"    mcp: {available}")
                    if missing:
                        print(f"    MISSING mcp: {missing}")
        return
    else:
        # existing flat task dry-run
        ...
```

This is critical for Mac Mini setup — run `--dry-run` on the smoke test to verify all MCP servers resolve before actually dispatching agents.

## 8. File Layout (Mac Mini)

```
~/.openclaw/
  bin/
    run_task.py                    # Updated with graph support
  mcp_registry.toml                # NEW: MCP server startup configs
  tasks/
    pending/
      smoke_test.yaml              # Graph tasks (new)
      fix_whatever.md              # Flat tasks (existing)
    active/
    completed/
    failed/
    templates/
      smoke_test.yaml              # Reusable templates
  cost_log.jsonl                   # Existing cost tracking
  openclaw.json                    # Existing config

~/projects/data/task_graph/
  experiments.jsonl                # NEW: per-task experiment records
  proposals.jsonl                  # NEW: improvement proposals
  model_floors.json                # NEW: cumulative learning
```

## 9. Migration Checklist (for MAC_MINI_TRANSFER_NOTES.md)

Add to the "Must Transfer" section:

| Item | Source | Notes |
|------|--------|-------|
| `mcp_registry.toml` | `~/.openclaw/mcp_registry.toml` | Uses `~` paths, no edits needed |
| `model_floors.json` | `~/projects/data/task_graph/model_floors.json` | Learned knowledge — not regenerable |
| `experiments.jsonl` | `~/projects/data/task_graph/experiments.jsonl` | Historical experiments — optional but valuable |
| `proposals.jsonl` | `~/projects/data/task_graph/proposals.jsonl` | Optional — starts fresh is fine |

Add to the "Post-Transfer" checklist:

- [ ] Generate `mcp_registry.toml` (run `generate_mcp_registry.py` or copy from WSL2)
- [ ] Verify: `python3 -c "from llm_client.task_graph import load_graph; print('ok')"`
- [ ] Dry-run smoke test: `run_task.py --dry-run ~/.openclaw/tasks/templates/smoke_test.yaml`
- [ ] Live smoke test: `run_task.py ~/.openclaw/tasks/templates/smoke_test.yaml`

## 10. What This Does NOT Cover

- **OpenClaw writing task graphs.** That's the coordinator brain's responsibility. This spec only covers the mechanical runner.
- **Graph retry logic.** Phase 1 stops on failure. OpenClaw decides whether to retry on the next heartbeat.
- **Budget-aware wave dispatch.** Phase 1 checks budget at graph start only.
- **MCP server health checks.** If a server fails to start, the agent task will fail with an error. No pre-flight health check yet.
- **Graph versioning.** No mechanism to diff/track changes to task graph templates over time. Use git.
