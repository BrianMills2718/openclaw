# Cognitive Architecture Ontology - Modular Structure

## Design Philosophy

**Goal:** A reified hypergraph ontology that can:
1. Describe ANY cognitive architecture (generality)
2. Precisely capture OpenClaw's specific implementation (specificity)
3. Enable visual comparison across different agent systems (comparison)

**Approach:** Core + Extensions + Instances

---

## Structure

```
┌─────────────────────────────────────────────────────┐
│                  UNIVERSAL CORE                      │
│  (Minimal components present in every agent)         │
│  - Perception, Memory, Reasoning, Action             │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│               EXTENSION MODULES                      │
│  (Optional capabilities some agents have)            │
│  - Error Handling, Social, Learning, Emotion, etc.   │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                   INSTANCES                          │
│  (Specific agent implementations)                    │
│  - OpenClaw, AutoGPT, LangGraph, Claude.ai, etc.     │
└─────────────────────────────────────────────────────┘
```

---

## Level 1: Universal Core

**Components every agent must have** (if it doesn't have these, it's not really an agent):

### Input
- **Perception** - How information enters the system
  - *Even passive systems receive queries/prompts*

### Memory
- **Working Memory** - Active context being processed
  - *Even stateless APIs have a "context window"*

### Processing
- **Reasoning** - Drawing conclusions from available information
  - *Core cognitive function*

### Output
- **Action/Execution** - Affecting the world (even if just text output)
  - *Responses, tool calls, etc.*

**Minimal Relationships:**
- Input → Working Memory (perception feeds into active context)
- Working Memory ↔ Reasoning (bidirectional)
- Reasoning → Action (decisions lead to outputs)

**This is the minimal graph** - if a system lacks any of these, it's questionable whether it's an "agent."

---

## Level 2: Extension Modules

**Optional capabilities that differentiate architectures:**

### Memory Extensions
- **Episodic Memory** - Event logs over time
- **Semantic Memory** - Factual knowledge store
- **Procedural Memory** - Skills/how-to knowledge
- **Vector Memory** - Semantic search capability

### Processing Extensions
- **Planning** - Multi-step future-oriented thinking
- **Temporal Reasoning** - Time-based logic
- **Causal Reasoning** - Cause-effect understanding
- **Analogical Reasoning** - Transfer learning

### Control Extensions
- **Attention** - Selective filtering/prioritization
- **Goal Management** - BDI (Beliefs, Desires, Intentions)
- **Error Handling** - Detection, recovery, retry
- **Context Management** - Switching, building, maintaining

### Meta Extensions
- **Meta-Cognition** - Self-monitoring, strategy adjustment
- **Learning** - Adaptation, knowledge acquisition
- **Explanation** - Trace generation, justification

### Social Extensions
- **Social Cognition** - Multi-agent coordination
- **Theory of Mind** - Understanding other agents
- **Communication Pragmatics** - Conversational understanding

### Affective Extensions (rarely used)
- **Emotion** - Affective processing
- **Motivation** - Intrinsic drives
- **Personality** - Consistent behavioral traits

### Embodiment Extensions (for robots/physical agents)
- **Sensorimotor** - Physical sensing and movement
- **Spatial Reasoning** - Navigation, 3D understanding
- **Motor Control** - Action execution in physical space

---

## Level 3: Instances (Specific Agents)

### Instance: OpenClaw

**Includes:**
- **Core:** ✓ All (Perception, Working Memory, Reasoning, Action)
- **Memory Extensions:** ✓ Episodic, ✓ Semantic, ✓ Procedural, ✓ Vector
- **Processing Extensions:** ✓ Planning, ✓ Temporal Reasoning
- **Control Extensions:** ✓ Attention, ✓ Goal Management, ✓ Error Handling, ✓ Context Management
- **Meta Extensions:** ✓ Meta-Cognition
- **Social Extensions:** ✓ Social Cognition

**Excludes:**
- Affective Extensions (no emotion/motivation)
- Embodiment Extensions (not physical)
- Learning Extension (uses pre-trained LLM, no online learning)

**Specific Implementation:**
```json
{
  "agent": "OpenClaw",
  "core": {
    "perception": "Multi-channel input (Discord, WhatsApp, Telegram, etc.)",
    "working_memory": "Session context (~130k tokens, ephemeral)",
    "reasoning": "LLM inference (Claude/GPT)",
    "action": "Tool calls (bash, browser, skills), channel actions"
  },
  "extensions": {
    "episodic_memory": "memory/YYYY-MM-DD.md (daily logs)",
    "semantic_memory": "MEMORY.md + vector search",
    "procedural_memory": "Skills (progressive disclosure, 700+)",
    "attention": "requireMention, groupPolicy, DM pairing",
    "goal_management": "Loop conditions, early termination",
    "error_handling": "try/catch/finally, retry with backoff",
    "context_management": "Session switching, explicit context flow",
    "meta_cognition": "Heartbeat (30min), session reset policies",
    "social_cognition": "Multi-agent routing, coordination",
    "temporal_reasoning": "Cron, heartbeat scheduling"
  }
}
```

### Instance: AutoGPT (hypothetical)

**Includes:**
- **Core:** ✓ All
- **Memory Extensions:** ✓ Vector (Pinecone), ✓ Episodic (logs)
- **Processing Extensions:** ✓ Planning (task decomposition)
- **Control Extensions:** ✓ Goal Management (explicit goals)

**Excludes:**
- Semantic Memory (no curated knowledge base)
- Procedural Memory (no skill system)
- Attention (processes everything)
- Error Handling (limited retry)
- Social Cognition (single agent)

