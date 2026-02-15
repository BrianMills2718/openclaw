# Mac Mini Tooling Ecosystem Setup

Companion to `MAC_MINI_TRANSFER_NOTES.md` (which covers data files).
This document covers system tools, configs, MCP servers, and automation.

**Source**: WSL2 Ubuntu on DESKTOP-79G7E9D
**Target**: Mac Mini (macOS, Apple Silicon)
**Key path change**: `/home/brian/` → `/Users/brian/`

---

## 1. System Tools to Install

Install in this order (dependencies flow down):

```bash
# 1. Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Core tools
brew install git gh docker python@3.12

# 3. Node version manager + Node
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
nvm install 22.16.0
nvm alias default 22.16.0

# 4. Python tools
curl -LsSf https://astral.sh/uv/install.sh | sh

# 5. Miniconda (needed for digimon KG-RAG)
# Download from https://docs.conda.io/en/latest/miniconda.html (Apple Silicon)

# 6. Rust (used by some dependencies)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 7. Bun
curl -fsSL https://bun.sh/install | bash

# 8. Tailscale (for WSL2 ↔ Mac Mini file transfer)
brew install --cask tailscale
```

### Global npm packages

```bash
npm install -g @openai/codex@0.101.0 openclaw@2026.2.1 @anthropic-ai/claude-code typescript repomix
```

MCP npx packages (auto-installed on first use, no pre-install needed):
`@modelcontextprotocol/server-filesystem`, `@modelcontextprotocol/server-puppeteer`,
`@modelcontextprotocol/server-sqlite`, `@modelcontextprotocol/server-postgres`,
`@emit-ia/youtube-transcript-mcp`, `mcp-server-fetch` (via uvx)

---

## 2. Configuration Files to Copy

### Must copy (then edit paths)

| Source | Purpose | Path edits needed? |
|--------|---------|-------------------|
| `~/.codex/config.toml` | Codex CLI + all 17 MCP servers | Yes (35 paths) |
| `~/.config/claude-cli-nodejs/mcp.json` | Claude Code MCP servers | Yes (5 paths) |
| `~/.openclaw/` (entire dir) | OpenClaw workspace, config, cron, skills | Yes (many) |
| `~/.codex/skills/` | Codex CLI skills (research-workbench, osint-investigation) | Yes (few) |
| `~/.gitconfig` | Git config | Yes (hooksPath) |
| `~/.ssh/` | SSH keys | No (preserve permissions!) |
| `~/.secrets/api_keys.env` | All API keys | No |
| `~/projects/research-agent/.mcp.json` | Research agent MCP config | Yes (20 paths) |
| `~/projects/.mcp.json` | Root projects MCP config | Yes (5 paths) |

### Must recreate (platform-specific)

| Item | WSL2 | macOS equivalent |
|------|------|-----------------|
| systemd service | `~/.config/systemd/user/openclaw-gateway.service` | `~/Library/LaunchAgents/com.openclaw.gateway.plist` |
| Crontab | `crontab -l` | `crontab -e` (same syntax, update paths) |
| .bashrc | `/home/brian/.bashrc` | `~/.zshrc` (macOS default shell is zsh) |

---

## 3. Path Substitution Script

Run this on the Mac Mini after copying config files:

