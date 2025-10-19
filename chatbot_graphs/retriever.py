"""
Neo4j retriever for knowledge graph querying.
"""
import os

# Optional Neo4j import
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

# Optional embedding support
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Optional Ollama for embeddings
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

# Optional Gemini for embeddings
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class Neo4jRetriever:
    """Handles Neo4j database connections and queries."""

    def __init__(self):
        """Initialize Neo4j connection."""
        if not HAS_NEO4J:
            raise ImportError("neo4j not installed")

        # Get Neo4j credentials from environment
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "financebench")

        if not self.password:
            raise ValueError("NEO4J_PASSWORD environment variable is required")

        # Create driver
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.username, self.password)
        )

        # Initialize embedding model for vector search
        # IMPORTANT: Model must generate vectors matching Neo4j vector dimensions
        self.embedding_model = None
        self.embedding_type = None

        # Check for embedding model configuration
        model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        embedding_provider = os.getenv("EMBEDDING_PROVIDER", "gemini")  # gemini, ollama, sentence-transformers

        # Try Gemini first (for embedding-001 and other Gemini models)
        if embedding_provider == "gemini" and HAS_GEMINI:
            try:
                # Configure Gemini API
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini embeddings")

                # Initialize Gemini client (using google-genai package)
                self.gemini_client = genai.Client(api_key=api_key)
                self.embedding_model = model_name
                self.embedding_type = "gemini"

                # Test embedding
                test_result = self.gemini_client.models.embed_content(
                    model=self.embedding_model,
                    contents=["test"],
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                )
                test_vec = test_result.embeddings[0].values
                print(f"[Neo4j Retriever] Using Gemini embedding model: {self.embedding_model}")
                print(f"[Neo4j Retriever] Embedding dimension: {len(test_vec)}")
            except Exception as e:
                print(f"Warning: Could not use Gemini embedding model: {e}")
                self.embedding_model = None
                self.gemini_client = None

        # Try Ollama (for nomic-embed-text and other Ollama models)
        if self.embedding_model is None and embedding_provider == "ollama" and HAS_OLLAMA:
            try:
                # For Ollama models, just store the model name
                # The actual model name without @quantization suffix
                self.embedding_model = model_name.split('@')[0] if '@' in model_name else model_name
                self.embedding_type = "ollama"

                # Test embedding
                test_vec = ollama.embeddings(model=self.embedding_model, prompt="test")['embedding']
                print(f"[Neo4j Retriever] Using Ollama embedding model: {self.embedding_model}")
                print(f"[Neo4j Retriever] Embedding dimension: {len(test_vec)}")
            except Exception as e:
                print(f"Warning: Could not use Ollama embedding model: {e}")
                self.embedding_model = None

        # Fall back to sentence-transformers
        if self.embedding_model is None and HAS_SENTENCE_TRANSFORMERS:
            try:
                model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
                print(f"[Neo4j Retriever] Loading sentence-transformer model: {model_name}")
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_type = "sentence_transformer"
                test_vec = self.embedding_model.encode("test")
                print(f"[Neo4j Retriever] Embedding dimension: {len(test_vec)}")
            except Exception as e:
                print(f"Warning: Could not load embedding model: {e}")
                self.embedding_model = None

    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text using the configured model."""
        if not self.embedding_model:
            raise ValueError("No embedding model available")

        if self.embedding_type == "gemini":
            # Use google-genai package API
            result = self.gemini_client.models.embed_content(
                model=self.embedding_model,
                contents=[text],
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY"  # Use RETRIEVAL_QUERY for query embeddings
                )
            )
            return result.embeddings[0].values
        elif self.embedding_type == "ollama":
            result = ollama.embeddings(model=self.embedding_model, prompt=text)
            return result['embedding']
        elif self.embedding_type == "sentence_transformer":
            return self.embedding_model.encode(text).tolist()
        else:
            raise ValueError(f"Unknown embedding type: {self.embedding_type}")

    def search_knowledge_graph(self, query: str, limit: int = 5) -> str:
        """
        Search the knowledge graph for relevant information.

        Args:
            query: Search query text
            limit: Maximum number of results to return

        Returns:
            Formatted context string with retrieved information
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Search for nodes matching the query text
                # Only search properties that exist in the schema
                cypher_query = """
                MATCH (n)
                WHERE toLower(n.name) CONTAINS toLower($search_text)
                   OR (n.description IS NOT NULL AND toLower(n.description) CONTAINS toLower($search_text))
                OPTIONAL MATCH (n)-[r]-(related)
                WITH n, collect({
                    relation: type(r),
                    node: related.name,
                    direction: CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END
                }) as relationships
                RETURN n.name as name,
                       n.label as type,
                       n.description as description,
                       relationships
                LIMIT $limit
                """

                result = session.run(cypher_query, search_text=query, limit=limit)
                records = list(result)

                if not records:
                    return f"No information found in knowledge graph for: {query}"

                # Format the results into readable context
                context_parts = []
                for record in records:
                    name = record["name"]
                    node_type = record["type"]
                    description = record["description"]
                    relationships = record["relationships"]

                    # Build entity description
                    entity_desc = f"\n**{name}** ({node_type})"

                    # Add description
                    if description:
                        entity_desc += f"\n  - Description: {description}"

                    # Add relationships
                    if relationships:
                        entity_desc += "\n  - Related to:"
                        for rel in relationships[:5]:  # Limit relationships shown
                            if rel['node']:
                                direction = "->" if rel['direction'] == 'outgoing' else "<-"
                                entity_desc += f"\n    - {direction} {rel['relation']}: {rel['node']}"

                    context_parts.append(entity_desc)

                return "\n".join(context_parts)

        except Exception as e:
            return f"Error querying knowledge graph: {str(e)}"

    def vector_similarity_search(self, query: str, limit: int = 5, similarity_threshold: float = 0.5) -> str:
        """
        Search the knowledge graph using vector similarity on embeddings.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            similarity_threshold: Minimum cosine similarity threshold (0-1)

        Returns:
            Formatted context string with retrieved information
        """
        if not self.embedding_model:
            return "Vector search not available: embedding model not loaded"

        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)

            with self.driver.session(database=self.database) as session:
                # Vector similarity search using manual cosine similarity calculation
                # Formula: cosine_similarity = dot_product(A, B) / (magnitude(A) * magnitude(B))
                cypher_query = """
                MATCH (n)
                WHERE n.embeddings IS NOT NULL
                WITH n,
                     reduce(dot = 0.0, i IN range(0, size(n.embeddings)-1) |
                          dot + n.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN n.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS max_similarity
                WHERE max_similarity >= $threshold
                ORDER BY max_similarity DESC
                LIMIT $limit

                // For each entity, get relationships with properties (same pattern as entity_graph_search)
                WITH n, max_similarity
                OPTIONAL MATCH (n)-[r]-(related)
                WHERE related IS NOT NULL
                WITH n, max_similarity, r, related,
                     CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction

                // Get source chunks
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(n)

                RETURN n.name as name,
                       n.label as type,
                       n.id as id,
                       n.description as description,
                       max_similarity as similarity,
                       type(r) as relation_type,
                       related.name as related_node,
                       properties(r) as relation_properties,
                       direction,
                       collect(DISTINCT {
                           id: chunk.id,
                           content: chunk.content,
                           chunk_index: chunk.chunk_index,
                           page_number: chunk.page_number
                       }) as source_chunks
                """

                result = session.run(
                    cypher_query,
                    query_vector=query_embedding,
                    threshold=similarity_threshold,
                    limit=limit
                )
                records = list(result)

                if not records:
                    return f"No similar entities found in knowledge graph for: {query} (threshold: {similarity_threshold})"

                # Group records by entity (since each row is entity-relationship pair)
                from collections import defaultdict
                entities = defaultdict(lambda: {
                    'relationships': [],
                    'source_chunks': []
                })

                for record in records:
                    entity_key = (record["name"], record["id"])

                    # Store entity info
                    if 'name' not in entities[entity_key]:
                        entities[entity_key].update({
                            'name': record["name"],
                            'type': record["type"],
                            'id': record["id"],
                            'description': record["description"],
                            'similarity': record["similarity"]
                        })

                    # Add relationship if exists
                    if record.get("relation_type"):
                        entities[entity_key]['relationships'].append({
                            'relation': record["relation_type"],
                            'node': record["related_node"],
                            'direction': record["direction"],
                            'properties': record["relation_properties"]
                        })

                    # Merge source chunks
                    for chunk in record.get("source_chunks", []):
                        if chunk.get('id') and chunk not in entities[entity_key]['source_chunks']:
                            entities[entity_key]['source_chunks'].append(chunk)

                # Format the results into readable context
                context_parts = []
                for entity_data in entities.values():
                    name = entity_data["name"]
                    entity_type = entity_data["type"]
                    entity_id = entity_data["id"]
                    description = entity_data["description"]
                    similarity = entity_data["similarity"]
                    source_chunks = entity_data["source_chunks"]
                    relationships = entity_data["relationships"]

                    # Build entity description
                    entity_desc = f"\n**{name}** ({entity_type}) [similarity: {similarity:.3f}]"
                    if entity_id and entity_id != name:
                        entity_desc += f"\n  - ID: {entity_id}"
                    if description:
                        entity_desc += f"\n  - Description: {description}"

                    # Add source chunks prominently if available
                    if source_chunks:
                        entity_desc += "\n  - Source Chunks (Text Evidence):"
                        for chunk in source_chunks[:3]:  # Limit to 3 chunks
                            if chunk.get('content'):
                                chunk_idx = chunk.get('chunk_index', '?')
                                page_num = chunk.get('page_number', '?')
                                entity_desc += f"\n    [Chunk {chunk_idx}, Page {page_num}]: \"{chunk['content']}\""

                    # Add relationships with ALL properties
                    if relationships:
                        entity_desc += "\n  - Related to:"
                        for rel in relationships[:5]:  # Limit relationships shown
                            if rel['node']:
                                direction = "->" if rel['direction'] == 'outgoing' else "<-"
                                entity_desc += f"\n    - {direction} {rel['relation']}: {rel['node']}"

                                # Add ALL relationship properties (same pattern as entity_graph_search)
                                if rel.get('properties'):
                                    props = rel['properties']
                                    if props and isinstance(props, dict):
                                        entity_desc += "\n      Properties:"
                                        for key, value in props.items():
                                            entity_desc += f"\n        • {key}: {value}"

                    context_parts.append(entity_desc)

                return "\n".join(context_parts)

        except Exception as e:
            return f"Error performing vector similarity search: {str(e)}"

    def typed_vector_search(
        self,
        query: str,
        entity_types: list[str] = None,
        relationship_types: list[str] = None,
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> str:
        """
        Type-filtered vector similarity search for SPG (Semantic Property Graph).

        This method performs vector search with filtering by entity types and relationship types,
        leveraging the SPG structure to provide more precise and relevant results.

        Args:
            query: Search query text
            entity_types: List of entity type labels to filter (e.g., ["Company", "Executive"])
                         If None, searches all entity types
            relationship_types: List of relationship types to filter (e.g., ["REPORTED_FINANCIALS", "OWNS"])
                               If None, includes all relationship types
            limit: Maximum number of results to return
            similarity_threshold: Minimum cosine similarity threshold (0-1)

        Returns:
            Formatted context string with type-filtered entities, relationships, and properties

        Example use cases:
            - typed_vector_search("earnings report", entity_types=["Company", "FinancialStatement"])
            - typed_vector_search("executive compensation", entity_types=["Executive"], relationship_types=["EMPLOYS"])
            - typed_vector_search("market data", relationship_types=["REPORTED_FINANCIALS", "HAS_MARKET_DATA"])
        """
        if not self.embedding_model:
            return "Typed vector search not available: embedding model not loaded"

        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)

            with self.driver.session(database=self.database) as session:
                # Build type filter for entity labels
                type_filter = ""
                if entity_types:
                    # Use labels() function to check if any of the entity's labels match
                    type_filter = "AND any(label IN labels(n) WHERE label IN $entity_types)"

                # Vector similarity search with entity type filtering
                cypher_query = f"""
                MATCH (n)
                WHERE n.embeddings IS NOT NULL
                {type_filter}
                WITH n,
                     reduce(dot = 0.0, i IN range(0, size(n.embeddings)-1) |
                          dot + n.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN n.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS max_similarity
                WHERE max_similarity >= $threshold
                ORDER BY max_similarity DESC
                LIMIT $limit

                // Get relationships with type filtering
                WITH n, max_similarity
                OPTIONAL MATCH (n)-[r]-(related)
                WHERE related IS NOT NULL
                  AND ($relationship_types IS NULL OR type(r) IN $relationship_types)
                WITH n, max_similarity, r, related,
                     CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction

                // Get source chunks
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(n)

                RETURN n.name as name,
                       n.label as type,
                       labels(n) as all_labels,
                       n.id as id,
                       n.description as description,
                       max_similarity as similarity,
                       type(r) as relation_type,
                       related.name as related_node,
                       labels(related) as related_labels,
                       properties(r) as relation_properties,
                       direction,
                       collect(DISTINCT {{
                           id: chunk.id,
                           content: chunk.content,
                           chunk_index: chunk.chunk_index,
                           page_number: chunk.page_number
                       }}) as source_chunks
                """

                result = session.run(
                    cypher_query,
                    query_vector=query_embedding,
                    threshold=similarity_threshold,
                    limit=limit,
                    entity_types=entity_types,
                    relationship_types=relationship_types
                )
                records = list(result)

                if not records:
                    type_desc = f" of types {entity_types}" if entity_types else ""
                    return f"No similar entities{type_desc} found in knowledge graph for: {query} (threshold: {similarity_threshold})"

                # Group records by entity
                from collections import defaultdict
                entities = defaultdict(lambda: {
                    'relationships': [],
                    'source_chunks': []
                })

                for record in records:
                    entity_key = (record["name"], record["id"])

                    # Store entity info
                    if 'name' not in entities[entity_key]:
                        entities[entity_key].update({
                            'name': record["name"],
                            'type': record["type"],
                            'all_labels': record["all_labels"],
                            'id': record["id"],
                            'description': record["description"],
                            'similarity': record["similarity"]
                        })

                    # Add relationship if exists and matches filter
                    if record.get("relation_type"):
                        entities[entity_key]['relationships'].append({
                            'relation': record["relation_type"],
                            'node': record["related_node"],
                            'related_labels': record["related_labels"],
                            'direction': record["direction"],
                            'properties': record["relation_properties"]
                        })

                    # Merge source chunks
                    for chunk in record.get("source_chunks", []):
                        if chunk.get('id') and chunk not in entities[entity_key]['source_chunks']:
                            entities[entity_key]['source_chunks'].append(chunk)

                # Format the results
                context_parts = []
                context_parts.append(f"\n## Type-Filtered Vector Search Results")
                if entity_types:
                    context_parts.append(f"**Entity Types Filter**: {', '.join(entity_types)}")
                if relationship_types:
                    context_parts.append(f"**Relationship Types Filter**: {', '.join(relationship_types)}")
                context_parts.append(f"**Found**: {len(entities)} entities\n")

                for entity_data in entities.values():
                    name = entity_data["name"]
                    all_labels = entity_data.get("all_labels", [])
                    entity_type = entity_data["type"]
                    entity_id = entity_data["id"]
                    description = entity_data["description"]
                    similarity = entity_data["similarity"]
                    source_chunks = entity_data["source_chunks"]
                    relationships = entity_data["relationships"]

                    # Build entity description with all labels (SPG types)
                    labels_str = ", ".join(all_labels) if all_labels else entity_type
                    entity_desc = f"\n**{name}** [{labels_str}] [similarity: {similarity:.3f}]"
                    if entity_id and entity_id != name:
                        entity_desc += f"\n  - ID: {entity_id}"
                    if description:
                        entity_desc += f"\n  - Description: {description}"

                    # Add source chunks if available
                    if source_chunks:
                        entity_desc += "\n  - Source Chunks:"
                        for chunk in source_chunks[:3]:  # Limit to 3 chunks
                            if chunk.get('content'):
                                chunk_idx = chunk.get('chunk_index', '?')
                                page_num = chunk.get('page_number', '?')
                                entity_desc += f"\n    [Chunk {chunk_idx}, Page {page_num}]: \"{chunk['content']}\""

                    # Add filtered relationships with ALL SPG properties
                    if relationships:
                        entity_desc += f"\n  - Relationships ({len(relationships)} found):"
                        for rel in relationships[:10]:  # Show up to 10 relationships
                            if rel['node']:
                                direction = "->" if rel['direction'] == 'outgoing' else "<-"
                                related_labels_str = ", ".join(rel.get('related_labels', []))
                                entity_desc += f"\n    {direction} [{rel['relation']}] → **{rel['node']}** [{related_labels_str}]"

                                # Add ALL SPG relationship properties
                                if rel.get('properties'):
                                    props = rel['properties']
                                    if props and isinstance(props, dict) and len(props) > 0:
                                        entity_desc += "\n      Properties:"
                                        for key, value in props.items():
                                            entity_desc += f"\n        • {key}: {value}"

                    context_parts.append(entity_desc)

                return "\n".join(context_parts)

        except Exception as e:
            return f"Error performing typed vector search: {str(e)}"

    def semantic_path_search(
        self,
        start_entity: str,
        end_entity: str,
        max_hops: int = 3,
        path_relationship_types: list[str] = None,
        return_all_paths: bool = True,
        limit_paths: int = 10
    ) -> str:
        """
        Find semantic paths between two entities with property-rich relationships (SPG).

        This method finds the most semantically relevant paths connecting two entities,
        extracting ALL relationship properties along each path. Leverages SPG structure
        for multi-hop traversal with rich edge properties.

        Args:
            start_entity: Name or description of the starting entity
            end_entity: Name or description of the ending entity
            max_hops: Maximum path length (1-5 hops recommended, default: 3)
            path_relationship_types: Filter paths by relationship types (default: None = all types)
            return_all_paths: Return all paths or only shortest (default: True)
            limit_paths: Maximum number of paths to return (default: 10)

        Returns:
            Formatted context with paths, relationship properties, and path scores

        Example use cases:
            - semantic_path_search("3M Company", "Q4 2023 revenue")
            - semantic_path_search("CEO", "FinancialStatement", max_hops=2)
            - semantic_path_search("Company", "RegulatoryFiling", path_relationship_types=["FILED", "PART_OF"])
        """
        if not self.embedding_model:
            return "Semantic path search not available: embedding model not loaded"

        try:
            print(f"\n[Semantic Path Search] Finding paths: '{start_entity}' → '{end_entity}'")
            print(f"  Max hops: {max_hops}")
            if path_relationship_types:
                print(f"  Relationship type filter: {path_relationship_types}")

            with self.driver.session(database=self.database) as session:
                # Step 1: Find start entities by text search + vector similarity
                start_embedding = self.generate_embedding(start_entity)

                start_query = """
                // Priority 1: Exact name match
                MATCH (n)
                WHERE n.name = $search_text OR n.official_name = $search_text
                RETURN n.name as name, n.id as id, labels(n) as labels, 1.0 as similarity, 'exact' as match_type

                UNION

                // Priority 2: Case-insensitive partial match on name or official_name
                MATCH (n)
                WHERE toLower(n.name) CONTAINS toLower($search_text)
                   OR toLower(n.official_name) CONTAINS toLower($search_text)
                WITH n
                WHERE NOT (n.name = $search_text OR n.official_name = $search_text)  // Exclude exact matches
                RETURN n.name as name, n.id as id, labels(n) as labels, 0.9 as similarity, 'partial' as match_type
                LIMIT 3

                // COMMENTED OUT FOR TESTING: Vector similarity disabled
                // To re-enable, uncomment the UNION and the vector similarity query below

                // UNION
                //
                // // Priority 3: Vector similarity
                // MATCH (n)
                // WHERE n.embeddings IS NOT NULL
                // WITH n,
                //      reduce(dot = 0.0, i IN range(0, size(n.embeddings)-1) |
                //           dot + n.embeddings[i] * $query_vector[i]) /
                //           (sqrt(reduce(sum = 0.0, x IN n.embeddings | sum + x * x)) *
                //            sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
                // WHERE similarity >= 0.3
                // WITH n, similarity
                // WHERE NOT (n.name = $search_text OR n.official_name = $search_text
                //           OR toLower(n.name) CONTAINS toLower($search_text)
                //           OR toLower(n.official_name) CONTAINS toLower($search_text))  // Exclude already matched
                // RETURN n.name as name, n.id as id, labels(n) as labels, similarity, 'vector' as match_type
                // ORDER BY similarity DESC
                // LIMIT 3
                """

                start_results = session.run(start_query, query_vector=start_embedding, search_text=start_entity)
                start_entities = [
                    {
                        'name': r['name'],
                        'id': r['id'],
                        'labels': r['labels'],
                        'similarity': r['similarity'],
                        'match_type': r['match_type']
                    }
                    for r in start_results
                ]

                if not start_entities:
                    return f"No entities found matching start: '{start_entity}'"

                print(f"  Found {len(start_entities)} start entities:")
                for e in start_entities:
                    print(f"    - {e['name']} [{', '.join(e['labels'])}] (similarity: {e['similarity']:.3f}, match: {e['match_type']})")

                # Step 2: Find end entities by text search + vector similarity
                end_embedding = self.generate_embedding(end_entity)

                end_results = session.run(start_query, query_vector=end_embedding, search_text=end_entity)
                end_entities = [
                    {
                        'name': r['name'],
                        'id': r['id'],
                        'labels': r['labels'],
                        'similarity': r['similarity'],
                        'match_type': r['match_type']
                    }
                    for r in end_results
                ]

                if not end_entities:
                    return f"No entities found matching end: '{end_entity}'"

                print(f"  Found {len(end_entities)} end entities:")
                for e in end_entities:
                    print(f"    - {e['name']} [{', '.join(e['labels'])}] (similarity: {e['similarity']:.3f}, match: {e['match_type']})")

                # Step 3: Find paths between start and end entities
                all_paths = []

                for start in start_entities:
                    for end in end_entities:
                        # Skip if same entity
                        if start['name'] == end['name'] and start['id'] == end['id']:
                            continue

                        # Build path relationship filter
                        rel_filter = ""
                        if path_relationship_types:
                            rel_filter = "WHERE all(r IN relationships(path) WHERE type(r) IN $path_types)"

                        # Find paths
                        path_query = f"""
                        MATCH (start {{name: $start_name, id: $start_id}})
                        MATCH (end {{name: $end_name, id: $end_id}})
                        MATCH path = (start)-[*1..{max_hops}]-(end)
                        {rel_filter}
                        WITH path,
                             [r IN relationships(path) | {{
                                 type: type(r),
                                 properties: properties(r),
                                 source: startNode(r).name,
                                 target: endNode(r).name
                             }}] as path_rels,
                             [n IN nodes(path) | {{
                                 name: n.name,
                                 id: n.id,
                                 labels: labels(n)
                             }}] as path_nodes,
                             length(path) as path_length
                        RETURN path_nodes, path_rels, path_length
                        ORDER BY path_length ASC
                        LIMIT $limit_paths
                        """

                        path_results = session.run(
                            path_query,
                            start_name=start['name'],
                            start_id=start['id'],
                            end_name=end['name'],
                            end_id=end['id'],
                            path_types=path_relationship_types,
                            limit_paths=limit_paths
                        )

                        for path_record in path_results:
                            path_info = {
                                'start_entity': start,
                                'end_entity': end,
                                'nodes': path_record['path_nodes'],
                                'relationships': path_record['path_rels'],
                                'length': path_record['path_length']
                            }

                            # Calculate path score
                            # Score = (start_sim + end_sim) / 2 - (path_length * 0.1) + property_richness
                            property_count = sum(
                                len(rel.get('properties', {}))
                                for rel in path_info['relationships']
                            )
                            property_richness = min(property_count * 0.05, 0.5)  # Cap at 0.5

                            path_score = (
                                (start['similarity'] + end['similarity']) / 2.0
                                - (path_info['length'] * 0.1)
                                + property_richness
                            )
                            path_info['score'] = path_score

                            all_paths.append(path_info)

                if not all_paths:
                    return f"No paths found between '{start_entity}' and '{end_entity}' within {max_hops} hops"

                # Sort paths by score
                all_paths.sort(key=lambda p: p['score'], reverse=True)

                print(f"  ✓ Found {len(all_paths)} paths\n")

                # Format output
                context_parts = []
                context_parts.append(f"\n## Semantic Path Search: '{start_entity}' → '{end_entity}'")
                context_parts.append(f"**Found {len(all_paths)} paths** (max {max_hops} hops)\n")

                for idx, path in enumerate(all_paths[:limit_paths], 1):
                    start_e = path['start_entity']
                    end_e = path['end_entity']
                    nodes = path['nodes']
                    relationships = path['relationships']
                    path_length = path['length']
                    score = path['score']

                    # Path header
                    context_parts.append(f"\n### Path {idx} (length: {path_length}, score: {score:.3f})")
                    context_parts.append(f"**Start**: {start_e['name']} [{', '.join(start_e['labels'])}] (sim: {start_e['similarity']:.3f})")
                    context_parts.append(f"**End**: {end_e['name']} [{', '.join(end_e['labels'])}] (sim: {end_e['similarity']:.3f})")

                    # Path visualization
                    path_str = ""
                    for i, node in enumerate(nodes):
                        labels_str = ', '.join(node['labels'])
                        path_str += f"**{node['name']}** [{labels_str}]"

                        if i < len(relationships):
                            rel = relationships[i]
                            path_str += f" -[{rel['type']}]→ "

                    context_parts.append(f"\n**Path**: {path_str}")

                    # Relationship properties (ALL SPG properties)
                    context_parts.append(f"\n**Relationships along path**:")
                    for i, rel in enumerate(relationships, 1):
                        context_parts.append(f"\n{i}. **{rel['source']}** -[{rel['type']}]→ **{rel['target']}**")

                        props = rel.get('properties', {})
                        if props:
                            context_parts.append("   Properties:")
                            for key, value in props.items():
                                context_parts.append(f"     • {key}: {value}")
                        else:
                            context_parts.append("   (No properties)")

                return "\n".join(context_parts)

        except Exception as e:
            return f"Error performing semantic path search: {str(e)}"

    def question_aware_subgraph_retrieval(
        self,
        question: str,
        entities: list[str] = None,
        max_hops: int = 2,
        include_context: bool = True,
        property_filters: dict = None
    ) -> str:
        """
        Retrieve the optimal subgraph for answering a specific question.

        This method uses a multi-stage approach to extract the most relevant subgraph:
        1. Entity Identification: Find seed entities from question
        2. Type Inference: Infer required entity/relationship types from question
        3. Subgraph Expansion: Expand from seeds with relevance-based expansion
        4. Property Filtering: Include only relevant properties based on question
        5. Context Enrichment: Add source chunks and supporting entities

        Args:
            question: The user's question
            entities: Pre-extracted entity names (optional, will auto-extract if None)
            max_hops: Maximum subgraph expansion depth (default: 2)
            include_context: Include source chunks for context (default: True)
            property_filters: Filter by specific properties (e.g., {"period": "Q4 2023"})

        Returns:
            Formatted subgraph context optimized for the question

        Example:
            question: "What was 3M's revenue in Q4 2023?"
            → Returns subgraph: 3M -[REPORTED_FINANCIALS{revenue, period="Q4 2023"}]-> FinancialStatement
        """
        if not self.embedding_model:
            return "Question-aware subgraph retrieval not available: embedding model not loaded"

        try:
            print(f"\n[Subgraph Retrieval] Question: {question}")

            with self.driver.session(database=self.database) as session:
                # Stage 1: Identify seed entities using vector similarity on the full question
                question_embedding = self.generate_embedding(question)

                # Find top entities most relevant to the entire question
                seed_query = """
                MATCH (e)
                WHERE e.embeddings IS NOT NULL
                WITH e,
                     reduce(dot = 0.0, i IN range(0, size(e.embeddings)-1) |
                          dot + e.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN e.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
                WHERE similarity >= 0.4
                RETURN e.name as name,
                       e.id as id,
                       labels(e) as labels,
                       e.description as description,
                       similarity
                ORDER BY similarity DESC
                LIMIT 5
                """

                seed_results = session.run(seed_query, query_vector=question_embedding)
                seed_entities = [
                    {
                        'name': r['name'],
                        'id': r['id'],
                        'labels': r['labels'],
                        'description': r['description'],
                        'similarity': r['similarity']
                    }
                    for r in seed_results
                ]

                if not seed_entities:
                    return f"No relevant entities found for question: {question}"

                print(f"  Stage 1: Found {len(seed_entities)} seed entities")
                for e in seed_entities[:3]:
                    print(f"    - {e['name']} [{', '.join(e['labels'])}] (sim: {e['similarity']:.3f})")

                # Stage 2: Infer question type and required schema elements
                # Use keywords to infer what types of entities/relationships are needed
                question_lower = question.lower()

                required_rel_types = []
                if any(word in question_lower for word in ['revenue', 'profit', 'earnings', 'financial', 'income', 'sales']):
                    required_rel_types.append('REPORTED_FINANCIALS')
                if any(word in question_lower for word in ['owns', 'subsidiary', 'acquisition', 'ownership']):
                    required_rel_types.append('OWNS')
                if any(word in question_lower for word in ['executive', 'ceo', 'cfo', 'officer', 'employee']):
                    required_rel_types.append('EMPLOYS')
                if any(word in question_lower for word in ['filed', 'filing', '10-k', '10-q', 'report']):
                    required_rel_types.append('FILED')

                print(f"  Stage 2: Inferred relationship types: {required_rel_types if required_rel_types else 'ALL'}")

                # Stage 3: Expand subgraph from seeds with relevance-based traversal
                seed_ids = [e['id'] for e in seed_entities]
                seed_names = [e['name'] for e in seed_entities]

                # Build property filter clause
                property_filter_clause = ""
                if property_filters:
                    filter_conditions = []
                    for key, value in property_filters.items():
                        filter_conditions.append(f"r.{key} =~ '.*{value}.*'")
                    if filter_conditions:
                        property_filter_clause = "AND (" + " OR ".join(filter_conditions) + ")"

                # Build relationship type filter
                rel_type_filter = ""
                if required_rel_types:
                    rel_type_filter = f"AND type(r) IN {required_rel_types}"

                # Subgraph expansion query: Get k-hop neighborhood with relevance scoring
                expansion_query = f"""
                // Start from seed entities
                MATCH (seed)
                WHERE seed.id IN $seed_ids OR seed.name IN $seed_names

                // Expand up to max_hops with relationship filtering
                MATCH path = (seed)-[*1..{max_hops}]-(related)
                WHERE related IS NOT NULL

                // Extract relationships from path
                WITH seed, related, path, relationships(path) as path_rels
                UNWIND path_rels as r

                // Filter by relationship types if specified
                WITH DISTINCT seed, related, r
                WHERE $rel_types IS NULL OR type(r) IN $rel_types

                // Get source and target nodes
                WITH seed, related, r, startNode(r) as source, endNode(r) as target

                // Get source chunks for context
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(source)

                RETURN DISTINCT
                    source.name as source_name,
                    source.id as source_id,
                    labels(source) as source_labels,
                    source.description as source_desc,
                    type(r) as rel_type,
                    properties(r) as rel_props,
                    target.name as target_name,
                    target.id as target_id,
                    labels(target) as target_labels,
                    target.description as target_desc,
                    collect(DISTINCT {{
                        content: chunk.content,
                        page_number: chunk.page_number
                    }}) as source_chunks
                LIMIT 100
                """

                subgraph_results = session.run(
                    expansion_query,
                    seed_ids=seed_ids,
                    seed_names=seed_names,
                    rel_types=required_rel_types if required_rel_types else None
                )

                # Stage 4: Structure and format the subgraph
                nodes = {}
                edges = []

                for record in subgraph_results:
                    # Add source node
                    source_key = (record['source_name'], record['source_id'])
                    if source_key not in nodes:
                        nodes[source_key] = {
                            'name': record['source_name'],
                            'id': record['source_id'],
                            'labels': record['source_labels'],
                            'description': record['source_desc'],
                            'chunks': record['source_chunks']
                        }

                    # Add target node
                    target_key = (record['target_name'], record['target_id'])
                    if target_key not in nodes:
                        nodes[target_key] = {
                            'name': record['target_name'],
                            'id': record['target_id'],
                            'labels': record['target_labels'],
                            'description': record['target_desc'],
                            'chunks': []
                        }

                    # Add edge
                    edges.append({
                        'source': record['source_name'],
                        'target': record['target_name'],
                        'type': record['rel_type'],
                        'properties': record['rel_props']
                    })

                print(f"  Stage 3: Extracted subgraph - {len(nodes)} nodes, {len(edges)} edges")

                if not nodes:
                    return "No relevant subgraph found for the question"

                # Stage 5: Format output
                context_parts = []
                context_parts.append(f"\n## Question-Specific Subgraph")
                context_parts.append(f"**Question**: {question}")
                context_parts.append(f"**Subgraph Size**: {len(nodes)} entities, {len(edges)} relationships\n")

                # Show nodes
                context_parts.append("### Entities in Subgraph:")
                for idx, (node_key, node) in enumerate(list(nodes.items())[:10], 1):
                    labels_str = ', '.join(node['labels'])
                    context_parts.append(f"\n{idx}. **{node['name']}** [{labels_str}]")
                    if node.get('description'):
                        context_parts.append(f"   Description: {node['description']}")

                    # Add source chunks if requested
                    if include_context and node.get('chunks'):
                        chunks = [c for c in node['chunks'] if c.get('content')]
                        if chunks:
                            context_parts.append(f"   Source Evidence: \"{chunks[0]['content'][:200]}...\"")

                # Show edges with ALL properties
                context_parts.append("\n### Relationships in Subgraph:")
                for idx, edge in enumerate(edges[:20], 1):
                    context_parts.append(f"\n{idx}. **{edge['source']}** -[{edge['type']}]→ **{edge['target']}**")

                    if edge['properties']:
                        context_parts.append("   Properties:")
                        for key, value in edge['properties'].items():
                            # Highlight properties mentioned in question
                            if any(word in question_lower for word in [key.lower(), str(value).lower()]):
                                context_parts.append(f"     • **{key}: {value}** ⭐")
                            else:
                                context_parts.append(f"     • {key}: {value}")

                return "\n".join(context_parts)

        except Exception as e:
            return f"Error in question-aware subgraph retrieval: {str(e)}"

    def entity_graph_search(self, entities: str, depth: int = 1) -> str:
        """
        Search for relationships BETWEEN multiple entities in the knowledge graph.

        This method finds entities from the input list, then discovers relationships
        that connect these entities to each other, extracting relationship properties
        and source chunks for the entities involved.

        Args:
            entities: Comma-separated list of entity names to search for
            depth: Unused (kept for backward compatibility)

        Returns:
            Formatted context showing relationships between the entities with:
            - Entity information (name, type, description)
            - Relationships between entities with properties
            - Source chunks for each entity involved
        """
        if not self.embedding_model:
            return f"Entity search not available: embedding model not loaded"

        try:
            # Parse entities - split by comma
            entity_list = [e.strip() for e in entities.split(',') if e.strip()]

            if not entity_list:
                return "No valid entities provided"

            if len(entity_list) < 1:
                return "Please provide at least one entity name"

            print(f"\n[Entity Graph Search] Finding {len(entity_list)} entities and relationships between them...")

            # Generate embeddings for all entities
            entity_embeddings = {}
            for entity_name in entity_list:
                entity_embeddings[entity_name] = self.generate_embedding(entity_name)

            with self.driver.session(database=self.database) as session:
                # Step 1: Find all entities using vector similarity
                found_entities = []

                for entity_name, query_embedding in entity_embeddings.items():
                    find_entity_query = """
                    MATCH (e)
                    WHERE e.embeddings IS NOT NULL
                    WITH e,
                         reduce(dot = 0.0, i IN range(0, size(e.embeddings)-1) |
                              dot + e.embeddings[i] * $query_vector[i]) /
                              (sqrt(reduce(sum = 0.0, x IN e.embeddings | sum + x * x)) *
                               sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
                    WHERE similarity >= 0.5
                    ORDER BY similarity DESC
                    LIMIT 1
                    RETURN e.name as name,
                           e.id as id,
                           labels(e)[0] as node_type,
                           e.label as label,
                           e.description as description,
                           similarity
                    """

                    result = session.run(find_entity_query, query_vector=query_embedding)
                    record = result.single()

                    if record:
                        found_entities.append({
                            'query': entity_name,
                            'name': record['name'],
                            'id': record['id'] or record['name'],
                            'type': record['node_type'] or record['label'],
                            'description': record['description'],
                            'similarity': record['similarity']
                        })
                        print(f"  ✓ Found: {record['name']} (similarity: {record['similarity']:.3f})")
                    else:
                        print(f"  ✗ Not found: {entity_name}")

                if not found_entities:
                    return f"None of the {len(entity_list)} entities were found in the knowledge graph"

                if len(found_entities) == 1:
                    # Only one entity found, show its information and connections
                    entity = found_entities[0]

                    # Get source chunks for this entity
                    chunks_query = """
                    MATCH (e)
                    WHERE e.name = $entity_name OR e.id = $entity_id
                    OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(e)
                    RETURN collect(DISTINCT {
                        id: chunk.id,
                        content: chunk.content,
                        chunk_index: chunk.chunk_index,
                        page_number: chunk.page_number
                    }) as source_chunks
                    """

                    result = session.run(chunks_query, entity_name=entity['name'], entity_id=entity['id'])
                    record = result.single()
                    chunks_raw = [c for c in record['source_chunks'] if c.get('id')]

                    # Deduplicate chunks by ID
                    seen_ids = set()
                    chunks = []
                    for chunk in chunks_raw:
                        chunk_id = chunk.get('id')
                        if chunk_id not in seen_ids:
                            seen_ids.add(chunk_id)
                            chunks.append(chunk)

                    context = f"\n## Found 1 Entity\n"
                    context += f"\n### {entity['name']} [{entity['type']}]"
                    if entity['description']:
                        context += f"\n- Description: {entity['description']}"
                    context += f"\n- Similarity: {entity['similarity']:.3f}"

                    if chunks:
                        context += "\n\n### Source Chunks:"
                        for chunk in chunks[:5]:
                            context += f"\n  - Chunk {chunk.get('chunk_index', '?')}, Page {chunk.get('page_number', '?')}"
                            if chunk.get('content'):
                                context += f"\n    {chunk['content']}"

                    return context

                # Step 2: Find relationships BETWEEN the found entities
                print(f"\n[Entity Graph Search] Finding relationships between {len(found_entities)} entities...")

                entity_ids = [e['id'] for e in found_entities]
                entity_names = [e['name'] for e in found_entities]

                # Query to find relationships between any pair of found entities
                relationships_query = """
                MATCH (e1)-[r]-(e2)
                WHERE (e1.name IN $entity_names OR e1.id IN $entity_ids)
                  AND (e2.name IN $entity_names OR e2.id IN $entity_ids)
                  AND id(e1) < id(e2)  // Avoid duplicates
                WITH e1, e2, r,
                     CASE WHEN startNode(r) = e1 THEN 'outgoing' ELSE 'incoming' END as direction

                // Get source chunks for both entities
                OPTIONAL MATCH (chunk1:Chunk)-[:SOURCE]->(e1)
                OPTIONAL MATCH (chunk2:Chunk)-[:SOURCE]->(e2)

                RETURN e1.name as entity1_name,
                       e1.id as entity1_id,
                       labels(e1)[0] as entity1_type,
                       e1.label as entity1_label,
                       e1.description as entity1_desc,
                       e2.name as entity2_name,
                       e2.id as entity2_id,
                       labels(e2)[0] as entity2_type,
                       e2.label as entity2_label,
                       e2.description as entity2_desc,
                       type(r) as relation_type,
                       properties(r) as relation_properties,
                       direction,
                       collect(DISTINCT {
                           id: chunk1.id,
                           content: chunk1.content,
                           chunk_index: chunk1.chunk_index,
                           page_number: chunk1.page_number
                       }) as entity1_chunks,
                       collect(DISTINCT {
                           id: chunk2.id,
                           content: chunk2.content,
                           chunk_index: chunk2.chunk_index,
                           page_number: chunk2.page_number
                       }) as entity2_chunks
                LIMIT 20
                """

                result = session.run(relationships_query, entity_names=entity_names, entity_ids=entity_ids)
                relationships = list(result)

                # Step 3: If no relationships found, expand entities and try again
                expansion_depth = 0
                max_expansions = 2  # Try expanding up to 2 times
                expanded_entities = list(found_entities)  # Start with original entities
                original_entity_count = len(found_entities)

                while not relationships and expansion_depth < max_expansions:
                    expansion_depth += 1
                    print(f"\n[Entity Graph Search] No direct relationships found. Expanding entities (depth {expansion_depth})...")

                    # Get 1-hop neighbors for each entity
                    expansion_query = """
                    MATCH (e)
                    WHERE e.name IN $entity_names OR e.id IN $entity_ids
                    MATCH (e)-[r]-(neighbor)
                    WHERE neighbor IS NOT NULL
                    RETURN DISTINCT
                        neighbor.name as name,
                        neighbor.id as id,
                        labels(neighbor)[0] as node_type,
                        neighbor.label as label,
                        neighbor.description as description,
                        type(r) as connection_type
                    LIMIT 20
                    """

                    expansion_result = session.run(expansion_query, entity_names=entity_names, entity_ids=entity_ids)
                    expansion_records = list(expansion_result)

                    if not expansion_records:
                        print(f"  ✗ No neighbors found to expand")
                        break

                    # Add neighbors to entity set
                    new_entities_added = 0
                    existing_ids = {e['id'] for e in expanded_entities}

                    for record in expansion_records:
                        neighbor_id = record['id'] or record['name']
                        if neighbor_id not in existing_ids:
                            expanded_entities.append({
                                'name': record['name'],
                                'id': neighbor_id,
                                'type': record['node_type'] or record['label'],
                                'description': record['description'],
                                'similarity': 0.0,  # Expanded entity, not directly searched
                                'expanded': True,
                                'connection_type': record['connection_type']
                            })
                            existing_ids.add(neighbor_id)
                            new_entities_added += 1

                    print(f"  ✓ Added {new_entities_added} neighbor entities (total now: {len(expanded_entities)})")

                    # Try finding relationships again with expanded entity set
                    expanded_entity_names = [e['name'] for e in expanded_entities]
                    expanded_entity_ids = [e['id'] for e in expanded_entities]

                    result = session.run(
                        relationships_query,
                        entity_names=expanded_entity_names,
                        entity_ids=expanded_entity_ids
                    )
                    relationships = list(result)

                    if relationships:
                        print(f"  ✓ Found {len(relationships)} relationships after expansion!")
                        # Update found_entities to include expanded set
                        found_entities = expanded_entities
                        entity_names = expanded_entity_names
                        entity_ids = expanded_entity_ids
                        break

                if not relationships:
                    # Still no relationships after expansion
                    context = f"\n## Found {len(found_entities)} Entities\n"
                    for idx, entity in enumerate(found_entities, 1):
                        context += f"\n### {idx}. {entity['name']} [{entity['type']}]"
                        if entity['description']:
                            context += f"\n- Description: {entity['description']}"
                        if entity.get('similarity', 0) > 0:
                            context += f"\n- Similarity: {entity['similarity']:.3f}"
                        if entity.get('expanded'):
                            context += f"\n- (Expanded via {entity.get('connection_type', 'relationship')})"

                    context += f"\n\n❌ No relationships found between these entities (tried {expansion_depth} expansion levels)"
                    return context

                # Format the output
                print(f"  ✓ Found {len(relationships)} relationships\n")

                # Count original vs expanded entities
                original_count = sum(1 for e in found_entities if not e.get('expanded', False))
                expanded_count = len(found_entities) - original_count

                if expanded_count > 0:
                    context = f"\n## Found {original_count} Original + {expanded_count} Expanded = {len(found_entities)} Total Entities and {len(relationships)} Relationships\n"
                    context += f"_(Expanded through {expansion_depth} hop(s) to find relationships)_\n"
                else:
                    context = f"\n## Found {len(found_entities)} Entities and {len(relationships)} Relationships\n"

                # Show entities - separate original from expanded
                if expanded_count > 0:
                    context += "\n### Original Entities:"
                    for idx, entity in enumerate([e for e in found_entities if not e.get('expanded', False)], 1):
                        context += f"\n{idx}. **{entity['name']}** [{entity['type']}]"
                        if entity['description']:
                            context += f" - {entity['description'][:100]}..."
                        context += f" (similarity: {entity['similarity']:.3f})"

                    context += "\n\n### Expanded Entities:"
                    for idx, entity in enumerate([e for e in found_entities if e.get('expanded', False)], 1):
                        context += f"\n{idx}. **{entity['name']}** [{entity['type']}]"
                        if entity['description']:
                            context += f" - {entity['description'][:100]}..."
                        context += f" (via {entity.get('connection_type', 'relationship')})"
                else:
                    context += "\n### Entities Found:"
                    for idx, entity in enumerate(found_entities, 1):
                        context += f"\n{idx}. **{entity['name']}** [{entity['type']}]"
                        if entity['description']:
                            context += f" - {entity['description'][:100]}..."
                        if entity.get('similarity', 0) > 0:
                            context += f" (similarity: {entity['similarity']:.3f})"

                # Show relationships
                context += "\n\n### Relationships Between Entities:"
                for idx, rel in enumerate(relationships, 1):
                    entity1_name = rel['entity1_name']
                    entity1_type = rel['entity1_type'] or rel['entity1_label']
                    entity2_name = rel['entity2_name']
                    entity2_type = rel['entity2_type'] or rel['entity2_label']
                    relation_type = rel['relation_type']
                    direction = rel['direction']
                    props = rel['relation_properties']

                    # Format relationship
                    if direction == 'outgoing':
                        context += f"\n\n**{idx}. {entity1_name}** [{entity1_type}] →{relation_type}→ **{entity2_name}** [{entity2_type}]"
                    else:
                        context += f"\n\n**{idx}. {entity1_name}** [{entity1_type}] ←{relation_type}← **{entity2_name}** [{entity2_type}]"

                    # Add relationship properties
                    if props and isinstance(props, dict) and len(props) > 0:
                        context += "\n  **Properties:**"
                        for key, value in props.items():  # Show ALL properties
                            context += f"\n    • {key}: {value}"

                    # Deduplicate and categorize chunks
                    entity1_chunks_raw = [c for c in rel['entity1_chunks'] if c.get('id')]
                    entity2_chunks_raw = [c for c in rel['entity2_chunks'] if c.get('id')]

                    # Deduplicate within each entity
                    seen_ids_e1 = set()
                    entity1_chunks_dedup = []
                    for chunk in entity1_chunks_raw:
                        chunk_id = chunk.get('id')
                        if chunk_id not in seen_ids_e1:
                            seen_ids_e1.add(chunk_id)
                            entity1_chunks_dedup.append(chunk)

                    seen_ids_e2 = set()
                    entity2_chunks_dedup = []
                    for chunk in entity2_chunks_raw:
                        chunk_id = chunk.get('id')
                        if chunk_id not in seen_ids_e2:
                            seen_ids_e2.add(chunk_id)
                            entity2_chunks_dedup.append(chunk)

                    # Find shared chunks (same ID in both entities)
                    shared_chunk_ids = seen_ids_e1.intersection(seen_ids_e2)

                    # Separate into shared and unique chunks
                    entity1_unique = [c for c in entity1_chunks_dedup if c.get('id') not in shared_chunk_ids]
                    entity2_unique = [c for c in entity2_chunks_dedup if c.get('id') not in shared_chunk_ids]
                    shared_chunks = [c for c in entity1_chunks_dedup if c.get('id') in shared_chunk_ids]

                    # Display shared chunks first (if any)
                    if shared_chunks:
                        context += f"\n\n  **Shared Source Chunks (from both entities):**"
                        for chunk in shared_chunks[:3]:
                            context += f"\n    - Chunk {chunk.get('chunk_index', '?')}, Page {chunk.get('page_number', '?')}"
                            if chunk.get('content'):
                                context += f"\n      \"{chunk['content']}\""

                    # Display entity1 unique chunks
                    if entity1_unique:
                        context += f"\n\n  **Source Chunks from {entity1_name} only:**"
                        for chunk in entity1_unique[:3]:
                            context += f"\n    - Chunk {chunk.get('chunk_index', '?')}, Page {chunk.get('page_number', '?')}"
                            if chunk.get('content'):
                                context += f"\n      \"{chunk['content']}\""

                    # Display entity2 unique chunks
                    if entity2_unique:
                        context += f"\n\n  **Source Chunks from {entity2_name} only:**"
                        for chunk in entity2_unique[:3]:
                            context += f"\n    - Chunk {chunk.get('chunk_index', '?')}, Page {chunk.get('page_number', '?')}"
                            if chunk.get('content'):
                                context += f"\n      \"{chunk['content']}\""

                return context

        except Exception as e:
            return f"Error performing entity graph search: {str(e)}"
    def _reciprocal_rank_fusion(self, result_lists: list[list[dict]], k: int = 60) -> list[dict]:
        """
        Fuse multiple ranked result lists using Reciprocal Rank Fusion (RRF).

        RRF is a simple yet effective algorithm for combining results from multiple
        retrieval strategies. Each result's score is calculated as:
        RRF score = sum(1 / (k + rank)) across all result lists

        Args:
            result_lists: List of ranked result lists, each containing dicts with 'id' and other fields
            k: RRF constant (typically 60), controls score decay

        Returns:
            Fused and re-ranked list of results
        """
        scores = {}

        for result_list in result_lists:
            for rank, result in enumerate(result_list, start=1):
                entity_id = result.get('id') or result.get('name')  # Use id or name as key
                score = 1.0 / (k + rank)

                if entity_id not in scores:
                    scores[entity_id] = {
                        'result': result,
                        'rrf_score': 0.0,
                        'sources': []  # Track which strategies found this result
                    }
                scores[entity_id]['rrf_score'] += score
                scores[entity_id]['sources'].append(result.get('source', 'unknown'))

        # Sort by RRF score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )

        # Return results with RRF scores
        return [
            {**item['result'], 'rrf_score': item['rrf_score'], 'fusion_sources': item['sources']}
            for item in sorted_results
        ]

    def _vector_search_scored(self, query: str, limit: int = 10, threshold: float = 0.4) -> list[dict]:
        """
        Vector similarity search on Entity nodes with source chunk retrieval.

        Searches Entity nodes using embeddings, then retrieves the source Chunks
        that contain actual text mentioning these entities.

        Args:
            query: Search query
            limit: Maximum results
            threshold: Minimum similarity threshold

        Returns:
            List of dicts with entity information, scores, and source chunks
        """
        if not self.embedding_model:
            return []

        try:
            query_embedding = self.generate_embedding(query)

            with self.driver.session(database=self.database) as session:
                # Search Entity nodes with embeddings and retrieve source chunks
                cypher_query = """
                MATCH (e:Entity)
                WHERE e.embeddings IS NOT NULL
                WITH e,
                     reduce(dot = 0.0, i IN range(0, size(e.embeddings)-1) |
                          dot + e.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN e.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
                WHERE similarity >= $threshold

                // Get source chunks that mention this entity
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(e)
                WITH e, similarity,
                     collect(DISTINCT {
                         id: chunk.id,
                         content: chunk.content,
                         chunk_index: chunk.chunk_index,
                         page_number: chunk.page_number,
                         word_count: chunk.word_count
                     }) as source_chunks

                // Get relationships to other entities
                OPTIONAL MATCH (e)-[r]-(related:Entity)
                WITH e, similarity, source_chunks,
                     collect(DISTINCT {
                         relation: type(r),
                         node: related.name,
                         official_name: related.official_name,
                         direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END
                     }) as relationships

                RETURN e.name as name,
                       e.label as type,
                       e.node_type as node_type,
                       e.id as id,
                       e.official_name as official_name,
                       e.description as description,
                       similarity as score,
                       source_chunks,
                       relationships
                ORDER BY similarity DESC
                LIMIT $limit
                """

                result = session.run(
                    cypher_query,
                    query_vector=query_embedding,
                    threshold=threshold,
                    limit=limit
                )

                return [
                    {
                        'id': record['id'] or record['name'],
                        'name': record['name'],
                        'type': record['node_type'] or record['type'],
                        'official_name': record['official_name'],
                        'description': record['description'],
                        'score': record['score'],
                        'source_chunks': record['source_chunks'],
                        'relationships': record['relationships'],
                        'source': 'vector'
                    }
                    for record in result
                ]
        except Exception as e:
            print(f"[Hybrid Search] Vector search error: {e}")
            return []

    def _chunk_text_search_scored(self, query: str, limit: int = 10) -> list[dict]:
        """
        Text-based search directly on Chunk content.

        Searches Chunk nodes for keyword matches in their text content.
        This provides lexical matching on the actual document text.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of dicts with chunk information and linked entities
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Search Chunk content for keywords
                cypher_query = """
                MATCH (c:Chunk)
                WHERE c.content IS NOT NULL AND toLower(c.content) CONTAINS toLower($search_text)

                // Get entities linked to this chunk
                OPTIONAL MATCH (c)-[:SOURCE]->(e:Entity)
                WITH c,
                     CASE
                         WHEN toLower(c.content) = toLower($search_text) THEN 1.0
                         WHEN toLower(c.content) CONTAINS toLower($search_text) THEN 0.7
                         ELSE 0.4
                     END as score,
                     collect(DISTINCT {
                         name: e.name,
                         official_name: e.official_name,
                         type: e.node_type,
                         id: e.id
                     }) as linked_entities

                RETURN c.id as id,
                       c.content as content,
                       c.chunk_index as chunk_index,
                       c.page_number as page_number,
                       c.word_count as word_count,
                       score,
                       linked_entities
                ORDER BY score DESC, c.chunk_index ASC
                LIMIT $limit
                """

                result = session.run(cypher_query, search_text=query, limit=limit)

                return [
                    {
                        'id': record['id'],
                        'name': f"Chunk {record['chunk_index']}: {record['content'][:60]}..." if record['content'] else f"Chunk {record['chunk_index']}",
                        'type': 'Chunk',
                        'content': record['content'],
                        'chunk_index': record['chunk_index'],
                        'page_number': record['page_number'],
                        'word_count': record['word_count'],
                        'score': record['score'],
                        'linked_entities': record['linked_entities'],
                        'is_chunk': True,
                        'source': 'chunk_text'
                    }
                    for record in result
                ]
        except Exception as e:
            print(f"[Hybrid Search] Chunk text search error: {e}")
            return []

    def _text_search_scored(self, query: str, limit: int = 10) -> list[dict]:
        """
        Text-based keyword search returning scored results for fusion.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of dicts with entity information and scores
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Only search properties that exist in the schema
                cypher_query = """
                MATCH (n)
                WHERE toLower(n.name) CONTAINS toLower($search_text)
                   OR (n.description IS NOT NULL AND toLower(n.description) CONTAINS toLower($search_text))
                OPTIONAL MATCH (n)-[r]-(related)
                WITH n,
                     CASE
                         WHEN toLower(n.name) = toLower($search_text) THEN 1.0
                         WHEN toLower(n.name) CONTAINS toLower($search_text) THEN 0.8
                         WHEN n.description IS NOT NULL AND toLower(n.description) CONTAINS toLower($search_text) THEN 0.6
                         ELSE 0.4
                     END as score,
                     collect({
                         relation: type(r),
                         node: related.name,
                         direction: CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END
                     }) as relationships
                RETURN n.name as name,
                       n.label as type,
                       n.id as id,
                       n.description as description,
                       score,
                       relationships
                ORDER BY score DESC
                LIMIT $limit
                """

                result = session.run(cypher_query, search_text=query, limit=limit)

                return [
                    {
                        'id': record['id'] or record['name'],
                        'name': record['name'],
                        'type': record['type'],
                        'description': record['description'],
                        'score': record['score'],
                        'relationships': record['relationships'],
                        'source': 'text'
                    }
                    for record in result
                ]
        except Exception as e:
            print(f"[Hybrid Search] Text search error: {e}")
            return []

    def _entity_search_scored(self, query: str, limit: int = 5) -> list[dict]:
        """
        Entity-based graph search with neighborhood and source chunk retrieval.

        Uses vector similarity to find entities, then explores their graph neighborhood
        and retrieves source chunks containing actual text.

        Args:
            query: Search query (entity name or description)
            limit: Maximum entities to find

        Returns:
            List of dicts with entity information, relationships, and source chunks
        """
        if not self.embedding_model:
            return []

        try:
            query_embedding = self.generate_embedding(query)

            with self.driver.session(database=self.database) as session:
                cypher_query = """
                MATCH (e:Entity)
                WHERE e.embeddings IS NOT NULL
                WITH e,
                     reduce(dot = 0.0, i IN range(0, size(e.embeddings)-1) |
                          dot + e.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN e.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
                WHERE similarity >= 0.5
                ORDER BY similarity DESC
                LIMIT $limit

                // Get source chunks that mention this entity
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(e)
                WITH e, similarity,
                     collect(DISTINCT {
                         id: chunk.id,
                         content: chunk.content,
                         chunk_index: chunk.chunk_index,
                         page_number: chunk.page_number,
                         word_count: chunk.word_count
                     })[..5] as source_chunks

                // Get relationships to other entities
                OPTIONAL MATCH (e)-[r]-(related:Entity)
                WITH e, similarity, source_chunks,
                     collect(DISTINCT {
                         relation: type(r),
                         node: related.name,
                         official_name: related.official_name,
                         direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END
                     }) as relationships

                RETURN e.name as name,
                       e.label as type,
                       e.node_type as node_type,
                       e.id as id,
                       e.official_name as official_name,
                       e.description as description,
                       similarity as score,
                       source_chunks,
                       relationships
                """

                result = session.run(
                    cypher_query,
                    query_vector=query_embedding,
                    limit=limit
                )

                return [
                    {
                        'id': record['id'] or record['name'],
                        'name': record['name'],
                        'type': record['node_type'] or record['type'],
                        'official_name': record['official_name'],
                        'description': record['description'],
                        'score': record['score'],
                        'source_chunks': record['source_chunks'],
                        'relationships': record['relationships'],
                        'source': 'entity_graph'
                    }
                    for record in result
                ]
        except Exception as e:
            print(f"[Hybrid Search] Entity search error: {e}")
            return []

    def _format_hybrid_results(self, fused_results: list[dict]) -> str:
        """
        Format fused results into readable context string.

        Args:
            fused_results: List of fused results with RRF scores

        Returns:
            Formatted context string
        """
        if not fused_results:
            return "No results found"

        context_parts = []

        for idx, result in enumerate(fused_results, 1):
            name = result.get('name', 'Unknown')
            entity_type = result.get('type', 'Unknown')
            entity_id = result.get('id')
            description = result.get('description')
            rrf_score = result.get('rrf_score', 0.0)
            original_score = result.get('score', 0.0)
            fusion_sources = result.get('fusion_sources', [])
            is_chunk = result.get('is_chunk', False)

            # Check if this is a Chunk result (direct text search)
            if is_chunk:
                # Format Chunk result with actual text content
                content = result.get('content', '')
                chunk_index = result.get('chunk_index', '?')
                page_number = result.get('page_number', '?')
                word_count = result.get('word_count', 0)
                linked_entities = result.get('linked_entities', [])

                entity_desc = f"\n**{idx}. Chunk {chunk_index}** (Page {page_number})"
                entity_desc += f"\n  - RRF Score: {rrf_score:.4f} | Original Score: {original_score:.3f}"
                entity_desc += f"\n  - Found by: {', '.join(set(fusion_sources))}"
                entity_desc += f"\n  - Word Count: {word_count}"

                # Show actual content
                if content:
                    entity_desc += f"\n  - Content:\n    \"{content}\""

                # Show linked entities
                if linked_entities:
                    entity_desc += "\n  - Mentions Entities:"
                    for entity in linked_entities[:5]:
                        if entity.get('name'):
                            official = entity.get('official_name')
                            entity_name = f"{entity['name']} ({official})" if official and official != entity['name'] else entity['name']
                            entity_desc += f"\n    • {entity_name} [{entity.get('type', 'Entity')}]"
            else:
                # Format Entity result
                official_name = result.get('official_name')
                relationships = result.get('relationships', [])
                source_chunks = result.get('source_chunks', [])

                entity_desc = f"\n**{idx}. {name}** ({entity_type})"
                entity_desc += f"\n  - RRF Score: {rrf_score:.4f} | Original Score: {original_score:.3f}"
                entity_desc += f"\n  - Found by: {', '.join(set(fusion_sources))}"

                if official_name and official_name != name:
                    entity_desc += f"\n  - Official Name: {official_name}"
                if entity_id and entity_id != name:
                    entity_desc += f"\n  - ID: {entity_id}"
                if description:
                    entity_desc += f"\n  - Description: {description}"

                # Add source chunks prominently if available
                if source_chunks and any(c.get('id') for c in source_chunks):
                    entity_desc += "\n  - Source Chunks (Text Evidence):"
                    for chunk in source_chunks[:3]:  # Limit to 3 chunks
                        if chunk.get('content'):
                            chunk_idx = chunk.get('chunk_index', '?')
                            page_num = chunk.get('page_number', '?')
                            entity_desc += f"\n    [Chunk {chunk_idx}, Page {page_num}]: \"{chunk['content']}\""

                # Add relationships
                if relationships:
                    entity_desc += "\n  - Related Entities:"
                    # Show up to 5 most important relationships
                    for rel in relationships[:5]:
                        if rel.get('node'):
                            direction = "→" if rel.get('direction') == 'outgoing' else "←"
                            rel_node = rel['node']
                            official = rel.get('official_name')
                            if official and official != rel_node:
                                rel_node = f"{rel_node} ({official})"
                            entity_desc += f"\n    • {direction} {rel.get('relation', 'UNKNOWN')}: {rel_node}"

            context_parts.append(entity_desc)

        return "\n".join(context_parts)

    def hybrid_search(self, query: str, limit: int = 5, enable_vector: bool = True,
                     enable_text: bool = True, enable_entity: bool = True,
                     enable_chunk: bool = True) -> str:
        """
        Hybrid search combining multiple retrieval strategies with Reciprocal Rank Fusion.

        This method combines FOUR powerful retrieval strategies:
        1. **Vector similarity search on Entities** - Semantic matching using entity embeddings
        2. **Text-based keyword search on Entities** - Lexical matching on entity names/descriptions
        3. **Entity graph search** - Structural matching with entity neighborhoods and relationships
        4. **Direct chunk text search** - Keyword search in actual document text (Chunk nodes)

        Each strategy retrieves source Chunks (actual text) to provide complete context.
        Results are fused using Reciprocal Rank Fusion (RRF) for optimal ranking.

        Args:
            query: Search query
            limit: Maximum number of final results to return
            enable_vector: Enable vector similarity search on Entity nodes
            enable_text: Enable text-based keyword search on Entity nodes
            enable_entity: Enable entity graph search with neighborhoods
            enable_chunk: Enable direct text search on Chunk content

        Returns:
            Formatted context string with fused results including:
            - Entity information (name, official_name, description, type)
            - Source chunks with actual text content from documents
            - Related entities and relationships
            - RRF fusion scores
        """
        print(f"\n[Hybrid Search] Query: {query[:60]}...")
        print(f"[Hybrid Search] Strategies: Vector={enable_vector}, Text={enable_text}, Entity={enable_entity}, Chunk={enable_chunk}")

        result_lists = []

        # Strategy 1: Vector similarity search on Entity nodes
        if enable_vector and self.embedding_model:
            print("[Hybrid Search] Running vector similarity search on Entities...")
            vector_results = self._vector_search_scored(query, limit=limit*2, threshold=0.4)
            if vector_results:
                result_lists.append(vector_results)
                print(f"  ✓ Found {len(vector_results)} entity results")
            else:
                print(f"  ✗ No entity vector results")

        # Strategy 2: Direct chunk text search
        if enable_chunk:
            print("[Hybrid Search] Running direct text search on Chunks...")
            chunk_results = self._chunk_text_search_scored(query, limit=limit*2)
            if chunk_results:
                result_lists.append(chunk_results)
                print(f"  ✓ Found {len(chunk_results)} chunk results")
            else:
                print(f"  ✗ No chunk text results")

        # Strategy 3: Text-based search on Entity names/descriptions
        if enable_text:
            print("[Hybrid Search] Running text-based search on Entities...")
            text_results = self._text_search_scored(query, limit=limit*2)
            if text_results:
                result_lists.append(text_results)
                print(f"  ✓ Found {len(text_results)} entity text results")
            else:
                print(f"  ✗ No entity text results")

        # Strategy 4: Entity graph search with neighborhoods
        if enable_entity and self.embedding_model:
            print("[Hybrid Search] Running entity graph search...")
            entity_results = self._entity_search_scored(query, limit=limit)
            if entity_results:
                result_lists.append(entity_results)
                print(f"  ✓ Found {len(entity_results)} entity graph results")
            else:
                print(f"  ✗ No entity graph results")

        if not result_lists:
            return f"No results found for query: {query}"

        # Apply Reciprocal Rank Fusion
        print(f"[Hybrid Search] Fusing results from {len(result_lists)} strategies using RRF...")
        fused_results = self._reciprocal_rank_fusion(result_lists, k=60)

        print(f"[Hybrid Search] Fused {len(fused_results)} unique results")
        print(f"[Hybrid Search] Returning top {limit} results\n")

        # Format and return top results
        return self._format_hybrid_results(fused_results[:limit])

    def close(self):
        """Close the Neo4j connection."""
        if hasattr(self, 'driver'):
            self.driver.close()


# Create global retriever instance
_retriever = None


def get_retriever() -> Neo4jRetriever:
    """Get or create the Neo4j retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = Neo4jRetriever()
    return _retriever


