# OpenClaw Setup - Current Status & Next Steps

**Last Updated:** 2026-02-07
**Installation Date:** 2026-02-02
**Current Status:** ✅ Fully operational with Discord

---

## Current Configuration

### System Info
- **OpenClaw Version:** Latest (as of 2026-02-03)
- **Installation:** Global npm install (`npm install -g openclaw`)
- **Node.js:** v22.16.0
- **Platform:** WSL2 (Ubuntu on Windows)

### Active Services
- **Gateway:** Running on port 18789 (local)
- **Service:** systemd user service (`openclaw-gateway.service`)
- **Model:** OpenAI Codex (gpt-5.2) via OAuth subscription
- **Channels:** Discord (active)

### Authentication
- **Primary Provider:** OpenAI Codex OAuth
  - Uses existing Codex subscription (no per-token billing)
  - Model: `openai-codex/gpt-5.2`
- **Failed Attempt:** Anthropic Claude Code OAuth
  - Issue: Subscription tokens restricted to Claude Code only
  - Not usable for third-party tools like OpenClaw

### Discord Integration
- **Bot Name:** Moltbot_20260202
- **Bot Token:** Stored in systemd service environment
- **Server:** moltbot-server (Guild ID: 1467958253152501854)
- **Configuration:**
  - requireMention: true (must @mention in groups)
  - DM: enabled with pairing policy
  - Message Content Intent: ✅ Enabled
  - Server Members Intent: ✅ Enabled

### Key File Locations
- **Config:** `~/.openclaw/openclaw.json`
- **Workspace:** `~/.openclaw/workspace/`
  - IDENTITY.md
  - USER.md
  - AGENTS.md
  - HEARTBEAT.md
  - SOUL.md
- **Sessions:** `~/.openclaw/agents/main/sessions/`
- **Auth:** `~/.openclaw/agents/main/agent/auth-profiles.json`
- **Systemd Service:** `~/.config/systemd/user/openclaw-gateway.service`
- **Service Override:** `~/.config/systemd/user/openclaw-gateway.service.d/discord.conf`

---

## What's Working ✅

1. **Multi-channel Gateway**
   - WebSocket server on port 18789
   - Session routing and isolation
   - Discord integration active

2. **Discord Bot**
   - Responds to @mentions
   - DM pairing functional
   - Message Content Intent enabled
   - Connected and operational