```bash
#!/bin/bash
# mac-mini-path-fix.sh — Run AFTER copying configs to Mac Mini

OLD="/home/brian"
NEW="/Users/brian"

# MCP configs
sed -i '' "s|${OLD}|${NEW}|g" ~/.codex/config.toml
sed -i '' "s|${OLD}|${NEW}|g" ~/.config/claude-cli-nodejs/mcp.json
sed -i '' "s|${OLD}|${NEW}|g" ~/projects/research-agent/.mcp.json
sed -i '' "s|${OLD}|${NEW}|g" ~/projects/.mcp.json
sed -i '' "s|${OLD}|${NEW}|g" ~/projects/twitter_explorer/.mcp.json
sed -i '' "s|${OLD}|${NEW}|g" ~/projects/dodaf/.mcp.json
sed -i '' "s|${OLD}|${NEW}|g" ~/projects/qualitative_coding/.mcp.json

# OpenClaw configs
sed -i '' "s|${OLD}|${NEW}|g" ~/.openclaw/openclaw.json
sed -i '' "s|${OLD}|${NEW}|g" ~/.openclaw/cron/jobs.json

# OpenClaw workspace docs (hardcoded paths in instructions)
find ~/.openclaw/workspace -name "*.md" -exec sed -i '' "s|${OLD}|${NEW}|g" {} +
find ~/.openclaw/agents -name "*.md" -exec sed -i '' "s|${OLD}|${NEW}|g" {} +

# Skills
find ~/.codex/skills -name "*.md" -exec sed -i '' "s|${OLD}|${NEW}|g" {} +
find ~/.openclaw/workspace/skills -name "*.md" -exec sed -i '' "s|${OLD}|${NEW}|g" {} +

# Git config
sed -i '' "s|${OLD}|${NEW}|g" ~/.gitconfig

echo "Path substitution complete. Verify with:"
echo "  grep -r '/home/brian' ~/.codex/ ~/.openclaw/ ~/.config/claude-cli-nodejs/"
```

---

## 4. MCP Server Inventory

### 18 servers, grouped by launch method

**Python venv servers** (10 servers, all need venv recreation):

| Server | Project | Venv | Recreate Command |
|--------|---------|------|-----------------|
| sam-gov-government | sam_gov | `.venv` | `uv venv && uv pip install -r requirements.txt` |
| sam-gov-social | sam_gov | `.venv` | (same venv as above) |
| sam-gov-research | sam_gov | `.venv` | (same venv as above) |
| intelligent-reddit-research | mcp-servers/intelligent-reddit-research | `.venv` | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| dodaf | dodaf | `.venv` | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| investigative-wiki | investigative_wiki | `.venv` | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| process-tracing | process_tracing | `test_env` | `python3 -m venv test_env && test_env/bin/pip install -e universal_llm_kit/` |
| theory-forge | theory-forge | `.venv` | `python3 -m venv .venv && .venv/bin/pip install -e .` |
| qualitative-coding | qualitative_coding | `qc_env` | `python3 -m venv qc_env && qc_env/bin/pip install -r requirements.txt` |
| conspiracy-epistemics | conspiracy_epistemics | `venv` | `python3 -m venv venv && venv/bin/pip install -r requirements.txt` |

**Conda server** (1 server):

| Server | Conda Env | Recreate |
|--------|-----------|----------|
| digimon-kgrag | `digimon` | Export: `conda env export -n digimon > digimon-env.yml` then `conda env create -f digimon-env.yml` |

**uv-managed server** (1 server):

| Server | Project | Recreate |
|--------|---------|----------|
| twitter | twitter_explorer | `uv sync` (requires Python 3.12, has `.python-version` file) |

**npx/uvx servers** (6 servers, no setup needed):

| Server | Package |
|--------|---------|
| fetch | `uvx mcp-server-fetch` |
| filesystem | `npx @modelcontextprotocol/server-filesystem` |
| sqlite | `npx @modelcontextprotocol/server-sqlite` |
| puppeteer | `npx @modelcontextprotocol/server-puppeteer` |
| youtube-transcript | `npx @emit-ia/youtube-transcript-mcp` |
| postgres | `npx @modelcontextprotocol/server-postgres` |

### Config inconsistencies to fix BEFORE transfer

1. **qualitative-coding**: Project-level `.mcp.json` and root `~/projects/.mcp.json` use `/usr/bin/python` (system Python) instead of `qc_env/bin/python`. Should match the Codex config.
2. **postgres**: Connection string hardcoded as `postgresql://postgres:password@localhost:5432/test_db`. Not running on WSL2 either. Decide if needed on Mac.

---

## 5. Environment Files (.env)

10 active .env files need manual transfer (not in git):

