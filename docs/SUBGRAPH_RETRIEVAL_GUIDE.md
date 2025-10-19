# Subgraph Retrieval Strategies for Question Answering

## Overview

This guide explains how to retrieve the **correct subgraph** from your SPG (Semantic Property Graph) financial knowledge graph to answer user questions effectively.

## Available Retrieval Tools

### 1. **neo4j_entity_graph_search_tool** ⭐ (NOW WITH INTELLIGENT EXPANSION)

**When to use**: Questions about relationships between specific named entities

**How it works**:
1. Finds seed entities using vector similarity
2. Searches for relationships BETWEEN them
3. **NEW**: If no relationships found, automatically expands to 1-hop neighbors
4. **NEW**: Retries relationship search with expanded entity set
5. **NEW**: Can expand up to 2 times (2-hop total)

**Key Features**:
- ✅ Automatic entity expansion until relationships found
- ✅ Shows which entities are original vs. expanded
- ✅ Displays ALL SPG relationship properties
- ✅ Includes source chunks for evidence

**Example**:
```python
# Question: "What is the relationship between 3M Company and its financial statements?"
neo4j_entity_graph_search_tool(entities=["3M Company", "FinancialStatement"])

# Output:
# Found 2 Original + 3 Expanded = 5 Total Entities and 4 Relationships
# (Expanded through 1 hop(s) to find relationships)
#
# Original Entities:
# 1. **3M Company** [Company] (similarity: 0.92)
# 2. **Consolidated Statement of Income** [FinancialStatement] (similarity: 0.88)
#
# Expanded Entities:
# 1. **Q4 2023** [TimePeriod] (via REPORTED_IN)
# 2. **10-K Filing** [RegulatoryFiling] (via PART_OF)
#
# Relationships:
# 1. **3M Company** [Company] →REPORTED_FINANCIALS→ **Consolidated Statement of Income** [FinancialStatement]
#    Properties:
#      • revenue: 8231000000
#      • period: Q4 2023
#      • profit: 541000000
#      ... (ALL 69 properties)
```

**Expansion Algorithm**:
```
1. Find initial entities by vector similarity
2. Search for relationships between them
3. IF no relationships found:
   a. Get 1-hop neighbors of each entity (up to 20)
   b. Add neighbors to entity set
   c. Retry relationship search
   d. Repeat up to 2 times
4. Return subgraph with original + expanded entities
```

---

### 2. **neo4j_typed_vector_search_tool** (SPG Type-Filtered)

**When to use**: Questions requiring specific entity or relationship types

**How it works**:
- Filters vector search by entity labels (Company, Executive, FinancialStatement)
- Filters relationships by type (REPORTED_FINANCIALS, OWNS, EMPLOYS)
- Returns entities with type-filtered relationships and properties

**Key Features**:
- ✅ SPG schema-aware type filtering
- ✅ Filter by multiple entity types (OR logic)
- ✅ Filter by multiple relationship types
- ✅ Returns ALL relationship properties

**Example**:
```python
# Question: "Find companies with revenue data"
neo4j_typed_vector_search_tool(
    query="revenue earnings financial",
    entity_types=["Company"],
    relationship_types=["REPORTED_FINANCIALS"]
)

# Output:
# Type-Filtered Vector Search Results
# Entity Types Filter: Company
# Relationship Types Filter: REPORTED_FINANCIALS
# Found: 5 entities
#
# 1. **3M Company** [Company, Entity] [similarity: 0.89]
#    Relationships (3 found):
#    -> [REPORTED_FINANCIALS] → **Q4 2023 Statement** [FinancialStatement]
#       Properties:
#         • revenue: 8231000000
#         • profit: 541000000
#         ... (ALL properties)
```

**Use Cases**:
- "Show me all executives" → entity_types: ["Executive"]
- "Find ownership structures" → relationship_types: ["OWNS"]
- "Companies with Q4 data" → entity_types: ["Company"], relationship_types: ["REPORTED_FINANCIALS"]

---

### 3. **neo4j_semantic_path_search_tool** (Multi-Hop Discovery)

**When to use**: Questions asking "how is X related to Y?" or tracing connection chains

**How it works**:
1. Finds start entity using vector similarity
2. Finds end entity using vector similarity
3. Discovers all paths between them (up to max_hops)
4. Scores paths by: semantic relevance + property richness + path length
5. Returns top paths with ALL properties

**Key Features**:
- ✅ Multi-hop path discovery (1-5 hops)
- ✅ Path scoring and ranking
- ✅ Relationship type filtering along paths
- ✅ ALL SPG properties for each edge in path
- ✅ Visual path representation

