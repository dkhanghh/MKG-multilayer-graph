"""
Search capabilities for Neo4j Retriever.
"""

class SearchMixin:
    """Mixin class for search functionality."""

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

        Args:
            query: Search query text
            entity_types: List of entity type labels to filter
            relationship_types: List of relationship types to filter
            limit: Maximum number of results to return
            similarity_threshold: Minimum cosine similarity threshold (0-1)

        Returns:
            Formatted context string with type-filtered entities, relationships, and properties
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

    def _reciprocal_rank_fusion(self, result_lists: list[list[dict]], k: int = 60) -> list[dict]:
        """
        Fuse multiple ranked result lists using Reciprocal Rank Fusion (RRF).
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
