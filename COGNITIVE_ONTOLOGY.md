# Cognitive Architecture Ontology

**Purpose:** A framework for describing agent cognitive systems, independent of implementation.

---

## Core Taxonomy

### 1. INPUT PROCESSING

#### Perception
**Definition:** How information enters the cognitive system
**Function:** Sensory input, pattern recognition
**Key Questions:**
- What information sources exist?
- How is raw input interpreted?
- What modalities are supported?

#### Attention
**Definition:** Filtering and prioritization mechanisms
**Function:** Selective attention, resource allocation
**Key Questions:**
- What gets processed vs ignored?
- How are priorities determined?
- What triggers focus shifts?

---

### 2. MEMORY SYSTEMS

#### Working Memory
**Definition:** Active context being processed
**Characteristics:**
- Limited capacity
- Temporary/ephemeral
- High accessibility
- Lost if not consolidated

**Key Metrics:** Capacity (tokens, items), retention duration

#### Episodic Memory
**Definition:** Event logs - autobiographical memory
**Characteristics:**
- Time-stamped
- Contextual
- Chronological ordering
- "What happened when"

**Structure:** Sequential events with temporal/spatial context

#### Semantic Memory
**Definition:** Facts, concepts, general knowledge
**Characteristics:**
- Decontextualized
- Organized by meaning
- "What I know" (not "when I learned it")
- Generalizable

**Structure:** Concepts, relationships, schemas

#### Procedural Memory
**Definition:** Skills and how-to knowledge
**Characteristics:**
- Often implicit
- "Knowing how" vs "knowing that"
- Activated automatically
- Compiled routines

**Structure:** Procedures, scripts, heuristics

---

### 3. COGNITIVE PROCESSING

#### Reasoning
**Definition:** Drawing inferences and conclusions
**Functions:**
- Deductive reasoning (logical conclusions)
- Inductive reasoning (pattern generalization)
- Abductive reasoning (best explanation)
- Analogical reasoning (transfer from similar cases)

#### Planning
**Definition:** Future-oriented thinking
**Functions:**
- Goal setting
- Strategy formation
- Resource allocation
- Temporal sequencing

#### Problem-Solving
**Definition:** Overcoming obstacles to achieve goals
**Approaches:**
- Trial and error
- Means-end analysis
- Constraint satisfaction
- Heuristic search

#### Decision-Making
**Definition:** Selecting among alternatives
**Factors:**
- Utility assessment
- Uncertainty handling
- Trade-off evaluation
- Preference integration

---

### 4. OUTPUT & ACTION

#### Action Selection
**Definition:** Choosing which actions to execute
**Mechanisms:**
- Behavior arbitration
- Priority ranking
- Conflict resolution

#### Execution
**Definition:** Carrying out selected actions
**Types:**
- Communication (linguistic output)
- Tool use (instrumental actions)
- Environmental modification

---

### 5. META-COGNITION

#### Self-Monitoring
**Definition:** Awareness of own cognitive processes
**Functions:**
- Performance tracking
- Error detection
- Confidence assessment

#### Strategy Adjustment
**Definition:** Modifying approach based on feedback
**Functions:**
- Recognizing when current strategy fails
- Switching strategies
- Learning from mistakes

#### Reflection
**Definition:** Deliberate examination of experiences
**Functions:**
- Pattern extraction
- Generalization
- Knowledge consolidation

---

## OpenClaw Mapping

| Cognitive Component | OpenClaw Implementation |
|---------------------|------------------------|
| **Perception** | Multi-channel input (Discord, WhatsApp, etc.) |
| **Attention** | `requireMention`, `groupPolicy`, DM pairing |
| **Working Memory** | Session context (~130k tokens, ephemeral) |
| **Episodic Memory** | Daily logs (`memory/YYYY-MM-DD.md`) |
| **Semantic Memory** | `MEMORY.md` + vector search |
| **Procedural Memory** | Skills system (progressive disclosure) |
| **Reasoning** | LLM inference with system prompt |
| **Planning** | Multi-turn conversations, heartbeat scheduling |
| **Action Selection** | Tool use decisions |
| **Execution** | Tool calls (bash, browser, skills, channel actions) |
| **Meta-Cognition** | Heartbeat system, session reset policies |

---

## Key Architectural Patterns

### Pattern 1: Multi-Tier Memory Hierarchy
- **Working** (ephemeral, limited) ↔ **Episodic** (persistent, chronological) ↔ **Semantic** (curated, searchable)
- Information flows: immediate → logged → consolidated → indexed

### Pattern 2: Progressive Disclosure
- Index (metadata) vs Content (full details)
- Load on-demand rather than upfront
- Reduces cognitive load while maintaining access

### Pattern 3: Attention Gating
- Not all input reaches cognition
- Rule-based filtering before processing
- Prevents overload, maintains focus

### Pattern 4: Meta-Cognitive Loops
- Periodic self-checks (heartbeat)
- Automatic maintenance (compaction, reset)
- Self-awareness without user intervention

---

## Using This Ontology

### To Describe Any Agent System:

1. **Map each cognitive component** to your implementation
2. **Identify which patterns** your system uses
3. **Note unique innovations** not captured by standard ontology
4. **Visualize information flow** through the components

### Questions to Ask:

- How does information enter? (Perception)
- What gets filtered out? (Attention)
- Where is active context held? (Working Memory)
- How are events logged? (Episodic)
- How is knowledge organized? (Semantic)
- Where are skills stored? (Procedural)
- How are decisions made? (Reasoning)
- How are actions executed? (Execution)
- How does the system monitor itself? (Meta-Cognition)

---

## Extensions & Variations

This ontology can be extended with:

- **Social Cognition**: Theory of mind, multi-agent interaction
- **Emotional Processing**: Affect recognition, mood states
- **Learning**: Adaptation mechanisms, knowledge acquisition
- **Embodiment**: Physical/sensorimotor integration
- **Temporal Dynamics**: Time perception, temporal reasoning

---

*This ontology draws from cognitive science, psychology, and AI research to provide a unified framework for understanding agent architectures.*