**Example**:
```python
# Question: "How is 3M connected to its Q4 2023 earnings?"
neo4j_semantic_path_search_tool(
    start_entity="3M Company",
    end_entity="Q4 2023 earnings",
    max_hops=3
)

# Output:
# Semantic Path Search: '3M Company' → 'Q4 2023 earnings'
# Found 3 paths (max 3 hops)
#
# Path 1 (length: 2, score: 0.87)
# Start: 3M Company [Company, Entity] (sim: 0.92)
# End: Q4 2023 revenue metric [FinancialMetric] (sim: 0.85)
#
# Path: **3M Company** [Company] -[REPORTED_FINANCIALS]→ **Q4 2023 Statement** [FinancialStatement] -[HAS_METRIC]→ **revenue** [FinancialMetric]
#
# Relationships along path:
# 1. **3M Company** -[REPORTED_FINANCIALS]→ **Q4 2023 Statement**
#    Properties:
#      • revenue: 8231000000
#      • period: Q4 2023
#      ... (ALL properties)
# 2. **Q4 2023 Statement** -[HAS_METRIC]→ **revenue**
#    Properties:
#      • value: 8231000000
#      • currency: USD
```

**Use Cases**:
- "How is Company X connected to filing Y?"
- "Trace the path from CEO to financial statement"
- "Find connection between subsidiary and parent revenue"

---

### 4. **neo4j_question_subgraph_tool** (Most Intelligent) 🧠

**When to use**: Complex questions requiring comprehensive subgraph context

**How it works** (5-stage pipeline):
1. **Entity Identification**: Find seed entities from question
2. **Type Inference**: Auto-detect required entity/relationship types
3. **Subgraph Expansion**: k-hop expansion from seeds (up to max_hops)
4. **Property Highlighting**: Highlight question-relevant properties with ⭐
5. **Context Enrichment**: Include source chunks for evidence

**Automatic Type Inference**:
```python
Question keywords → Detected relationship types:
- "revenue", "profit", "earnings" → REPORTED_FINANCIALS
- "owns", "subsidiary" → OWNS
- "executive", "CEO" → EMPLOYS
- "filed", "10-K" → FILED
```

**Key Features**:
- ✅ Fully automated subgraph extraction
- ✅ Intelligent type inference from keywords
- ✅ Multi-hop expansion with relevance filtering
- ✅ Property highlighting based on question
- ✅ Complete with source evidence

**Example**:
```python
# Question: "What was 3M's revenue in Q4 2023?"
neo4j_question_subgraph_tool(
    question="What was 3M's revenue in Q4 2023?",
    max_hops=2
)

# Output:
# Question-Specific Subgraph
# Question: What was 3M's revenue in Q4 2023?
# Subgraph Size: 8 entities, 12 relationships
#
# Stage 1: Found 5 seed entities
#   - 3M Company [Company] (sim: 0.92)
#   - Q4 2023 [TimePeriod] (sim: 0.85)
#   - revenue [FinancialMetric] (sim: 0.78)
#
# Stage 2: Inferred relationship types: ['REPORTED_FINANCIALS']
# Stage 3: Extracted subgraph - 8 nodes, 12 edges
#
# Entities in Subgraph:
# 1. **3M Company** [Company]
#    Description: Manufacturing conglomerate...
#    Source Evidence: "3M Company reported strong earnings..."
#
# Relationships in Subgraph:
# 1. **3M Company** -[REPORTED_FINANCIALS]→ **Q4 2023 Statement**
#    Properties:
#      • **revenue: 8231000000** ⭐  (mentioned in question)
#      • **period: Q4 2023** ⭐  (mentioned in question)
#      • profit: 541000000
#      ... (ALL properties)
```

**Use Cases**:
- Complex financial questions with multiple entities
- Questions with temporal constraints
- Multi-hop reasoning questions
- When you need complete context for LLM

---

## Choosing the Right Tool

### Decision Tree

```
Is the question about specific named entities?
├─ YES: Use neo4j_entity_graph_search_tool
│         ✓ Automatic expansion if no direct relationships
│         ✓ Shows original vs expanded entities
│
└─ NO: Does question mention specific entity/relationship TYPES?
   ├─ YES: Use neo4j_typed_vector_search_tool
   │         ✓ Filter by Company, Executive, etc.
   │         ✓ Filter by REPORTED_FINANCIALS, OWNS, etc.
   │
   └─ NO: Does question ask "how is X related to Y?"
      ├─ YES: Use neo4j_semantic_path_search_tool
      │         ✓ Multi-hop path discovery
      │         ✓ Path scoring and ranking
      │
      └─ NO: Use neo4j_question_subgraph_tool
                ✓ Fully automated
                ✓ Intelligent type inference
                ✓ Best for complex questions
```

### Quick Reference

| Question Pattern | Best Tool | Example |
|-----------------|-----------|---------|
| "Relationship between X and Y" | entity_graph_search | "Relationship between 3M and its statements" |
| "Show me [entity type]" | typed_vector_search | "Show me all executives" |
| "How is X connected to Y?" | semantic_path_search | "How is 3M connected to Q4 earnings?" |
| "What was X's Y in Z?" | question_subgraph | "What was 3M's revenue in Q4 2023?" |
| "Compare X and Y" | question_subgraph | "Compare Apple and Microsoft profit" |

