# RAG Chatbot with Neo4j Vector Search

This directory contains a Retrieval-Augmented Generation (RAG) chatbot that integrates with Neo4j knowledge graph for both text-based and vector similarity search, with intelligent query preprocessing.

## Features

### 1. **Smart Query Preprocessing** ⭐ ENHANCED
- **Intent Detection**: Automatically classifies user queries into categories:
  - `factual_lookup`: Looking for specific facts or information
  - `comparison`: Comparing multiple entities or concepts
  - `explanation`: Asking for explanation or understanding
  - `procedure`: Asking how to do something
  - `troubleshooting`: Trying to solve a problem
  - `general_conversation`: General chat or greeting
- **Answer-Relevant Entity Extraction** ⭐ ENHANCED: Identifies entities that can help answer the question
  - **Main Entities**: Primary subjects mentioned in the question
  - **Related Entities**: Concepts that might exist in the graph and help answer the question
  - **Contextual Entities**: Background concepts providing necessary context
  - Prioritizes the most important entities first
  - Example: For "temperature cycling vs thermal shock", extracts 15+ entities including standards, testing methodologies, and related concepts
- **Automatic Processing**: 2 LLM calls (intent + entity extraction)

### 2. **Triple Search Capabilities**
- **Text-based Search** (`neo4j_retrieval_tool`): Searches for entities by name, official_name, or aliases using keyword matching
- **Vector Similarity Search** (`neo4j_vector_search_tool`): Semantic search using embedding vectors stored in Neo4j nodes
- **Entity Graph Search** (`neo4j_entity_graph_search_tool`): ⭐ PRIMARY - Explores entities and their relationships in the graph
  - Starts from extracted entities
  - Traverses 1-2 levels of relationships
  - Returns comprehensive graph neighborhood context
  - Used FIRST when entities are detected

### 3. **ReAct Agent Architecture** ⭐ NEW
- Uses LangGraph's `create_react_agent` for intelligent tool usage
- **ReAct Pattern**: Combines Reasoning and Acting in a loop
  - Agent reasons about what tool to call
  - Executes the tool
  - Observes the result
  - Reasons about next steps
  - Repeats until it has enough information
- **Benefits**:
  - More intelligent tool selection
  - Can call multiple tools in sequence
  - Self-correcting: can retry or use different tools if first attempt fails
  - Explicit reasoning steps

### 4. **LangGraph Architecture**
- **Preprocessing Node**: Detects intent and generates sub-questions
- **Agent Node**: ReAct agent that handles all tool calling and reasoning
- **Simplified Flow**: preprocess_query → agent → END
  - No manual routing needed
  - Agent internally manages the tool-calling loop

## Installation

```bash
# Install required dependencies
pip install langchain-openai langchain-core langgraph neo4j sentence-transformers python-dotenv
```

## Configuration

Create a `.env` file with the following variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password
NEO4J_DATABASE=neo4j

# Embedding Model Configuration
# IMPORTANT: Must match the model used to generate vectors in Neo4j!
# For Ollama models (e.g., nomic-embed-text):
EMBEDDING_MODEL=nomic-embed-text
# For sentence-transformers models:
# EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# Ollama Configuration (if using Ollama embeddings)
OLLAMA_BASE_URL=http://localhost:11434
```

**Important Notes:**
- The embedding model **must** match the model used to generate `_name_vector` and `_desc_vector` in your Neo4j database
- If you used `nomic-embed-text` (or `text-embedding-nomic-embed-text-v1.5`) in your KAG pipeline, use `EMBEDDING_MODEL=nomic-embed-text`
- Make sure Ollama is running if using Ollama models: `ollama serve`
- The chatbot will automatically detect whether to use Ollama or sentence-transformers based on the model name

## Neo4j Node Structure

The chatbot expects Neo4j nodes with the following structure:

```cypher
(:Entity {
  _name_vector: [0.1, 0.2, ...],      // Vector for name (dimension depends on model)
  _desc_vector: [0.1, 0.2, ...],      // Vector for description (optional)
  semanticType: "Reference",           // Type of entity
  name: "entity name",                 // Display name
  id: "unique-id",                     // Unique identifier
  desc: "description text"             // Entity description
})
```

## Usage

### Running Locally
```bash
python chatbot_graphs/rag_graph.py
```

### Running with LangGraph Server
```bash
langgraph dev
```

Then access the `rag_chatbot` graph endpoint.

### Programmatic Usage
```python
from chatbot_graphs.rag_graph import graph
from langchain_core.messages import HumanMessage

