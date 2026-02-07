# Moltbot (OpenClaw) — Discord Setup Notes

> Moltbot was renamed to **OpenClaw** on Jan 29 2026 due to a trademark issue.
> The `moltbot` npm package still works but docs have moved to `docs.openclaw.ai`.
> CLI command is now `openclaw` (aliased from `moltbot`).

---

## 1. Prerequisites

| Requirement | Detail |
|-------------|--------|
| **Node.js** | v22+ required |
| **OS** | macOS, Linux native; Windows via WSL2 (Ubuntu recommended) |
| **Package manager** | npm or pnpm |
| **Discord account** | With a server you control (or have Manage Server perms on) |

**Refs:**
- [Getting Started](https://docs.openclaw.ai/start/getting-started)
- [GitHub repo](https://github.com/moltbot/moltbot)

---

## 2. Install Moltbot/OpenClaw

**Option A — installer script (recommended):**
```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

**Option B — npm:**
```bash
npm install -g openclaw@latest
# or: npm install -g moltbot@latest (legacy name still works)
```

**Option C — from source:**
```bash
git clone https://github.com/openclaw/openclaw.git
cd openclaw
pnpm install
pnpm ui:build
pnpm build
```

**Ref:** [Getting Started — Installation](https://docs.openclaw.ai/start/getting-started)

---

## 3. Create a Discord Bot

All of this happens in the **Discord Developer Portal**: https://discord.com/developers/applications

### 3a. Create application & bot
1. **Applications** → **New Application** → name it
2. Go to **Bot** tab → **Add Bot**
3. Copy the **Bot Token** — treat it like a password

### 3b. Enable required Gateway Intents
In **Bot** → **Privileged Gateway Intents**, enable:
- **Message Content Intent** — required to read message text in guilds
- **Server Members Intent** — needed for member lookups and allowlist matching
- Skip Presence Intent unless specifically needed

### 3c. Generate OAuth2 invite URL
In **OAuth2** → **URL Generator**:

**Scopes:**
- `bot`
- `applications.commands` (for slash commands)

**Minimum permissions:**
- View Channels
- Send Messages
- Read Message History
- Embed Links
- Attach Files
- Add Reactions (optional, recommended)

**Do not grant Administrator unless debugging.**

### 3d. Get IDs (enable Developer Mode first)
In Discord client: **User Settings → Advanced → Developer Mode → On**
- Right-click server name → **Copy Server ID** (guild ID)
- Right-click channel → **Copy Channel ID**
- Right-click user → **Copy User ID**

### 3e. Invite the bot
Open the OAuth2 URL from step 3c in a browser, select your server, authorize.

**Ref:** [Discord Channel Docs](https://docs.openclaw.ai/channels/discord)

---

## 4. Configure Moltbot for Discord

### 4a. Run the onboarding wizard (easiest path)
```bash
openclaw onboard --install-daemon
```
The wizard walks through gateway setup, auth, and channel providers including Discord.
It will prompt for your bot token.

### 4b. Manual configuration

**Environment variable (simplest):**
```bash
export DISCORD_BOT_TOKEN="your-bot-token-here"
```

**Or in config file** (`~/.openclaw/config.json5` or equivalent):
```json5
{
  channels: {
    discord: {
      enabled: true,
      token: "YOUR_BOT_TOKEN",
      // env var DISCORD_BOT_TOKEN is fallback if token not set here
    }
  }
}
```

### 4c. Start the gateway
```bash
# As a service (if installed via onboard --install-daemon):
openclaw gateway status

# Or manually in foreground:
openclaw gateway --port 18789 --verbose
```

Dashboard available at `http://127.0.0.1:18789/`

### 4d. Verify
```bash
openclaw status
openclaw health
openclaw channels status --probe   # audits permissions
```

**Ref:** [Getting Started](https://docs.openclaw.ai/start/getting-started)

---

## 5. DM Configuration

```json5
{
  channels: {
    discord: {
      dm: {
        enabled: true,
        policy: "pairing",        // "pairing" | "allowlist" | "open" | "disabled"
        allowFrom: ["userId"],    // user IDs, usernames, or "*" for anyone
      }
    }
  }
}
```

| Policy | Behavior |
|--------|----------|
| `pairing` (default) | Unknown users get a 1-hour pairing code; approve via `openclaw pairing approve discord <code>` |
| `allowlist` | Only users in `allowFrom` can message |
| `open` | Anyone can DM (requires `allowFrom: ["*"]`) |
| `disabled` | All DMs ignored |

**Important:** Discord requires bots and users to share a server before DMs work.

**Ref:** [Discord Channel Docs — DM Configuration](https://docs.openclaw.ai/channels/discord)

---

## 6. Guild (Server) Configuration

```json5
{
  channels: {
    discord: {
      guilds: {
        "GUILD_ID": {
          slug: "my-server",
          requireMention: true,    // bot only replies when @mentioned
          users: ["userId1"],      // user allowlist (empty = all)
          channels: {
            "CHANNEL_ID": {
              enabled: true,
              requireMention: false,
              users: ["userId1"],
              skills: ["skillName"],
              systemPrompt: "Extra context for this channel",
            },
            "*": { /* defaults for unlisted channels */ }
          }
        },
        "*": { requireMention: true }  // default for all guilds
      }
    }
  }
}
```

**Key points:**
- `requireMention: true` is recommended for shared channels
- When `channels` block is present, unlisted channels are **denied by default**
- When `channels` block is omitted, all guild channels are allowed
- Sessions are isolated per channel: `agent:<agentId>:discord:channel:<channelId>`

**Ref:** [Discord Channel Docs — Guild Configuration](https://docs.openclaw.ai/channels/discord)

---

## 7. Tool Actions & Permissions

Moltbot exposes Discord actions as tools the AI agent can use.

**Enabled by default:** reactions, stickers, emoji/sticker uploads, polls,
messages (read/send/edit/delete), threads, pins, search, member/role/channel info,
voice status, events

**Disabled by default:** `roles` (add/remove), `moderation` (timeout/kick/ban)

To toggle:
```json5
{
  channels: {
    discord: {
      actions: {
        moderation: false,  // keep off unless needed
        roles: false,
      }
    }
  }
}
```

**Ref:** [Discord Channel Docs — Tool Actions](https://docs.openclaw.ai/channels/discord)

---

## 8. Message Chunking & Media

```json5
{
  channels: {
    discord: {
      textChunkLimit: 2000,      // Discord's max (default)
      maxLinesPerMessage: 17,    // soft line limit
      chunkMode: "newline",      // "length" or "newline"
      mediaMaxMb: 8,             // inbound file size limit
      historyLimit: 20,          // guild message context window
    }
  }
}
```

**Ref:** [Discord Channel Docs](https://docs.openclaw.ai/channels/discord)

---

## 9. Security Notes

- **Treat the bot token like a password** — prefer `DISCORD_BOT_TOKEN` env var over config file
- Lock down config file permissions (`chmod 600`)
- Only grant the bot permissions it actually needs
- Moltbot runs commands on your local machine — **deploy on an isolated environment** that doesn't contain sensitive data
- Run `openclaw security audit --deep` to check your setup

**Refs:**
- [Security Guide](https://docs.openclaw.ai/gateway/security)
- [DEV Community Guide](https://dev.to/czmilo/moltbot-the-ultimate-personal-ai-assistant-guide-for-2026-d4e)

---

## 10. Troubleshooting

| Problem | Fix |
|---------|-----|
| "Used disallowed intents" | Enable Message Content + Server Members intents in Developer Portal; restart gateway |
| Bot connects but no replies in guild | Check Message Content Intent, channel permissions (View/Send/Read History), mention settings, allowlists |
| DMs don't work | Check `dm.enabled`, `dm.policy`, pending pairing approval, and that you share a server with the bot |
| `requireMention` at top level ignored | Must be under `channels.discord.guilds` or specific channel config |
| Permission audits fail with slugs | Use numeric channel IDs in config |

**Diagnostic commands:**
```bash
openclaw doctor                       # actionable warnings
openclaw channels status --probe      # permission audit
openclaw gateway --force              # force restart if stuck
```

**Ref:** [Discord Channel Docs — Troubleshooting](https://docs.openclaw.ai/channels/discord)

---

## 11. Azure / Cloud Deployment (alternative to local)

For always-on hosting via Azure Container Apps:
```bash
azd env set DISCORD_BOT_TOKEN "your-token"
azd env set DISCORD_ALLOWED_USERS "your-discord-user-id"
azd up
```
Estimated cost: ~$40–60/month.

DigitalOcean also offers a 1-click Droplet deployment.

**Refs:**
- [Azure Deploy Guide](https://techcommunity.microsoft.com/blog/appsonazureblog/deploy-moltbot-to-azure-container-apps-your-247-ai-assistant-in-30-minutes/4490611)
- [DigitalOcean Docs](https://docs.digitalocean.com/products/marketplace/catalog/moltbot/)

---

## Quick-Start Checklist

- [ ] Install Node.js 22+
- [ ] `npm install -g openclaw@latest`
- [ ] Create Discord app + bot at https://discord.com/developers/applications
- [ ] Enable **Message Content Intent** and **Server Members Intent**
- [ ] Generate OAuth2 URL with `bot` + `applications.commands` scopes
- [ ] Invite bot to your server
- [ ] `export DISCORD_BOT_TOKEN="your-token"`
- [ ] `openclaw onboard --install-daemon`
- [ ] `openclaw channels status --probe` to verify
- [ ] Send a message in your server mentioning the bot
