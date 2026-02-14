# Moltbot / OpenClaw

OpenClaw Discord bot setup and configuration.

> Moltbot was renamed to **OpenClaw** on Jan 29 2026 due to a trademark issue.
> The `moltbot` npm package still works but docs have moved to `docs.openclaw.ai`.

## Current Status

- **Gateway**: systemd user service (`openclaw-gateway.service`) on port 18789
- **Model**: gpt-5.2 via OpenAI Codex OAuth
- **Discord**: Bot active, responding to @mentions and DMs
- **Config**: `~/.openclaw/openclaw.json`
- **Workspace**: `~/.openclaw/workspace/`

See `OPENCLAW_STATUS.md` for full status, configuration details, and next steps.

## Quick Start

```bash
# Install
npm install -g openclaw@latest

# Set up Discord integration
export DISCORD_BOT_TOKEN="your-token"
openclaw onboard --install-daemon

# Verify
openclaw channels status --probe
```

See `DISCORD_SETUP_NOTES.md` for the complete Discord setup guide (bot creation, intents, OAuth2, guild config, DMs, troubleshooting).

## Key Files

| File | Purpose |
|------|---------|
| `DISCORD_SETUP_NOTES.md` | Complete Discord integration guide |
| `OPENCLAW_STATUS.md` | Current status, auth, services, next steps |

## Useful Commands

```bash
# Gateway management
systemctl --user status openclaw-gateway
systemctl --user restart openclaw-gateway
journalctl --user -u openclaw-gateway -f

# OpenClaw CLI
openclaw config get
openclaw sessions
openclaw skills
openclaw doctor
```

## Resources

- **Docs**: https://docs.openclaw.ai
- **GitHub**: https://github.com/openclaw/openclaw
- **ClawdHub**: https://clawdhub.com

## Archive

The `archive/ontology_2026-02-05/` directory contains cognitive architecture ontology work from the initial session. This work has been superseded by the `agent_ontology` project (`/home/brian/projects/agent_ontology`).
