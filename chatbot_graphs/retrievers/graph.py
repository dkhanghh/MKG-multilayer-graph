"""
Graph traversal capabilities for Neo4j Retriever.
"""

class GraphMixin:
    """Mixin class for graph traversal functionality."""

    def semantic_path_search(self, start_entity: str, end_entity: str, max_hops: int = 3) -> str:
        """
        Find semantic paths between two entities.

        Args:
            start_entity: Name of the starting entity
            end_entity: Name of the target entity
            max_hops: Maximum number of hops in the path

        Returns:
            Formatted context string with paths found
        """
        if not self.embedding_model:
            return "Semantic path search not available: embedding model not loaded"

        try:
            # Generate embeddings for start and end entities
            start_embedding = self.generate_embedding(start_entity)
            end_embedding = self.generate_embedding(end_entity)

            with self.driver.session(database=self.database) as session:
                # Find start and end nodes using vector similarity
                find_nodes_query = """
                MATCH (n)
                WHERE n.embeddings IS NOT NULL
                WITH n,
                     reduce(dot = 0.0, i IN range(0, size(n.embeddings)-1) |
                          dot + n.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN n.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS similarity
                WHERE similarity >= 0.6
                RETURN n.name as name, n.id as id, similarity
                ORDER BY similarity DESC
                LIMIT 1
                """

                start_node = session.run(find_nodes_query, query_vector=start_embedding).single()
                end_node = session.run(find_nodes_query, query_vector=end_embedding).single()

                if not start_node:
                    return f"Could not find start entity: {start_entity}"
                if not end_node:
                    return f"Could not find end entity: {end_entity}"

                start_id = start_node['id']
                end_id = end_node['id']

                print(f"Finding paths between {start_node['name']} and {end_node['name']}...")

                # Find paths between nodes
                path_query = f"""
                MATCH (start), (end)
                WHERE start.id = $start_id AND end.id = $end_id
                MATCH path = allShortestPaths((start)-[*..{max_hops}]-(end))
                RETURN path
                LIMIT 5
                """

                result = session.run(path_query, start_id=start_id, end_id=end_id)
                paths = list(result)

                if not paths:
                    return f"No paths found between {start_entity} and {end_entity} within {max_hops} hops"

                # Format paths
                context_parts = []
                context_parts.append(f"Found {len(paths)} paths between **{start_node['name']}** and **{end_node['name']}**:")

                for idx, record in enumerate(paths, 1):
                    path = record['path']
                    nodes = path.nodes
                    relationships = path.relationships

                    path_str = f"\nPath {idx}: "
                    for i, node in enumerate(nodes):
                        labels_str = ', '.join(node.labels)
                        path_str += f"**{node['name']}** [{labels_str}]"

                        if i < len(relationships):
                            rel = relationships[i]
                            path_str += f" -[{rel.type}]→ "

                    context_parts.append(f"\n**Path**: {path_str}")

                    # Relationship properties (ALL SPG properties)
                    context_parts.append(f"\n**Relationships along path**:")
                    for i, rel in enumerate(relationships, 1):
                        context_parts.append(f"\n{i}. **{rel.start_node['name']}** -[{rel.type}]→ **{rel.end_node['name']}**")

                        props = dict(rel.items())
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
        """
        if not self.embedding_model:
            return "Question-aware subgraph retrieval not available: embedding model not loaded"

        try:
            print(f"\n[Subgraph Retrieval] Question: {question}")
            question_lower = question.lower()

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

                # Stage 2: Semantic Schema Alignment
                # Use vector similarity to map question to relationship types
                schema_descriptions = {
                    'REPORTED_FINANCIALS': "financial performance revenue profit earnings income sales balance sheet cash flow",
                    'OWNS': "subsidiary acquisition ownership parent company stake investment structure",
                    'EMPLOYS': "executive ceo cfo officer employee management leadership board",
                    'FILED': "regulatory filings 10-k 10-q sec reports annual report",
                    'MENTIONS': "general mentions references discusses topics concepts"
                }
                
                required_rel_types = []
                print("  Stage 2: Analyzing semantic intent...")
                
                # We already have question_embedding from Stage 1
                
                for rel_type, description in schema_descriptions.items():
                    # Generate embedding for the description
                    # Note: In production, these should be cached
                    desc_embedding = self.generate_embedding(description)
                    
                    # Calculate cosine similarity manually
                    dot_product = sum(a * b for a, b in zip(question_embedding, desc_embedding))
                    norm_q = sum(x * x for x in question_embedding) ** 0.5
                    norm_d = sum(x * x for x in desc_embedding) ** 0.5
                    
                    similarity = dot_product / (norm_q * norm_d) if (norm_q * norm_d) > 0 else 0
                    
                    if similarity > 0.45:  # Threshold for relevance
                        required_rel_types.append(rel_type)
                        print(f"    - Matched {rel_type} (sim: {similarity:.3f})")

                print(f"  Stage 2: Inferred relationship types: {required_rel_types if required_rel_types else 'ALL (Unconstrained)'}")

                # Stage 3: Expand subgraph from seeds with relevance-based traversal
                seed_ids = [e['id'] for e in seed_entities]
                seed_names = [e['name'] for e in seed_entities]

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