# Create initial state with all required fields
state = {
    "messages": [HumanMessage(content="What do you know about X?")],
    "retrieved_context": "",
    "intent": "",
    "sub_questions": [],
    "original_question": ""
}

# Run the graph
result = graph.invoke(state)

# Access preprocessing results
print(f"Intent: {result['intent']}")
print(f"Sub-questions: {result['sub_questions']}")

# Get the response
for msg in result["messages"]:
    print(msg.content)
```

## How It Works

### 1. Text Search
```python
# Searches by exact or partial text matching
# Query: "joint electronic"
# Matches: nodes where name/official_name/aliases contain "joint electronic"
```

### 2. Vector Search
```python
# Uses semantic similarity
# Query: "temperature testing standards"
# Finds: nodes with similar meaning even if exact words don't match
# Returns: similarity scores (0-1) for each result
```

### 3. Complete Flow with ReAct Agent
1. **Preprocessing** (2 LLM calls):
   - Detects **intent** (comparison, explanation, etc.)
   - Extracts **answer-relevant entities** (main entities, related concepts, contextual background)
   - Example: Extracts 15+ entities like "temperature cycling", "thermal shock", "JEDEC standards", "reliability testing", etc.
2. **Context Injection**: Intent and entities are injected into the conversation
3. **ReAct Agent Loop** (automated):
   - **[Reason]**: Agent analyzes query, intent, and extracted entities
   - **[Act]**: Intelligently selects tools with **entity-first strategy**:
     - **START** with `neo4j_entity_graph_search_tool` (if entities extracted)
       - Explores graph neighborhood of ALL extracted entities
       - Retrieves relationships and connections (1-2 levels deep)
       - Provides rich graph structure context
     - **THEN** use `neo4j_vector_search_tool` if needed
       - Semantic search for additional information
       - Uses insights from graph context to refine queries
     - **Fallback** → Use `neo4j_retrieval_tool` for text search
   - **[Observe]**: Reviews retrieved results from all tools
   - **[Reason]**: Decides if more information is needed
   - **[Act]** (if needed): Calls additional tools with refined queries
   - **[Repeat]**: Until sufficient information is gathered
4. **Final Synthesis**: Agent produces comprehensive answer using:
   - **Graph context**: Entity relationships, connections, and neighborhood
   - **Semantic information**: Additional details from vector search
   - **Structured knowledge**: Understanding of how entities relate to each other

**Key Advantages**:
- **Entity-First Approach**: Always starts with graph structure when entities are detected
- **Comprehensive Entity Extraction**: Extracts not just mentioned entities, but also related concepts
- **Graph-Native Retrieval**: Leverages knowledge graph relationships for richer context
- **Iterative Refinement**: Can adjust search strategy based on graph discoveries

### 4. Entity Graph Search ⭐ PRIMARY TOOL
The `neo4j_entity_graph_search_tool` performs **graph traversal** starting from extracted entities:

**How it works:**
```python
# Called by ReAct agent when entities are extracted
# Example: Entities extracted: "temperature cycling, thermal shock"
#
# Tool receives:
# entities = "temperature cycling, thermal shock"
# depth = 2  # traverse 2 levels of relationships
#
# For each entity:
#   1. Find the entity node in Neo4j
#   2. Get Level 1 connections (direct relationships)
#      Example: temperature cycling → source → SMI 202b document
#   3. Get Level 2 connections (2-hop relationships)
#      Example: temperature cycling → via → related standard → test method
#   4. Format as structured context with relationship types
```

**Example Output:**
```
## Entity: temperature cycling