---

## Best Practices

### 1. **Entity Expansion Benefits**

The new expansion feature in `entity_graph_search_tool` solves the "sparse graph" problem:

**Before** (no expansion):
```
Query: ["Company A", "Financial Data"]
Result: "No relationships found between these entities ❌"
```

**After** (with expansion):
```
Query: ["Company A", "Financial Data"]
Step 1: No direct relationships found
Step 2: Expanding entities (depth 1)...
        Added 8 neighbor entities
Step 3: Found 4 relationships after expansion! ✓
Result: Shows Company A → FinancialStatement → Financial Metrics
```

### 2. **Property Filtering**

Use property filters to narrow results:

```python
neo4j_question_subgraph_tool(
    question="Show me 3M's Q4 2023 data",
    property_filters={"period": "Q4 2023"}
)
```

### 3. **Hop Depth Selection**

- **1 hop**: Direct relationships only (fast, precise)
- **2 hops**: Include intermediate entities (balanced)
- **3+ hops**: Broader context (slower, more comprehensive)

```python
# For simple questions
neo4j_semantic_path_search_tool(start, end, max_hops=1)

# For complex reasoning
neo4j_semantic_path_search_tool(start, end, max_hops=3)
```

### 4. **SPG Property Utilization**

All tools return **complete SPG properties**. Always include them in answers:

```python
# ✓ GOOD: Include property values
"3M's Q4 2023 revenue was $8.23 billion"

# ✗ BAD: Generic response
"3M reported financial data"
```

---

## Integration with Agent

The agent automatically selects the right tool based on question analysis:

```python
# In agent.py
context_message = HumanMessage(content=f"""
**Tool Selection Guide:**

1. neo4j_entity_graph_search_tool - Use when:
   - User asks about relationships between SPECIFIC named entities
   - NOW with automatic expansion if no direct relationships found!

2. neo4j_typed_vector_search_tool - Use when:
   - User wants SPECIFIC entity TYPES
   - User wants SPECIFIC relationship TYPES

3. neo4j_semantic_path_search_tool - Use when:
   - User asks "how is X related to Y"
   - User wants to trace chains of relationships

4. neo4j_question_subgraph_tool - Use when:
   - Complex questions requiring comprehensive context
   - Questions with temporal constraints
   - When automatic type inference would help
""")
```

---

## Performance Considerations

### Tool Complexity

| Tool | Query Complexity | Use When |
|------|-----------------|----------|
| entity_graph_search | Medium (with expansion) | Known entities, may need expansion |
| typed_vector_search | Low | Type-specific queries |
| semantic_path_search | High | Multi-hop discovery needed |
| question_subgraph | Very High | Complex comprehensive queries |

### Optimization Tips

1. **Start specific**: Use entity_graph_search for known entities
2. **Use type filters**: Reduce search space with typed_vector_search
3. **Limit hops**: Use 2 hops for most cases, 3+ only when necessary
4. **Property filters**: Narrow results with temporal/value filters

---

## Examples by Question Type

### Financial Metrics
```python
Q: "What was 3M's revenue in Q4 2023?"
Tool: neo4j_question_subgraph_tool(question, max_hops=2)
Why: Auto-detects REPORTED_FINANCIALS, highlights revenue
```

### Ownership Structure
```python
Q: "What companies does Google own?"
Tool: neo4j_typed_vector_search_tool(
    query="Google subsidiaries",
    entity_types=["Company"],
    relationship_types=["OWNS"]
)
Why: Type-filtered for ownership relationships
```

### Executive Connections
```python
Q: "How is the CEO connected to financial statements?"
Tool: neo4j_semantic_path_search_tool(
    start_entity="CEO",
    end_entity="FinancialStatement",
    max_hops=2
)
Why: Multi-hop path discovery
```

### Entity Relationships (with expansion!)
```python
Q: "Find the relationship between Company X and Product Y"
Tool: neo4j_entity_graph_search_tool(entities=["Company X", "Product Y"])
Why: Will automatically expand if no direct relationship
```

---

## Summary

✅ **neo4j_entity_graph_search_tool**: NOW WITH INTELLIGENT EXPANSION!
- Automatically finds intermediate entities to connect sparse graphs
- Shows which entities are original vs. expanded
- Best for specific named entity queries

✅ **neo4j_typed_vector_search_tool**: SPG Type-Aware Filtering
- Filter by entity types and relationship types
- Best for type-specific queries

✅ **neo4j_semantic_path_search_tool**: Multi-Hop Path Discovery
- Find and rank paths between entities
- Best for "how is X related to Y" questions

✅ **neo4j_question_subgraph_tool**: Fully Automated Intelligence
- 5-stage pipeline with automatic type inference
- Best for complex comprehensive questions

All tools return **complete SPG relationship properties** for rich context!
