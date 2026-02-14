# Cognitive Architecture Ontology - Complete Documentation

## Overview

This is a **formal ontology** for describing agent cognitive architectures using a **reified hypergraph** model. Unlike simple taxonomies, this captures:

- **Components** as nodes
- **Relationships** as nodes (reification)
- **Roles** that participants play
- **Properties** of both components and relationships
- **Constraints** and logical axioms

## Files

| File | Format | Purpose |
|------|--------|---------|
| `cognitive-architecture.ttl` | Turtle/OWL | Formal ontology (machine-readable) |
| `cognitive-network.json` | JSON | Network representation for visualization |
| `cognitive-network.html` | HTML/D3.js | Interactive graph visualization |
| `COGNITIVE_ONTOLOGY.md` | Markdown | Conceptual documentation |

## Why Reified Hypergraph?

### Traditional Graph (Binary Relationships)
```
A --edge--> B
```
**Limitations:**
- Only binary relationships
- Can't add properties to edges
- Can't represent n-ary relationships
- Can't express role information

### Reified Hypergraph (Relationships as Nodes)
```
A --participatesIn--> Relationship_Event
Relationship_Event --hasRole(source)--> A
Relationship_Event --hasRole(target)--> B
Relationship_Event --hasTrigger--> "capacity_exceeded"
Relationship_Event --hasLatency--> 100ms
```

**Advantages:**
- Relationships are first-class citizens
- Can have properties (trigger, latency, etc.)
- Multiple participants with specific roles
- Queryable and analyzable
- Temporal/causal information

## Core Structure

### 1. Cognitive Components (17 categories)

#### Input Processing
- **Perception** - Sensory input and pattern recognition
- **Attention** - Selective filtering and prioritization

#### Memory Systems
- **Working Memory** - Limited capacity, ephemeral (session context)
- **Episodic Memory** - Time-stamped event logs (daily files)
- **Semantic Memory** - Decontextualized facts (MEMORY.md)
- **Procedural Memory** - Skills and how-to knowledge (progressive disclosure)

#### Cognitive Processing
- **Reasoning** - Inference, decision-making
- **Planning** - Future-oriented thinking
- **Temporal Reasoning** - Time-based reasoning
- **Causal Reasoning** - Cause-effect understanding

#### Goal Management (BDI Model)
- **Goal System** - Beliefs, Desires, Intentions

#### Error Management
- **Error Handling** - Detection, recovery, retry

#### Context
- **Context Management** - Building, switching, maintaining

#### Action
- **Execution** - Tool use and action execution

#### Meta
- **Meta-Cognition** - Self-monitoring, strategy adjustment

#### Learning
- **Learning** - Knowledge and skill acquisition

#### Social
- **Social Cognition** - Multi-agent coordination, theory of mind

#### Transparency
- **Explanation** - Trace generation, justification

### 2. Relationship Categories

#### Information Flow
Direction of data movement
- `feedsInto`, `consolidatesTo`, `retrievesFrom`

#### Control Flow
Activation and regulation
- `activates`, `inhibits`, `triggers`

#### Temporal
Time-based relationships
- `precedes`, `concurrent`

#### Structural
Compositional relationships
- `hasPart`, `isPartOf`

#### Dependency
Requirements
- `requires`, `dependsOn`

### 3. Relationship Events (Reified)

| Event | Type | Description |
|-------|------|-------------|
| Input Flow | Information | Perception → Working Memory |
| Attention Gate | Control | Attention filters input |
| Memory Consolidation | Consolidation | Working → Episodic |
| Semantic Extraction | Consolidation | Episodic → Semantic |
| Memory Retrieval | Retrieval | Semantic → Working |
| Skill Loading | Retrieval | Procedural → Working |
| Action Selection | Control | Reasoning → Execution |
| Error Detection | Control | Execution failure detected |
| Context Switch | Control | Session change |
| Self-Monitoring | Control | Meta-cognition heartbeat |

### 4. Roles

Participants in relationships have roles:

- **Source** - Originator of information flow
- **Target** - Recipient of information flow
- **Trigger** - Initiator of process
- **Modulator** - Influences but doesn't control
- **Controller** - Directs or regulates

### 5. Properties

#### Data Properties (Component Attributes)
- `hasCapacity` - Memory capacity (tokens/items)
- `hasLatency` - Processing latency
- `hasAccuracy` - Accuracy metric (0.0-1.0)
- `isEphemeral` - Whether data persists
- `hasRetentionPolicy` - Retention rules

#### Object Properties (Relationships)
- See "Relationship Categories" above

## Using the Visualization

### Open the Interactive Graph
```bash
xdg-open /home/brian/projects/moltbot/cognitive-network.html
```

### Features
- **Drag nodes** to rearrange layout
- **Click nodes** to see details in sidebar
- **Filter** by relationship type (checkboxes)
- **Toggle labels** to reduce clutter
- **Reset layout** to re-simulate
- **Zoom/pan** with mouse

### Visual Encoding
- **Large circles** = Cognitive components
- **Small circles** = Relationship events (reified edges)
- **Colors** = Category (see legend)
- **Edge colors** = Relationship type
- **Roles** = Labels on edges

## Querying the Ontology (SPARQL)

You can query the `.ttl` file using SPARQL:

