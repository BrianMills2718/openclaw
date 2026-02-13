# Moltbot / OpenClaw

OpenClaw Discord bot setup + cognitive architecture ontology framework.

## What This Is

1. **OpenClaw Discord integration** — Fully operational AI assistant on Discord (gpt-5.2 via Codex OAuth)
2. **Cognitive architecture ontology** — Reified hypergraph framework for modeling agent architectures
3. **Interactive visualizations** — D3.js-based tools for exploring cognitive architectures
4. **Agent comparison** — Compare OpenClaw vs AutoGPT vs Claude.ai vs Minimal agents

## Quick Start

```bash
# Serve visualizations
cd /home/brian/projects/moltbot
python3 -m http.server 8000
# Then open http://localhost:8000/openclaw-cognitive.html
```

## Key Files

| File | Purpose |
|------|---------|
| `OPENCLAW_STATUS.md` | Current setup status, auth, services |
| `QUICK_START.md` | How to use the framework |
| `ONTOLOGY_STRUCTURE.md` | Core + Extensions ontology design |
| `cognitive-architecture.ttl` | Formal OWL ontology (SPARQL queryable) |
| `agent-instances.json` | Concrete agent implementations for comparison |
| `openclaw-cognitive.html` | Main interactive visualization |
| `agent-comparison.html` | Side-by-side agent comparison tool |

## OpenClaw Service

- **Gateway**: systemd user service (`openclaw-gateway.service`) on port 18789
- **Model**: gpt-5.2 via OpenAI Codex OAuth
- **Config**: `~/.openclaw/openclaw.json`
- **Workspace**: `~/.openclaw/workspace/` (beliefs, memory, reflections, tools)
- **Cron**: `~/.openclaw/cron/jobs.json` (daily diary entries)

GitHub repo name: `openclaw`