### Direct Connections (Level 1):
  - ← dualChamber: smi 202b
  - → source: SMI 202b Temperature Cycling Dual Chamber

### Indirect Connections (Level 2):
  - via smi 202b → relatedStandard: JEDEC JESD22-A104
  - via Temperature Test → appliesTo: Semiconductor Components
```

**Benefits:**
- **Graph Context**: Understands how entities are connected, not just isolated facts
- **Relationship Discovery**: Reveals connections between entities that might not be obvious
- **Neighborhood Exploration**: Gets comprehensive context about an entity's ecosystem
- **Multi-level Traversal**: Can explore 1 or 2 levels deep (configurable)
- **Prioritized Search**: Agent uses this FIRST when entities are detected

## Vector Similarity Search Details

### Cosine Similarity Calculation
The implementation uses manual cosine similarity calculation in Cypher:

```cypher
cosine_similarity = dot_product(A, B) / (magnitude(A) * magnitude(B))
```

This works without requiring the Neo4j GDS (Graph Data Science) library.

### Similarity Threshold
Default threshold: `0.7` (70% similarity)
- Higher threshold = more strict matching
- Lower threshold = more results but potentially less relevant

### Search Process
1. Query text is embedded using `sentence-transformers`
2. Query vector is compared against `_name_vector` and `_desc_vector`
3. Highest similarity score is selected for each node
4. Results above threshold are returned, sorted by similarity

## Customization

### Adjust Similarity Threshold
Edit the `neo4j_vector_search_tool` in `rag_graph.py`:
```python
retriever.vector_similarity_search(query, limit=5, similarity_threshold=0.5)
```

### Change Embedding Model
Update `.env`:
```bash
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
```

### Modify Result Limit
```python
retriever.search_knowledge_graph(query, limit=10)
retriever.vector_similarity_search(query, limit=10)
```

## Troubleshooting

### "Vector search not available"
- Ensure `sentence-transformers` is installed
- Check if embedding model loaded successfully

### "No similar entities found"
- Lower the similarity threshold (try 0.5 instead of 0.7)
- Check if nodes have `_name_vector` or `_desc_vector` fields
- Verify vectors are the correct dimension (384 for all-MiniLM-L6-v2)

### Connection errors
- Verify Neo4j is running
- Check credentials in `.env`
- Ensure Neo4j allows connections from your network

## Architecture Diagram

```
User Query
    ↓
Preprocessing Node (2 LLM calls)
    ├─→ Intent Detection → comparison/explanation/factual_lookup/etc.
    └─→ Comprehensive Entity Extraction → 10-20+ entities
            - Main entities: "temperature cycling", "thermal shock"
            - Related: "JEDEC standards", "reliability testing"
            - Contextual: "materials testing", "environmental testing"
    ↓
ReAct Agent Node
    │
    ├─→ [Reasoning] Analyze query, intent, and extracted entities
    ├─→ [Action] Entity-first tool selection:
    │       │
    │       ├─→ START: neo4j_entity_graph_search_tool (ALWAYS FIRST)
    │       │   └─→ Graph traversal for ALL entities
    │       │       - Explore 1-2 levels of relationships
    │       │       - Get comprehensive neighborhood context
    │       │       - Process 15+ entities in single call
    │       │
    │       ├─→ OPTIONAL: neo4j_vector_search_tool
    │       │   └─→ Semantic search for additional details
    │       │       - Use graph insights to refine queries
    │       │
    │       └─→ FALLBACK: neo4j_retrieval_tool (text search)
    │
    ├─→ [Observation] Review all tool results
    │       - Graph structure & relationships
    │       - Entity connections & properties
    │       - Additional semantic context
    │
    ├─→ [Reasoning] Synthesize or continue searching
    │       ├─→ IF sufficient → Generate answer
    │       └─→ IF insufficient → Call additional tools
    │
    └─→ [Final Answer] Graph-aware comprehensive response
    ↓
