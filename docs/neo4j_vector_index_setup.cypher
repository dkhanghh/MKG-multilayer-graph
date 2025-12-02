// ========================================
// Neo4j Vector Index Setup Queries
// ========================================
// These queries will create vector indexes for all node types with embeddings
// Vector indexes provide much faster similarity search using ANN (Approximate Nearest Neighbor)

// ========================================
// Step 1: Check existing indexes
// ========================================
// Run this first to see what indexes already exist
SHOW INDEXES;


// ========================================
// Step 2: Check embedding dimensions
// ========================================
// Find out what dimension your embeddings have
// (Common sizes: 768 for sentence-transformers, 1536 for OpenAI/Gemini)
MATCH (n)
WHERE n.embeddings IS NOT NULL
RETURN DISTINCT labels(n) as nodeLabel, size(n.embeddings) as embeddingDimension
LIMIT 10;


// ========================================
// Step 3: Create vector indexes for each node type
// ========================================

// 3.1 Create vector index for Entity nodes
// Replace DIMENSION_SIZE with your actual embedding dimension (e.g., 768, 1536)
CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
FOR (n:Entity)
ON n.embeddings
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,  // CHANGE THIS to your embedding dimension!
    `vector.similarity_function`: 'cosine'
  }
};

// 3.2 Create vector index for Chunk nodes (if they have embeddings)
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
FOR (n:Chunk)
ON n.embeddings
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,  // CHANGE THIS to your embedding dimension!
    `vector.similarity_function`: 'cosine'
  }
};

// 3.3 Create vector index for ALL nodes (generic)
// This creates an index that works across all node labels
// Note: You may want to create separate indexes per label for better performance
CREATE VECTOR INDEX all_node_embeddings IF NOT EXISTS
FOR (n)
ON n.embeddings
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 768,  // CHANGE THIS to your embedding dimension!
    `vector.similarity_function`: 'cosine'
  }
};


// ========================================
// Step 4: Wait for indexes to be built
// ========================================
// After creating indexes, check their status
// Wait until state is "ONLINE" before querying
SHOW INDEXES
YIELD name, state, populationPercent, type
WHERE type = "VECTOR"
RETURN name, state, populationPercent;


// ========================================
// Step 5: Test the vector index with a query
// ========================================
// Once indexes are ONLINE, test them with this query
// Replace $query_vector with your actual embedding vector

// Example using Entity index:
CALL db.index.vector.queryNodes('entity_embeddings', 5, $query_vector)
YIELD node, score
RETURN node.name as name,
       node.description as description,
       labels(node) as labels,
       score
ORDER BY score DESC;

// Example with score threshold filtering:
CALL db.index.vector.queryNodes('entity_embeddings', 10, $query_vector)
YIELD node, score
WHERE score >= 0.5
RETURN node.name as name,
       node.description as description,
       labels(node) as labels,
       score
ORDER BY score DESC;


// ========================================
// Step 6: Query with relationships (like your current code)
// ========================================
// Full query with relationships and source chunks
CALL db.index.vector.queryNodes('entity_embeddings', 10, $query_vector)
YIELD node as n, score
WHERE score >= $threshold

// Get relationships
OPTIONAL MATCH (n)-[r]-(related)
WHERE related IS NOT NULL

// Get source chunks
OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(n)

RETURN n.name as name,
       n.label as type,
       n.id as id,
       n.description as description,
       score as similarity,
       type(r) as relation_type,
       related.name as related_node,
       properties(r) as relation_properties,
       CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction,
       collect(DISTINCT {
           id: chunk.id,
           content: chunk.content,
           chunk_index: chunk.chunk_index,
           page_number: chunk.page_number
       }) as source_chunks
LIMIT $limit;


// ========================================
// Performance Comparison: Manual vs Vector Index
// ========================================

// MANUAL COSINE SIMILARITY (SLOW - your current approach):
// Scans ALL nodes, computes similarity for each
MATCH (n)
WHERE n.embeddings IS NOT NULL
WITH n,
     reduce(dot = 0.0, i IN range(0, size(n.embeddings)-1) |
          dot + n.embeddings[i] * $query_vector[i]) /
          (sqrt(reduce(sum = 0.0, x IN n.embeddings | sum + x * x)) *
           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
WHERE similarity >= 0.5
RETURN n.name, similarity
ORDER BY similarity DESC
LIMIT 5;

// VECTOR INDEX (FAST - recommended):
// Uses ANN algorithm, only computes for likely candidates
CALL db.index.vector.queryNodes('entity_embeddings', 5, $query_vector)
YIELD node, score
WHERE score >= 0.5
RETURN node.name, score
ORDER BY score DESC;


// ========================================
// Optional: Drop indexes (if you need to recreate them)
// ========================================
// DROP INDEX entity_embeddings IF EXISTS;
// DROP INDEX chunk_embeddings IF EXISTS;
// DROP INDEX all_node_embeddings IF EXISTS;


// ========================================
// Additional: Check node counts per label
// ========================================
MATCH (n)
WHERE n.embeddings IS NOT NULL
RETURN labels(n) as nodeLabel, count(*) as nodeCount, size(n.embeddings) as embeddingSize
ORDER BY nodeCount DESC;