| Project | Key API keys |
|---------|-------------|
| sam_gov | OPENAI, GEMINI, BRAVE_SEARCH, REDDIT creds, DVIDS, USAJOBS, CONGRESS, COURTLISTENER, NEWSAPI, EXA, TELEGRAM, SMTP |
| qualitative_coding | OPENAI, GEMINI, ANTHROPIC, NEO4J creds, model configs |
| Digimons | OPENAI, GEMINI, ANTHROPIC, NEO4J creds, model configs |
| investigative_wiki | OPENAI, DVIDS, SAM_GOV (deprecated), USAJOBS, BRAVE_SEARCH, REDDIT, GEMINI, TAVILY |
| twitter_explorer | RAPIDAPI_KEY |
| conspiracy_epistemics | GEMINI_API_KEY |
| theory-forge | OPENAI, GEMINI, THEORY_FORGE_MODEL |
| process_tracing | GOOGLE_API_KEY, GEMINI, OPENAI, GEMINI_MODEL |
| steno | OPENAI (steno-specific key), GEMINI |
| humour | XAI_API_KEY (Grok), XAI_MODEL |
| agent_ecology2 | GEMINI |

Transfer script:
```bash
# From WSL2 (after Tailscale is set up on both):
for proj in sam_gov qualitative_coding Digimons investigative_wiki twitter_explorer \
  conspiracy_epistemics theory-forge process_tracing steno humour agent_ecology2; do
  scp ~/projects/${proj}/.env macmini:~/projects/${proj}/.env
done
```

---

## 6. Secrets Cleanup (DO BEFORE TRANSFER)

### DONE (on WSL2, 2026-02-15)

- [x] Moved `GOOGLE_AI_STUDIO_KEY` and `GITHUB_PERSONAL_ACCESS_TOKEN` from `.bashrc` to `~/.secrets/api_keys.env`
- [x] `.bashrc` now sources `~/.secrets/api_keys.env` instead of hardcoding
- [x] Removed hardcoded `gho_` OAuth token from Claude Code `mcp.json`

### On Mac Mini transfer — generate fresh tokens

All tokens in `~/.secrets/api_keys.env` should be rotated when setting up the Mac Mini:
- Generate new GitHub PATs at https://github.com/settings/tokens
- Consolidate `GITHUB_TOKEN` and `GITHUB_PERSONAL_ACCESS_TOKEN` into one token
- Consider using a secrets manager (macOS Keychain, 1Password CLI, or `security` command) instead of a flat env file
- Set `~/.secrets/api_keys.env` to `chmod 600` and block from agent read access

---

## 7. Crontab

### Current crontab (WSL2) — needs path fixes

```cron
# Discord daily scrape — STALE PATH (still /home/brian/sam_gov, not /projects/sam_gov)
0 2 * * * /home/brian/sam_gov/.venv/bin/python3 /home/brian/sam_gov/experiments/discord/discord_daily_scrape.py >> /home/brian/sam_gov/data/logs/discord_daily_scrape_cron.log 2>&1

# Reddit daily scrape — STALE PATH (same issue)
0 3 * * * /home/brian/sam_gov/.venv/bin/python3 /home/brian/sam_gov/experiments/reddit/reddit_daily_scrape.py >> /home/brian/sam_gov/data/logs/reddit_daily_scrape_cron.log 2>&1

# FDOT monitoring
0 8 * * * /home/brian/projects/brent/brent_chatgpt/scripts/run_monitoring.sh >> /tmp/fdot-monitor.log 2>&1

# Claude Code history backup
0 4 * * * /home/brian/backups/claude-code/backup-claude-history.sh >> /home/brian/backups/claude-code/backup.log 2>&1
```

### Mac Mini crontab (corrected)

```cron
# Discord daily scrape
0 2 * * * /Users/brian/projects/sam_gov/.venv/bin/python3 /Users/brian/projects/sam_gov/experiments/discord/discord_daily_scrape.py >> /Users/brian/projects/sam_gov/data/logs/discord_daily_scrape_cron.log 2>&1

# Reddit daily scrape
0 3 * * * /Users/brian/projects/sam_gov/.venv/bin/python3 /Users/brian/projects/sam_gov/experiments/reddit/reddit_daily_scrape.py >> /Users/brian/projects/sam_gov/data/logs/reddit_daily_scrape_cron.log 2>&1

# FDOT monitoring
0 8 * * * /Users/brian/projects/brent/brent_chatgpt/scripts/run_monitoring.sh >> /tmp/fdot-monitor.log 2>&1

# Claude Code history backup
0 4 * * * /Users/brian/backups/claude-code/backup-claude-history.sh >> /Users/brian/backups/claude-code/backup.log 2>&1
```