```sparql
# Find all components that feed into Working Memory
PREFIX : <http://openclaw.ai/ontology/cognitive#>

SELECT ?component ?relationship
WHERE {
  ?relationship :hasTarget :workingMemoryInstance .
  ?relationship :hasSource ?component .
}
```

```sparql
# Find all consolidation events
PREFIX : <http://openclaw.ai/ontology/cognitive#>

SELECT ?event ?source ?target ?trigger
WHERE {
  ?event a :ConsolidationEvent .
  ?event :hasSource ?source .
  ?event :hasTarget ?target .
  ?event :hasTrigger ?trigger .
}
```

## Extending the Ontology

### Adding a New Component

1. **In Turtle (.ttl):**
```turtle
:NewComponent rdf:type owl:Class ;
    rdfs:subClassOf :CognitiveComponent ;
    rdfs:label "New Component" ;
    rdfs:comment "Description of new component" .
```

2. **In JSON:**
```json
{
  "id": "new_component",
  "label": "New Component",
  "type": "component",
  "category": "new_category",
  "description": "Description"
}
```

3. **Update categories:**
```json
"new_category": {
  "color": "#hexcolor",
  "label": "New Category"
}
```

### Adding a New Relationship

1. **Define the property in Turtle:**
```turtle
:newRelationship rdf:type owl:ObjectProperty ;
    rdfs:label "new relationship" ;
    rdfs:comment "Description" .
```

2. **Create reified event:**
```turtle
:newEvent rdf:type :RelationshipEvent ;
    rdfs:label "New Event" ;
    :hasSource :componentA ;
    :hasTarget :componentB ;
    :hasTrigger "some_trigger" .
```

3. **Add to JSON:**
```json
{
  "id": "new_event",
  "label": "New Event",
  "type": "relationship_event",
  "relationship_type": "new_type",
  "trigger": "some_trigger"
}
```

4. **Add edges:**
```json
{
  "source": "componentA",
  "target": "new_event",
  "role": "source",
  "label": "participates"
},
{
  "source": "new_event",
  "target": "componentB",
  "role": "target",
  "label": "affects"
}
```

## Mapping Real Systems

### OpenClaw Example

| Component | Implementation |
|-----------|----------------|
| Perception | Multi-channel input (Discord, WhatsApp) |
| Attention | `requireMention`, `groupPolicy`, DM pairing |
| Working Memory | Session context (~130k tokens) |
| Episodic Memory | `memory/YYYY-MM-DD.md` |
| Semantic Memory | `MEMORY.md` + vector search |
| Procedural Memory | Skills (progressive disclosure) |
| Reasoning | LLM inference |
| Execution | Tool calls (bash, browser, skills) |
| Meta-Cognition | Heartbeat system |

### Your System

Create a new instance in the Turtle file:

```turtle
:MyAgent rdf:type :CognitiveAgent ;
    :hasComponent :myPerception ;
    :hasComponent :myWorkingMemory .

:myPerception rdf:type :Perception ;
    :implementedAs "Custom input parser" .

:myWorkingMemory rdf:type :WorkingMemory ;
    :hasCapacity 50000 ;
    :isEphemeral true .
```

## Missing Components (Known Gaps)

This ontology is **not complete**. Missing areas:

1. **Emotion/Affect** - Emotional processing
2. **Motivation** - Drive systems, reward
3. **Creative Generation** - Novel idea generation
4. **Counterfactual Reasoning** - "What if" scenarios
5. **Analogical Reasoning** - Transfer learning
6. **Uncertainty Representation** - Probabilistic reasoning
7. **Multi-scale Temporal** - Different time granularities
8. **Embodiment** - Physical/sensorimotor grounding

## Relationship Type Taxonomy

Current types are **incomplete**. Should add:

- **Transformation** - How information changes form
- **Encoding/Decoding** - Format conversion
- **Compression/Expansion** - Information density
- **Validation** - Correctness checking
- **Prioritization** - Ranking/ordering
- **Aggregation** - Combining multiple sources
- **Filtering** - Removal based on criteria

## Future Work

### Phase 1: Complete Ontology
- Add missing cognitive components
- Expand relationship taxonomy
- Add more role types
- Define cardinality constraints

### Phase 2: Validation
- Test against multiple agent systems
- Identify edge cases
- Refine definitions
- Add formal axioms

### Phase 3: Tooling
- SPARQL query interface
- Ontology diff tool
- Validation checker
- Auto-mapper from code

### Phase 4: Applications
- Agent comparison tool
- Architecture recommendation
- Performance prediction
- Debugging assistant

## References

### Cognitive Science
- Working Memory Model (Baddeley & Hitch)
- Episodic/Semantic Memory (Tulving)
- BDI Architecture (Rao & Georgeff)

### AI/Agent Systems
- SOAR Architecture
- ACT-R Cognitive Architecture
- Belief-Desire-Intention Model

### Knowledge Representation
- OWL (Web Ontology Language)
- RDF (Resource Description Framework)
- SPARQL Query Language

## License & Attribution

This ontology is open for use and extension. When using:

1. Cite this work
2. Document extensions
3. Share improvements
4. Maintain attribution chain

---

**Version:** 1.0
**Last Updated:** 2026-02-05
**Maintainer:** OpenClaw Project
**Status:** Work in Progress - Not Complete