**Key Difference from OpenClaw:**
- No multi-channel support
- No session isolation
- Goal-driven (vs reactive)
- Limited memory architecture

### Instance: Claude.ai (Web Interface)

**Includes:**
- **Core:** ✓ All
- **Memory Extensions:** ✓ Working Memory only (conversation context)
- **Processing Extensions:** ✓ Planning (multi-turn)

**Excludes:**
- Episodic Memory (no persistent logs)
- Semantic Memory (relies on pre-training)
- Procedural Memory (no skill loading)
- Most extensions (minimal architecture)

**Key Difference:**
- Stateless between conversations
- No persistent memory
- No tool use (web interface version)
- Pure LLM reasoning

---

## Comparison Framework

### Comparison Dimensions

1. **Coverage** - Which extensions does each agent use?
2. **Memory Hierarchy** - How many memory tiers?
3. **Control Complexity** - How sophisticated is control flow?
4. **Social Capability** - Single vs multi-agent?
5. **Persistence** - What survives between sessions?

### Comparison Matrix

| Component | OpenClaw | AutoGPT | Claude.ai | LangGraph |
|-----------|----------|---------|-----------|-----------|
| **Core** | | | | |
| Perception | Multi-channel | File/Web | Text only | Custom |
| Working Memory | 130k session | Task context | Conversation | Graph state |
| Reasoning | LLM | LLM + loop | LLM | LLM + graph |
| Action | Tools + channels | Tools | Text only | Custom tools |
| **Extensions** | | | | |
| Episodic Memory | ✓ Daily files | ✓ Logs | ✗ | ✗ |
| Semantic Memory | ✓ MEMORY.md | ✗ | ✗ | △ Optional |
| Procedural Memory | ✓ Skills (700+) | ✗ | ✗ | △ Custom |
| Attention | ✓ Multi-filter | ✗ | ✗ | △ Custom |
| Goal Management | ✓ BDI-lite | ✓ Explicit | ✗ | ✓ Graph nodes |
| Error Handling | ✓ try/catch/retry | △ Basic retry | ✗ | ✓ Graph paths |
| Context Management | ✓ Session switching | △ Limited | ✗ | ✓ State management |
| Meta-Cognition | ✓ Heartbeat | ✗ | ✗ | ✗ |
| Social Cognition | ✓ Multi-agent | ✗ | ✗ | △ Custom |

**Legend:** ✓ = Fully supported | △ = Partially supported | ✗ = Not supported

---

## Visual Comparison Strategy

### 1. Component Coverage Radar Chart
Shows which extensions each agent implements (0-100% coverage)

### 2. Side-by-Side Hypergraphs
Show actual graph structure for each agent with:
- Shared components highlighted
- Unique components colored differently
- Relationship density visible

### 3. Diff View
Overlay two agents' graphs:
- Green = Component A has, B doesn't
- Red = Component B has, A doesn't
- Blue = Both have
- Gray = Neither has

### 4. Architecture Patterns
Identify common patterns:
- **Pattern: Reactive** (Perception → Reasoning → Action)
- **Pattern: Deliberative** (Goal → Planning → Reasoning → Action)
- **Pattern: Hybrid** (Both reactive and deliberative paths)
- **Pattern: Multi-tier Memory** (Working → Episodic → Semantic)

---

## Use Cases

### Use Case 1: Understanding OpenClaw
1. Load OpenClaw instance graph
2. Explore components and relationships
3. Trace information flow through system
4. Identify architectural decisions

### Use Case 2: Comparing Agents
1. Load multiple instance graphs
2. Use comparison matrix
3. Identify unique capabilities
4. Understand trade-offs

### Use Case 3: Designing New Agent
1. Start with universal core
2. Select extensions based on requirements
3. Compare to existing agents
4. Validate completeness

### Use Case 4: Debugging/Optimization
1. Visualize actual vs intended architecture
2. Identify bottlenecks (relationship density)
3. Find missing error handling paths
4. Optimize information flow

---

## Next Steps

### To Complete This Framework:

1. **Create modular ontology files:**
   - `core.ttl` - Universal components
   - `ext-memory.ttl` - Memory extensions
   - `ext-control.ttl` - Control extensions
   - `ext-social.ttl` - Social extensions
   - etc.

2. **Create instance files:**
   - `instance-openclaw.ttl` - OpenClaw specifics
   - `instance-autogpt.ttl` - AutoGPT specifics
   - etc.

3. **Create comparison visualizations:**
   - Side-by-side graphs
   - Diff view
   - Coverage radar
   - Pattern detector

4. **Build query interface:**
   - "Show me all agents with episodic memory"
   - "What's different between OpenClaw and AutoGPT?"
   - "Which pattern does this agent follow?"

---

## Benefits of This Approach

### For OpenClaw Development:
- ✓ Visual architecture documentation
- ✓ Identify missing components
- ✓ Compare to other frameworks
- ✓ Communicate design decisions

### For General Agent Work:
- ✓ Understand any agent quickly
- ✓ Compare architectures objectively
- ✓ Identify patterns and anti-patterns
- ✓ Design new agents systematically

### For Research:
- ✓ Common vocabulary
- ✓ Quantitative comparison
- ✓ Pattern taxonomy
- ✓ Architectural evolution tracking

---

**This gives you both:**
1. **Precision** for OpenClaw (via specific instance graph)
2. **Generality** for any agent (via core + extensions)
3. **Comparison** across systems (via shared ontology)

The reified hypergraph representation works perfectly because it handles varying complexity - simple agents have sparse graphs, complex ones have dense graphs, but they're all comparable.
