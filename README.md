# Moltbot / OpenClaw Project

**Complete OpenClaw setup, research, and cognitive architecture framework**

This repository contains:
1. ✅ **OpenClaw Discord integration** - Fully working setup
2. ✅ **Cognitive architecture ontology** - Reified hypergraph framework
3. ✅ **Interactive visualizations** - Drag, click, explore
4. ✅ **Agent comparison tools** - Compare any agent architectures
5. ✅ **Complete documentation** - Setup notes, status, next steps

## Quick Start on New Computer

### 1. Get the files
```bash
# If using git (recommended)
git clone <your-repo-url>
cd moltbot

# OR just copy this entire directory
```

### 2. Start HTTP server
```bash
python3 -m http.server 8000
```

### 3. Open visualizations
```bash
# Main interactive cognitive architecture (START HERE)
http://localhost:8000/openclaw-cognitive.html

# Agent comparison tool
http://localhost:8000/agent-comparison.html

# Alternative views
http://localhost:8000/openclaw-architecture.html
http://localhost:8000/cognitive-network.html
```

## What's Included

### Interactive Visualizations
- **openclaw-cognitive.html** - ⭐ Main tool: Drag nodes, click for details, shows cognitive loops
- **agent-comparison.html** - Compare OpenClaw vs AutoGPT vs Claude.ai vs Minimal
- **openclaw-architecture.html** - Scenario-based flows (Discord message, memory, skills, heartbeat)
- **cognitive-network.html** - Full ontology network graph

### Data Files
- **agent-instances.json** - Concrete agent implementations for comparison
- **cognitive-network.json** - Network graph data
- **cognitive-architecture.ttl** - Formal OWL ontology (SPARQL queryable)

### Documentation
- **QUICK_START.md** - How to use the framework
- **ONTOLOGY_STRUCTURE.md** - Core + Extensions design
- **ONTOLOGY_README.md** - Complete reference
- **COGNITIVE_ONTOLOGY.md** - Conceptual framework

## Project Status

**OpenClaw:** ✅ Fully operational
- Discord bot active and responding
- Gateway running on port 18789
- Model: OpenAI Codex (gpt-5.2)
- Memory system initialized
- Session management working

**See:** `OPENCLAW_STATUS.md` for complete current state and next steps

## All Files Included

### Setup & Status
- **DISCORD_SETUP_NOTES.md** - Complete Discord integration guide
- **OPENCLAW_STATUS.md** - Current status, config, next steps

### Cognitive Architecture Framework
- **COGNITIVE_ONTOLOGY.md** - Conceptual framework
- **ONTOLOGY_STRUCTURE.md** - Core + Extensions design
- **ONTOLOGY_README.md** - Complete reference
- **QUICK_START.md** - How to use the framework
- **cognitive-architecture.ttl** - Formal OWL ontology

### Interactive Visualizations
- **openclaw-cognitive.html** - ⭐ Main interactive graph
- **agent-comparison.html** - Compare multiple agents
- **openclaw-architecture.html** - Scenario-based flows
- **cognitive-network.html** - Full ontology network

### Data Files
- **agent-instances.json** - OpenClaw, AutoGPT, Claude.ai, Minimal
- **cognitive-network.json** - Network graph data

## Requirements

- Python 3 (for HTTP server)
- Modern web browser (Chrome, Firefox, Safari)
- That's it! (OpenClaw itself not required to view visualizations)

## Key Features

✅ **Reified Hypergraph** - Relationships are nodes with roles
✅ **Fully Interactive** - Drag nodes, click for rich details
✅ **Shows Cognitive Loops** - Working Memory ↔ Reasoning, Error Recovery, etc.
✅ **Concrete Examples** - Real OpenClaw implementation details
✅ **Comparison Framework** - Map any agent to same ontology

## Understanding the Ontology

**Relation vs Role (Dinner Party Analogy):**
- **Relation:** "Having dinner together" (the event)
- **Roles:** Host, guest, cook, cleaner (how people participate)

Same in OpenClaw:
- **Relation:** "Memory Consolidation Event"
- **Roles:** Working Memory (source), Episodic Memory (target), Context Manager (trigger)

## Files Created During Session

All files in this directory were created during a single Claude Code session to build a complete cognitive architecture ontology for OpenClaw/Moltbot.

Session date: 2026-02-05
