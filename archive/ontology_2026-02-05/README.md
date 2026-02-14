# Archived: Cognitive Architecture Ontology (2026-02-05)

## What This Is

These files were created during a single Claude Code session on 2026-02-05 to build a cognitive architecture ontology for OpenClaw/Moltbot. They represent the first iteration of what became the `agent_ontology` project.

## Why Archived

The `agent_ontology` project (`/home/brian/projects/agent_ontology`) has completely superseded this work:

- **Ontology format**: These used freeform markdown + OWL/TTL. agent_ontology uses 32 executable YAML specs with JSON Schema validation.
- **Visualizations**: These used standalone D3.js HTML files. agent_ontology has `spec-viewer.html` that renders directly from the YAML specs.
- **Tooling**: These had no validation or code generation. agent_ontology has `validate_specs.py`, `generate_code.py`, and evolutionary search.
- **Coverage**: These covered ~16 cognitive extensions informally. agent_ontology has 32 formally specified components with traits, ports, and lifecycle hooks.

## Contents

| File | Description |
|------|-------------|
| `COGNITIVE_ONTOLOGY.md` | Conceptual framework (reified hypergraph) |
| `ONTOLOGY_README.md` | Complete ontology reference |
| `ONTOLOGY_STRUCTURE.md` | Core + Extensions design |
| `QUICK_START.md` | Framework usage guide |
| `cognitive-architecture.ttl` | Formal OWL ontology |
| `cognitive-network.json` | Network graph data |
| `agent-instances.json` | Agent implementations for comparison |
| `cognitive-architecture.html` | Architecture visualization |
| `agent-comparison.html` | Side-by-side agent comparison |
| `cognitive-network.html` | Full ontology network graph |
| `openclaw-cognitive.html` | Main interactive cognitive graph |
| `openclaw-architecture.html` | Scenario-based flow visualization |

## Do Not Move to agent_ontology

These files are outdated and would add clutter. The agent_ontology project has its own representations that are more rigorous and tooling-integrated.