### OpenClaw internal cron (4 jobs in `~/.openclaw/cron/jobs.json`)

| Job | Schedule | Status |
|-----|----------|--------|
| Daily diary ping | 10pm ET | FAILING — "Ambiguous Discord recipient" |
| Morning brief | 7am ET | FAILING |
| Nightly meditation | 1am ET | OK |
| Research heartbeat | Every 4h | OK |

These are managed by the OpenClaw gateway process, not system crontab. They'll transfer with `~/.openclaw/` but the two failing jobs need fixing.

---

## 8. OpenClaw Gateway Service (systemd → launchd)

### Current (Linux, disabled)

`~/.config/systemd/user/openclaw-gateway.service.disabled`

### Mac Mini equivalent

Create `~/Library/LaunchAgents/com.openclaw.gateway.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/brian/.nvm/versions/node/v22.16.0/bin/node</string>
        <string>/Users/brian/.nvm/versions/node/v22.16.0/lib/node_modules/openclaw/dist/index.js</string>
        <string>gateway</string>
        <string>--port</string>
        <string>18789</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/brian</string>
        <key>OPENCLAW_GATEWAY_PORT</key>
        <string>18789</string>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/brian/.openclaw/logs/gateway.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/brian/.openclaw/logs/gateway.err.log</string>
</dict>
</plist>
```

Control with:
```bash
launchctl load ~/Library/LaunchAgents/com.openclaw.gateway.plist    # enable
launchctl unload ~/Library/LaunchAgents/com.openclaw.gateway.plist  # disable
launchctl start com.openclaw.gateway   # start now
launchctl stop com.openclaw.gateway    # stop now
```

Note: `RunAtLoad` set to `false` — load the plist but don't auto-start until you're ready.

---

## 9. Shell Config (bashrc → zshrc)

macOS default shell is zsh. Key items to port from `.bashrc`:

```zsh
# ~/.zshrc on Mac Mini

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

# Bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# Rust
source "$HOME/.cargo/env"

# uv / local bin
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/bin:$PATH"

# Secrets (NOT hardcoded)
[ -f ~/.secrets/api_keys.env ] && source ~/.secrets/api_keys.env

# Claude Code
export CLAUDE_CODE_MAX_OUTPUT_TOKENS=16384

# Aliases
alias gs='git status --short'
alias clada='claude --dangerously-skip-permissions'
alias cladas='claude --continue --dangerously-skip-permissions'
alias cladar='claude --resume --dangerously-skip-permissions'

# Conda (will be added by miniconda installer)
```

