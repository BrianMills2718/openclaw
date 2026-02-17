# Moltbot / OpenClaw

OpenClaw Discord bot setup project.

## What This Is

This repo contains setup notes and configuration for running OpenClaw (formerly Moltbot) as a Discord bot.

## Key Files

- `DISCORD_SETUP_NOTES.md` — Complete Discord integration guide
- `OPENCLAW_STATUS.md` — Current status, auth config, services, next steps
- `TASK_GRAPH_WIRING.md` — How run_task.py evolves to support YAML task graphs (via llm_client.task_graph)
- `MAC_MINI_TRANSFER_NOTES.md` — Large files not in git that need manual transfer
- `MAC_MINI_TOOLING_SETUP.md` — System tools, configs, MCP servers, venv recreation for Mac Mini

## OpenClaw Service

- **Gateway**: systemd user service on port 18789
- **Model**: gpt-5.2 via OpenAI Codex OAuth
- **Config**: `~/.openclaw/openclaw.json`
- **Workspace**: `~/.openclaw/workspace/`

## Related Projects

- **agent_ontology** (`/home/brian/projects/agent_ontology`) — Cognitive architecture ontology framework (evolved from early work in this repo)
- **sam_gov** (`/home/brian/sam_gov`) — Research platform with MCP tools

## Archive

`archive/ontology_2026-02-05/` contains superseded ontology work. See that directory's README for details.
