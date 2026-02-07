# OpenClaw Cognitive Architecture Framework

Complete reified hypergraph ontology for understanding and comparing agent cognitive architectures.

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

## Requirements

- Python 3 (for HTTP server)
- Modern web browser (Chrome, Firefox, Safari)
- That's it!

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