3. **Memory System**
   - Workspace initialized
   - Bootstrap files created (IDENTITY, USER, etc.)
   - Session persistence working
   - Daily logs ready (memory/*.md)

4. **LLM Integration**
   - OpenAI Codex working
   - Streaming responses
   - Tool use functional

5. **Session Management**
   - Per-sender isolation
   - Context switching
   - Reset policies configured

---

## Known Issues / Limitations ⚠️

1. **Memory Growth**
   - Daily logs grow infinitely (no auto-cleanup)
   - Known issue: GitHub #5429
   - Workaround: Manual cleanup needed

2. **Heartbeat Not Configured**
   - Default: disabled (every: "0m")
   - Recommendation: Start with 0, enable later
   - Cost consideration: ~$0.01-0.02/day at 30min intervals

3. **Learning Extension**
   - Not implemented (uses pre-trained LLM only)
   - No online learning or adaptation
   - Memory updates != learning

4. **Explanation System**
   - No explicit trace generation
   - Relies on LLM transparency
   - Could add reasoning trace skill

---

## Configuration Summary

### Gateway (`~/.openclaw/openclaw.json`)
```json
{
  "gateway": {
    "mode": "local",
    "port": 18789,
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "<YOUR_GATEWAY_TOKEN_HERE>"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "openai-codex/gpt-5.2"
      },
      "workspace": "/home/brian/.openclaw/workspace",
      "compaction": {
        "mode": "safeguard"
      }
    }
  },
  "channels": {
    "discord": {
      "enabled": true,
      "groupPolicy": "allowlist",
      "dm": {
        "enabled": true,
        "policy": "pairing"
      },
      "guilds": {
        "1467958253152501854": {
          "slug": "moltbot-server",
          "requireMention": true
        }
      }
    }
  }
}
```

### Systemd Service Environment
```ini
# ~/.config/systemd/user/openclaw-gateway.service.d/discord.conf
[Service]
Environment="DISCORD_BOT_TOKEN=<YOUR_BOT_TOKEN_HERE>"
```

**Note:** Actual token is stored locally and NOT committed to git.

---

## Architecture Understanding

### Cognitive Components Present
- ✅ Perception (multi-channel input)
- ✅ Attention (requireMention, groupPolicy)
- ✅ Working Memory (session context ~130k tokens)
- ✅ Episodic Memory (memory/YYYY-MM-DD.md)
- ✅ Semantic Memory (MEMORY.md + vector search)
- ✅ Procedural Memory (skills, progressive disclosure)
- ✅ Reasoning (LLM inference)
- ✅ Planning (multi-turn conversations)
- ✅ Goal Management (loop conditions, early termination)
- ✅ Error Handling (try/catch/retry)
- ✅ Context Management (session switching)
- ✅ Execution (tools, browser, skills)
- ✅ Meta-Cognition (heartbeat system - not yet enabled)
- ✅ Social Cognition (multi-agent routing)
- ✅ Temporal Reasoning (cron, heartbeat scheduling)
- ❌ Learning (not implemented)
- ❌ Explanation (no trace generation)

### Key Architectural Patterns
1. **Multi-Tier Memory:** Working → Episodic → Semantic → Procedural
2. **Progressive Disclosure:** Skills loaded on-demand (saves ~65k tokens)
3. **Session Isolation:** Per-sender routing prevents context leakage
4. **Hybrid Pattern:** Both reactive and deliberative paths
5. **Cost Optimization:** Heartbeat batching, prompt caching

---

## Next Steps

### Immediate (Do Now)
- [ ] **Enable Heartbeat** - Start with longer interval (60min) to test
- [ ] **Configure MEMORY.md** - Add initial facts about user/preferences
- [ ] **Test Memory System** - Verify daily logs are being written
- [ ] **Add SMS/WhatsApp** - Configure additional channels if desired

### Short Term (This Week)
- [ ] **Monitor Memory Growth** - Check daily log file sizes
- [ ] **Explore Skills** - Browse ClawdHub, install useful skills
- [ ] **Configure Workspace** - Customize IDENTITY.md, USER.md
- [ ] **Test Multi-Agent** - Try routing to different agents
- [ ] **Set Up Diary** - Configure activity tracking workflow

### Medium Term (This Month)
- [ ] **Deploy Cognitive Ontology** - Use framework to analyze OpenClaw
- [ ] **Compare Architectures** - Map OpenClaw vs other frameworks
- [ ] **Optimize Token Usage** - Profile and reduce unnecessary context
- [ ] **Add Integrations** - Linear, Slack, email, calendar
- [ ] **Implement Custom Skills** - Create project-specific capabilities

### Long Term (Future)
- [ ] **Learning Extension** - Add feedback loops for adaptation
- [ ] **Explanation System** - Implement reasoning trace generation
- [ ] **Multi-Modal** - Add image, voice capabilities
- [ ] **Advanced Memory** - Implement compaction strategies
- [ ] **Performance Tuning** - Optimize for cost and latency

---

## Troubleshooting Reference

### Gateway Won't Start
```bash
# Check status
systemctl --user status openclaw-gateway

# View logs
journalctl --user -u openclaw-gateway -f

# Restart
systemctl --user restart openclaw-gateway
```

### Discord Bot Not Responding
1. Check Message Content Intent in Discord Developer Portal
2. Verify bot is in server members list
3. Check requireMention setting
4. Verify DISCORD_BOT_TOKEN is set in service environment

### Authentication Issues
```bash
# Check auth profiles
cat ~/.openclaw/agents/main/agent/auth-profiles.json

# Re-run onboarding if needed
openclaw onboard
```

### Memory Issues
```bash
# Check workspace
ls -la ~/.openclaw/workspace/

# Check daily logs
ls -la ~/.openclaw/workspace/memory/

# Monitor session files
ls -lh ~/.openclaw/agents/main/sessions/
```

---

## Research & Documentation

### Completed Deep Dives
1. ✅ **Fundamental Differences** - OpenClaw vs Claude Code/MCP
2. ✅ **Memory Architecture** - 4-tier hierarchy, no auto-cleanup
3. ✅ **Heartbeat System** - 30min polling, cost optimization
4. ✅ **Skills Loading** - Progressive disclosure pattern
5. ✅ **Session Management** - Isolation and routing
6. ✅ **Browser Control** - CDP + Playwright architecture
7. ✅ **Cognitive Ontology** - Formal reified hypergraph model

### Documentation Created
- DISCORD_SETUP_NOTES.md - Complete Discord integration guide
- COGNITIVE_ONTOLOGY.md - Conceptual framework
- ONTOLOGY_STRUCTURE.md - Core + Extensions design
- ONTOLOGY_README.md - Complete ontology reference
- QUICK_START.md - Framework usage guide
- Interactive visualizations (4 HTML files)
- Formal ontology (cognitive-architecture.ttl)

### Questions Answered
- Why OpenClaw vs Claude Code? → Multi-channel, persistent, always-on
- How does memory work? → 4 tiers with different retention policies
- How are skills loaded? → Progressive disclosure, not bulk
- What's the heartbeat? → Batched 30min self-monitoring
- Session isolation? → Deterministic routing by source
- Browser automation? → CDP + Playwright

---

## Useful Commands

```bash
# OpenClaw CLI
openclaw config get              # View config
openclaw config set key value    # Update config
openclaw sessions                # List sessions
openclaw skills                  # List skills
openclaw system heartbeat enable # Enable heartbeat

# Gateway Management
systemctl --user start openclaw-gateway
systemctl --user stop openclaw-gateway
systemctl --user restart openclaw-gateway
systemctl --user status openclaw-gateway

# Logs
journalctl --user -u openclaw-gateway -f

# Skills (ClawdHub)
clawdhub search "keyword"
clawdhub install skill-name
clawdhub update --all
```

---

## Resources

- **Official Docs:** https://docs.openclaw.ai
- **ClawdHub:** https://clawdhub.com
- **Discord:** https://discord.gg/openclaw (if exists)
- **GitHub:** https://github.com/openclaw/openclaw

---

## Notes from Session

- Successfully set up from scratch with comprehensive documentation
- Switched from Anthropic to Codex OAuth due to subscription token restrictions
- Created complete cognitive architecture framework with reified hypergraph ontology
- Built 4 interactive visualizations for understanding architecture
- Mapped OpenClaw to formal ontology (11/16 extensions present)
- Identified key patterns: hybrid reactive/deliberative, 4-tier memory, progressive disclosure

**Session Duration:** ~8 hours of exploration, setup, and research
**Outcome:** Fully functional OpenClaw + deep architectural understanding
