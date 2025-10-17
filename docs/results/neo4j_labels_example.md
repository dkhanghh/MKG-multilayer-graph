# Neo4j Label Structure

## How Categories Become Labels

### NER Extraction Output
```json
[
  {
    "name": "Sonion Measurement Lab",
    "category": "Laboratory",
    "description": "..."
  },
  {
    "name": "SMI 203a",
    "category": "TestInstruction",
    "description": "..."
  },
  {
    "name": "VPU product",
    "category": "Equipment",
    "description": "..."
  }
]
```

### Neo4j Graph Result

```cypher
# Each entity gets TWO labels:
# 1. :Entity (base label for all entities)
# 2. :Category (specific type from NER)

(:Entity:Laboratory {id: "sonion_lab", name: "Sonion Measurement Lab"})
(:Entity:TestInstruction {id: "smi_203a", name: "SMI 203a"})
(:Entity:Equipment {id: "vpu_product", name: "VPU product"})
(:Chunk {id: "chunk_1", content: "..."})
```

### Query Examples

```cypher
// Find all Laboratory entities
MATCH (n:Laboratory)
RETURN n

// Find all TestInstruction entities
MATCH (n:TestInstruction)
RETURN n

// Find all entities (any category)
MATCH (n:Entity)
RETURN n

// Find which chunks are sources for Laboratory entities
MATCH (c:Chunk)-[:SOURCE]->(e:Laboratory)
RETURN c, e

// Count entities by category
MATCH (n:Entity)
RETURN labels(n), count(*) as count
```

## Benefits

1. ✅ Type-safe queries: `MATCH (n:Laboratory)` 
2. ✅ Better performance with label indexes
3. ✅ Clear semantic structure in graph
4. ✅ Easy filtering by entity type
5. ✅ Compatible with graph visualization tools