Response to User

Note: Entity-first strategy means graph traversal is ALWAYS the first step,
providing rich relational context for the agent's reasoning.
```

## Performance Notes

- **Query Preprocessing**: ~1-2 seconds (2 LLM calls: intent + entity extraction)
  - Fast and efficient with focused extraction
  - Extracts 10-20+ entities per complex query
- **ReAct Agent**: Variable, depends on reasoning complexity and available context
  - **With entities**: 1-2 tool calls (~2-4 seconds)
    - Entity graph search (fast, explores all entities in single call)
    - Optional vector search for additional info
    - Answer synthesis
  - **Without entities**: 1-2 tool calls (~1-2 seconds)
    - Direct vector or text search
    - Answer synthesis
  - Benefits: Graph-first approach provides comprehensive relationship context
- **Entity Graph Search**: Very fast (~50-200ms for 1-2 level traversal per entity)
  - Processes multiple entities efficiently
  - Example: 15 entities searched in ~1-2 seconds total
- **Vector Search**: Moderate (~200-500ms per query with embedding generation)
- **Text Search**: Fast (~50-100ms for exact matches)
- **Neo4j Query**: Depends on graph size and complexity

**Note**: The comprehensive entity extraction strategy ensures the agent has all relevant context from the start, reducing the need for multiple tool calls and iterations.

## Example Output

When you run the chatbot with a complex question:

```
User: What are temperature cycling tests and how do they differ from thermal shock tests?

[Preprocessing] Intent: comparison
[Preprocessing] Original: What are temperature cycling tests and how do they differ from thermal shock tests?
[Preprocessing] Entities (15): temperature cycling, thermal shock, reliability testing, materials testing,
JEDEC standards, ASTM standards, environmental testing, thermal fatigue, electronic components,
mechanical stress testing, failure analysis, testing methodologies, temperature variation,
thermal cycling, product durability testing

[ReAct Agent] Initialized with 3 Neo4j retrieval tools (text, vector, entity-graph)

[Agent Node] Injected preprocessing context:
  Intent: comparison
  Entities: 15 - temperature cycling, thermal shock, reliability testing, ...

[Agent Node] Invoking ReAct agent...

[Entity Graph Search] Exploring 15 entities (depth=2):
  1. temperature cycling
  2. thermal shock
  3. reliability testing
  ... (and 12 more)

[Entity Graph Search] Entity 1/15: temperature cycling
  ✓ Found entity with 1 direct connections and 1 indirect connections

[Entity Graph Search] Entity 2/15: thermal shock
  ✓ Found entity with 1 direct connections and 1 indirect connections

[Entity Graph Search] Found 3/15 entities (others not in graph, gracefully handled)

Tool Result:
## Entity: temperature cycling

### Direct Connections (Level 1):
  - ← dualChamber: smi 202b
  - → source: SMI 202b Temperature Cycling Dual Chamber

### Indirect Connections (Level 2):
  - via smi 202b → relatedStandard: JEDEC JESD22-A104
  ...

[Agent may call vector search for additional semantic information]

AI: [Provides detailed comparison using graph relationships and semantic context]
```

**Key Points:**
- **Comprehensive extraction**: 15 entities extracted (main + related + contextual)
- **Efficient search**: All entities searched in single tool call
- **Graceful handling**: Entities not found in graph are reported, not blocking
- **Graph-first**: Uses relationship context before falling back to semantic search

## Future Enhancements

- [ ] Add hybrid search (combine text + vector scores)
- [ ] Implement result caching
- [ ] Add support for Neo4j vector indexes
- [ ] Multi-hop relationship traversal
- [ ] Query expansion and refinement
- [ ] Conversation memory management