**Do NOT port from .bashrc:**
- `DISPLAY` export (WSL2 X11 forwarding, not needed on Mac)
- `/home/brian/.claude/local` PATH (doesn't exist)
- Hardcoded API keys (move to `~/.secrets/api_keys.env`)

---

## 10. Docker Dependencies

Only one project requires Docker:

**investigative_wiki** — Weaviate + Neo4j
```bash
cd ~/projects/investigative_wiki
docker compose up -d
```

On Mac Mini: Install Docker Desktop for Mac, then run the compose file.

---

## 11. Conda Environments

Export on WSL2 before transfer:
```bash
conda env export -n digimon > ~/projects/moltbot/conda-digimon-env.yml
conda env export -n trustgraph > ~/projects/moltbot/conda-trustgraph-env.yml
```

Recreate on Mac Mini:
```bash
conda env create -f ~/projects/moltbot/conda-digimon-env.yml
conda env create -f ~/projects/moltbot/conda-trustgraph-env.yml
```

Note: Some packages may not have Apple Silicon builds. Cross that bridge when we get there.

---

## 12. Venv Recreation Script

Run on Mac Mini after cloning all repos:

```bash
#!/bin/bash
# recreate-venvs.sh — Run on Mac Mini after git clone

PROJECTS_DIR="$HOME/projects"

# Standard .venv projects
for proj in sam_gov dodaf investigative_wiki theory-forge; do
  echo "=== $proj ==="
  cd "$PROJECTS_DIR/$proj"
  python3 -m venv .venv
  if [ -f requirements.txt ]; then
    .venv/bin/pip install -r requirements.txt
  elif [ -f pyproject.toml ]; then
    .venv/bin/pip install -e .
  fi
done

# sam_gov uses requirements.txt
cd "$PROJECTS_DIR/sam_gov" && .venv/bin/pip install -r requirements.txt

# theory-forge uses pyproject.toml
cd "$PROJECTS_DIR/theory-forge" && .venv/bin/pip install -e .

# Non-standard venv names
echo "=== process_tracing (test_env) ==="
cd "$PROJECTS_DIR/process_tracing"
python3 -m venv test_env
test_env/bin/pip install -e universal_llm_kit/

echo "=== qualitative_coding (qc_env) ==="
cd "$PROJECTS_DIR/qualitative_coding"
python3 -m venv qc_env
qc_env/bin/pip install -r requirements.txt

echo "=== conspiracy_epistemics (venv) ==="
cd "$PROJECTS_DIR/conspiracy_epistemics"
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# uv-managed
echo "=== twitter_explorer (uv) ==="
cd "$PROJECTS_DIR/twitter_explorer"
uv sync

# MCP servers
echo "=== intelligent-reddit-research ==="
cd "$PROJECTS_DIR/mcp-servers/intelligent-reddit-research"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

echo "Done. Test each server with: codex exec 'test mcp server X'"
```

---

## 13. Transfer Checklist

### Pre-transfer (on WSL2)

- [ ] Export conda environments to YML
- [ ] Clean up `.bashrc` secrets → move to `~/.secrets/api_keys.env`
- [ ] Rotate exposed GitHub tokens (`.bashrc` and `mcp.json`)
- [ ] Fix qualitative-coding `.mcp.json` inconsistency (use qc_env, not system python)
- [ ] Fix stale crontab paths (`/home/brian/sam_gov` → `/home/brian/projects/sam_gov`)
- [ ] Verify all git repos are pushed to GitHub

### Transfer (via Tailscale rsync or USB)

- [ ] `~/.secrets/api_keys.env`
- [ ] `~/.ssh/` (chmod 700 dir, chmod 600 private key)
- [ ] `~/.openclaw/` (entire directory)
- [ ] `~/.codex/` (config.toml + skills/)
- [ ] `~/.config/claude-cli-nodejs/mcp.json`
- [ ] `~/.gitconfig`
- [ ] All project `.env` files (see section 5)
- [ ] All project `.mcp.json` files
- [ ] Data files per `MAC_MINI_TRANSFER_NOTES.md`
- [ ] `~/backups/claude-code/backup-claude-history.sh`
- [ ] `~/bin/gemini-review` (custom script)

### Post-transfer (on Mac Mini)

- [ ] Install system tools (section 1)
- [ ] Install global npm packages
- [ ] Run path substitution script (section 3)
- [ ] Clone all git repos from GitHub
- [ ] Recreate venvs (section 12)
- [ ] Recreate conda environments (section 11)
- [ ] Copy `.env` files into projects
- [ ] Set up `.zshrc` (section 9)
- [ ] Create launchd plist (section 8) — don't enable yet
- [ ] Set up crontab (section 7)
- [ ] Start Docker, run `docker compose up` for investigative_wiki
- [ ] Test each MCP server individually
- [ ] Re-authenticate: `gh auth login`, OpenAI OAuth for Codex/OpenClaw
- [ ] Verify: `codex exec "list available MCP tools"`

---

## 14. Known Issues to Fix (Not Blocking Transfer)

| Issue | Location | Notes |
|-------|----------|-------|
| OpenClaw cron: daily diary failing | `~/.openclaw/cron/jobs.json` | "Ambiguous Discord recipient" |
| OpenClaw cron: morning brief failing | `~/.openclaw/cron/jobs.json` | Same error |
| Timezone inconsistency | USER.md says ET, cron may run PT | Verify after Mac Mini setup |
| Researcher agent barely configured | `~/.openclaw/agents/researcher/` | Empty IDENTITY.md, USER.md |
| postgres MCP: not running | `config.toml` | Decide if needed on Mac |
