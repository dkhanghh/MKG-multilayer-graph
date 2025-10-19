"""
RAG Chat Graph with Neo4j Knowledge Base Integration

This module implements a conversational agent that retrieves information
from a Neo4j knowledge graph and uses ChatOpenAI to answer questions.
"""

import os
from typing import TypedDict, Annotated, Sequence, Literal
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

# Load environment variables
load_dotenv(override=True)

# Optional Neo4j import
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    print("Warning: neo4j not installed. Install with: pip install neo4j")

# Optional embedding support
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    print("Warning: sentence-transformers not installed. Vector search will not be available.")

# Optional Ollama for embeddings
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False
    print("Warning: ollama not installed. Ollama embedding models will not be available.")

# Optional Gemini for embeddings
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("Warning: google-genai not installed. Gemini embedding models will not be available. Install with: pip install google-genai")


# =============================================================================
# State Definition
# =============================================================================

class ChatState(TypedDict):
    """State for the chat graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retrieved_context: str
    intent: str  # Detected intent of the user query
    original_question: str  # The original user question
    entities: list[str]  # Extracted entities that are relevant to answering the query


# =============================================================================
# Neo4j Connection and Retrieval
# =============================================================================

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

                // Get source chunks linked to the entity
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(n)
                WHERE chunk IS NOT NULL
                WITH n, max_similarity,
                     collect(DISTINCT {
                         id: chunk.id,
                         content: chunk.content,
                         chunk_index: chunk.chunk_index,
                         page_number: chunk.page_number
                     }) as source_chunks

                // Get relationships
                OPTIONAL MATCH (n)-[r]-(related)
                WHERE related IS NOT NULL
                WITH n, max_similarity, source_chunks,
                     collect(DISTINCT {
                         relation: type(r),
                         node: related.name,
                         direction: CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END
                     }) as relationships

                RETURN n.name as name,
                       n.label as type,
                       n.id as id,
                       n.description as description,
                       max_similarity as similarity,
                       source_chunks,
                       relationships
                ORDER BY max_similarity DESC
                LIMIT $limit
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

                # Format the results into readable context
                context_parts = []
                for record in records:
                    name = record["name"]
                    entity_type = record["type"]
                    entity_id = record["id"]
                    description = record["description"]
                    similarity = record["similarity"]
                    source_chunks = record["source_chunks"]
                    relationships = record["relationships"]

                    # Build entity description
                    entity_desc = f"\n**{name}** ({entity_type}) [similarity: {similarity:.3f}]"
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
                        entity_desc += "\n  - Related to:"
                        for rel in relationships[:5]:  # Limit relationships shown
                            if rel['node']:
                                direction = "->" if rel['direction'] == 'outgoing' else "<-"
                                entity_desc += f"\n    - {direction} {rel['relation']}: {rel['node']}"

                    context_parts.append(entity_desc)

                return "\n".join(context_parts)

        except Exception as e:
            return f"Error performing vector similarity search: {str(e)}"

    def entity_graph_search(self, entity_name: str, depth: int = 2) -> str:
        """
        Search the knowledge graph starting from a specific entity using vector similarity.

        Uses embeddings for semantic matching, then traverses relationships.

        Args:
            entity_name: Name of the entity to start from
            depth: Number of relationship hops to traverse (1 or 2)

        Returns:
            Formatted context with entity and its neighborhood
        """
        if not self.embedding_model:
            return f"Entity search not available: embedding model not loaded for '{entity_name}'"

        try:
            # Generate embedding for the entity name
            query_embedding = self.generate_embedding(entity_name)

            with self.driver.session(database=self.database) as session:
                # Query to find entity using vector similarity and traverse relationships
                cypher_query = """
                MATCH (e)
                WHERE e.embeddings IS NOT NULL
                WITH e,
                     reduce(dot = 0.0, i IN range(0, size(e.embeddings)-1) |
                          dot + e.embeddings[i] * $query_vector[i]) /
                          (sqrt(reduce(sum = 0.0, x IN e.embeddings | sum + x * x)) *
                           sqrt(reduce(sum = 0.0, x IN $query_vector | sum + x * x))) AS max_similarity
                WHERE max_similarity >= 0.5
                ORDER BY max_similarity DESC
                LIMIT 1

                // Get level 1 relationships and their source chunks
                OPTIONAL MATCH (e)-[r1]-(related1)
                WHERE related1 IS NOT NULL
                WITH e, max_similarity,
                     collect(DISTINCT {
                         relation: type(r1),
                         target: related1.name,
                         target_id: related1.id,
                         direction: CASE WHEN startNode(r1) = e THEN 'outgoing' ELSE 'incoming' END
                     }) as level1_rels,
                     collect(DISTINCT related1) as level1_entities

                // Get source chunks for level 1 entities
                UNWIND CASE WHEN size(level1_entities) > 0 THEN level1_entities ELSE [null] END as l1_entity
                OPTIONAL MATCH (chunk1:Chunk)-[:SOURCE]->(l1_entity)
                WHERE l1_entity IS NOT NULL AND chunk1 IS NOT NULL
                WITH e, max_similarity, level1_rels, level1_entities,
                     collect(DISTINCT {
                         entity_name: l1_entity.name,
                         entity_id: l1_entity.id,
                         chunk_id: chunk1.id,
                         content: chunk1.content,
                         chunk_index: chunk1.chunk_index,
                         page_number: chunk1.page_number
                     }) as level1_chunks

                // Get level 2 relationships if depth >= 2
                OPTIONAL MATCH (e)-[r1]-(via)-[r2]-(related2)
                WHERE $depth >= 2 AND via <> e AND related2 <> e AND related2 IS NOT NULL
                WITH e, max_similarity, level1_rels, level1_chunks,
                     collect(DISTINCT {
                         relation: type(r2),
                         target: related2.name,
                         target_id: related2.id,
                         via: via.name
                     })[..10] as level2_rels,
                     collect(DISTINCT related2) as level2_entities

                // Get source chunks for level 2 entities
                UNWIND CASE WHEN size(level2_entities) > 0 THEN level2_entities ELSE [null] END as l2_entity
                OPTIONAL MATCH (chunk2:Chunk)-[:SOURCE]->(l2_entity)
                WHERE l2_entity IS NOT NULL AND chunk2 IS NOT NULL
                WITH e, max_similarity, level1_rels, level1_chunks, level2_rels,
                     collect(DISTINCT {
                         entity_name: l2_entity.name,
                         entity_id: l2_entity.id,
                         chunk_id: chunk2.id,
                         content: chunk2.content,
                         chunk_index: chunk2.chunk_index,
                         page_number: chunk2.page_number
                     }) as level2_chunks

                // Get source chunks linked to the main entity
                OPTIONAL MATCH (chunk:Chunk)-[:SOURCE]->(e)
                WHERE chunk IS NOT NULL
                WITH e, max_similarity, level1_rels, level1_chunks, level2_rels, level2_chunks,
                     collect(DISTINCT {
                         id: chunk.id,
                         content: chunk.content,
                         chunk_index: chunk.chunk_index,
                         page_number: chunk.page_number
                     }) as source_chunks

                RETURN e.name as name,
                       e.label as type,
                       e.id as id,
                       e.description as description,
                       max_similarity as similarity,
                       level1_rels,
                       level2_rels,
                       source_chunks,
                       level1_chunks,
                       level2_chunks
                """

                result = session.run(
                    cypher_query,
                    query_vector=query_embedding,
                    depth=depth
                )

                record = result.single()

                if not record:
                    return f"Entity '{entity_name}' not found in knowledge graph (searched with similarity threshold 0.5)"

                # Format the entity and its neighborhood
                name = record["name"]
                entity_type = record["type"]
                entity_id = record["id"]
                description = record["description"]
                similarity = record["similarity"]
                level1_rels = record["level1_rels"]
                level2_rels = record["level2_rels"] if depth >= 2 else []
                source_chunks = record["source_chunks"]
                level1_chunks = record["level1_chunks"]
                level2_chunks = record["level2_chunks"] if depth >= 2 else []

                context = f"\n## Entity: {name} [similarity: {similarity:.3f}]"
                if entity_type:
                    context += f" ({entity_type})"
                if entity_id and entity_id != name:
                    context += f"\n- ID: {entity_id}"
                if description:
                    context += f"\n- Description: {description}"

                # Note if this is a fuzzy match
                if similarity < 0.9:
                    context += f"\n- Note: Found via semantic similarity (query: '{entity_name}')"

                # Add source chunks for main entity
                if source_chunks and any(c.get('id') for c in source_chunks):
                    context += "\n\n### Source Chunks (Main Entity):"
                    for chunk in source_chunks[:5]:  # Limit to 5 chunks
                        if chunk.get('id'):
                            context += f"\n  - Chunk ID: {chunk['id']}"
                            if chunk.get('chunk_index') is not None:
                                context += f" (index: {chunk['chunk_index']})"
                            if chunk.get('page_number') is not None:
                                context += f", Page: {chunk['page_number']}"
                            if chunk.get('content'):
                                context += f"\n    Content: {chunk['content']}"

                # Add level 1 relationships
                if level1_rels and any(r['relation'] for r in level1_rels):
                    context += "\n\n### Direct Connections (Level 1):"
                    for rel in level1_rels[:10]:  # Limit to 10
                        if rel['relation'] and rel['target']:
                            direction = "→" if rel['direction'] == 'outgoing' else "←"
                            context += f"\n  - {direction} {rel['relation']}: {rel['target']}"

                # Add source chunks for level 1 entities
                if level1_chunks:
                    # Group chunks by entity
                    chunks_by_entity = {}
                    for chunk in level1_chunks:
                        if chunk.get('chunk_id'):  # Only include chunks that exist
                            entity_name = chunk.get('entity_name', 'Unknown')
                            if entity_name not in chunks_by_entity:
                                chunks_by_entity[entity_name] = []
                            chunks_by_entity[entity_name].append(chunk)

                    if chunks_by_entity:
                        context += "\n\n### Source Chunks from Level 1 Entities:"
                        for entity_name, chunks in list(chunks_by_entity.items())[:5]:  # Limit to 5 entities
                            context += f"\n  **From: {entity_name}**"
                            for chunk in chunks[:3]:  # Limit to 3 chunks per entity
                                context += f"\n    - Chunk ID: {chunk['chunk_id']}"
                                if chunk.get('chunk_index') is not None:
                                    context += f" (index: {chunk['chunk_index']})"
                                if chunk.get('page_number') is not None:
                                    context += f", Page: {chunk['page_number']}"
                                if chunk.get('content'):
                                    context += f"\n      {chunk['content']}"

                # Add level 2 relationships if depth is 2
                if depth >= 2 and level2_rels and any(r['relation'] for r in level2_rels):
                    context += "\n\n### Indirect Connections (Level 2):"
                    for rel in level2_rels[:10]:  # Limit to 10
                        if rel['relation'] and rel['target'] and rel['via']:
                            context += f"\n  - via {rel['via']} → {rel['relation']}: {rel['target']}"

                # Add source chunks for level 2 entities
                if depth >= 2 and level2_chunks:
                    # Group chunks by entity
                    chunks_by_entity_l2 = {}
                    for chunk in level2_chunks:
                        if chunk.get('chunk_id'):  # Only include chunks that exist
                            entity_name = chunk.get('entity_name', 'Unknown')
                            if entity_name not in chunks_by_entity_l2:
                                chunks_by_entity_l2[entity_name] = []
                            chunks_by_entity_l2[entity_name].append(chunk)

                    if chunks_by_entity_l2:
                        context += "\n\n### Source Chunks from Level 2 Entities:"
                        for entity_name, chunks in list(chunks_by_entity_l2.items())[:3]:  # Limit to 3 entities
                            context += f"\n  **From: {entity_name}**"
                            for chunk in chunks[:2]:  # Limit to 2 chunks per entity
                                context += f"\n    - Chunk ID: {chunk['chunk_id']}"
                                if chunk.get('chunk_index') is not None:
                                    context += f" (index: {chunk['chunk_index']})"
                                if chunk.get('page_number') is not None:
                                    context += f", Page: {chunk['page_number']}"
                                if chunk.get('content'):
                                    context += f"\n      {chunk['content']}"

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


# =============================================================================
# Tool Definition
# =============================================================================

@tool
def neo4j_retrieval_tool(query: str) -> str:
    """
    Search the Neo4j knowledge graph for information relevant to the query.

    Use this tool when you need to find facts, entities, or relationships
    from the knowledge base to answer user questions using text-based search.

    Args:
        query: The search query to find relevant information

    Returns:
        Retrieved context from the knowledge graph
    """
    retriever = get_retriever()
    return retriever.search_knowledge_graph(query)


@tool
def neo4j_vector_search_tool(query: str) -> str:
    """
    Search the Neo4j knowledge graph using semantic vector similarity.

    Use this tool when you need to find semantically similar entities or concepts
    in the knowledge base. This is more powerful than text search as it understands
    meaning and context, not just keyword matches.

    Args:
        query: The search query to find semantically similar information

    Returns:
        Retrieved context from the knowledge graph with similarity scores
    """
    retriever = get_retriever()
    return retriever.vector_similarity_search(query, limit=5, similarity_threshold=0.5)


@tool
def neo4j_multi_query_search_tool(queries: str) -> str:
    """
    Search the Neo4j knowledge graph with multiple queries using vector similarity search.

    This tool processes multiple sub-questions efficiently using semantic vector search
    for each query. Provide queries separated by newlines or semicolons.

    This is ideal for:
    - Comparison queries (search for each entity semantically)
    - Complex questions broken into parts
    - Multi-aspect information gathering with semantic understanding

    Args:
        queries: Multiple search queries separated by newlines or semicolons

    Returns:
        Combined retrieved context from the knowledge graph for all queries using vector search
    """
    retriever = get_retriever()

    # Parse queries - split by newline or semicolon
    query_list = []
    for q in queries.replace(';', '\n').split('\n'):
        q = q.strip()
        # Remove numbering like "1. ", "2) ", etc.
        q = q.lstrip('0123456789.-)• \t')
        if q:
            query_list.append(q)

    if not query_list:
        return "No valid queries provided"

    print(f"\n[Multi-Query Vector Search] Processing {len(query_list)} queries with semantic search:")
    for i, q in enumerate(query_list, 1):
        print(f"  {i}. {q}")

    # Retrieve information for each query using ONLY vector search
    results = []
    successful_queries = 0

    for i, query in enumerate(query_list, 1):
        print(f"\n[Multi-Query Vector Search] Query {i}/{len(query_list)}: {query[:50]}...")

        # Use vector search with lowered threshold for broader semantic matching
        result = retriever.vector_similarity_search(query, limit=5, similarity_threshold=0.5)

        if result and "No similar entities found" not in result:
            results.append(f"\n### Results for: {query}\n{result}")
            successful_queries += 1
            print(f"  ✓ Found {result.count('**')} entities with semantic similarity")
        else:
            # Document that no results were found for this query
            results.append(f"\n### Results for: {query}\nNo semantically similar entities found (threshold: 0.5)")
            print(f"  ✗ No results above similarity threshold")

    print(f"\n[Multi-Query Vector Search] Retrieved results for {successful_queries}/{len(query_list)} queries\n")

    if successful_queries == 0:
        return f"No semantically similar entities found in knowledge graph for any of the {len(query_list)} queries (similarity threshold: 0.5)"

    return "\n".join(results)


@tool
def neo4j_entity_graph_search_tool(entities: str, depth: int = 2) -> str:
    """
    Search the knowledge graph starting from specific entities using vector similarity.

    This tool uses semantic similarity (via embeddings) to find entities
    in the graph, then explores their relationships 1-2 levels deep. This makes it robust to
    variations in entity naming - it can find semantically similar entities even if the exact
    name doesn't match.

    This is ideal for:
    - Finding all information related to a specific entity (even with fuzzy name matching)
    - Understanding relationships between entities
    - Exploring the neighborhood of semantically similar entities
    - Getting comprehensive context about entities and their connections

    Args:
        entities: Entity name(s) to search for. Can be a single entity or comma-separated list
        depth: Number of relationship hops (1 or 2). Default is 2.

    Returns:
        Graph context showing the entity and its connected nodes up to the specified depth,
        with similarity scores indicating match quality
    """
    retriever = get_retriever()

    # Parse entities - split by comma
    entity_list = []
    for entity in entities.split(','):
        entity = entity.strip()
        if entity:
            entity_list.append(entity)

    if not entity_list:
        return "No valid entities provided"

    print(f"\n[Entity Graph Search - Vector Similarity] Exploring {len(entity_list)} entities (depth={depth}):")
    for i, e in enumerate(entity_list, 1):
        print(f"  {i}. {e}")

    # Search for each entity using vector similarity
    results = []
    successful_searches = 0

    for i, entity in enumerate(entity_list, 1):
        print(f"\n[Entity Graph Search] Entity {i}/{len(entity_list)}: {entity}")

        result = retriever.entity_graph_search(entity, depth=depth)

        if result and "not found" not in result.lower():
            results.append(result)
            successful_searches += 1
            # Count relationships found and extract similarity score
            level1_count = result.count("Level 1")
            level2_count = result.count("Level 2")
            # Extract similarity score from result
            similarity_match = result.find("[similarity:")
            if similarity_match != -1:
                sim_str = result[similarity_match:similarity_match+30]
                print(f"  ✓ Found via vector similarity with {level1_count} direct connections" +
                      (f" and {level2_count} indirect connections" if depth >= 2 else ""))
            else:
                print(f"  ✓ Found entity with {level1_count} direct connections" +
                      (f" and {level2_count} indirect connections" if depth >= 2 else ""))
        else:
            results.append(f"\n## Entity: {entity}\n- Status: Not found in knowledge graph (similarity threshold: 0.5)")
            print(f"  ✗ No semantically similar entity found")

    print(f"\n[Entity Graph Search] Found {successful_searches}/{len(entity_list)} entities via vector similarity\n")

    if successful_searches == 0:
        return f"None of the {len(entity_list)} entities were found in the knowledge graph"

    return "\n\n---\n".join(results)


@tool
def neo4j_hybrid_search_tool(query: str, limit: int = 5) -> str:
    """
    Search the Neo4j knowledge graph using advanced hybrid search with Reciprocal Rank Fusion.

    This is the RECOMMENDED tool for most queries. It combines FOUR powerful retrieval strategies:

    1. **Vector Similarity Search on Entities** - Semantic matching on entities using embeddings
    2. **Direct Chunk Text Search** - Keyword search on actual document text (Chunk nodes)
    3. **Text-based Keyword Search on Entities** - Lexical matching on entity names/descriptions
    4. **Entity Graph Search** - Structural matching with entity neighborhoods and relationships

    Results from all strategies are intelligently fused using Reciprocal Rank Fusion (RRF),
    which creates an optimal ranking that leverages the strengths of each approach. This provides:
    - Better recall (finds relevant results from both entities AND document text)
    - Better precision (ranks most relevant results first)
    - Complete context (actual text chunks with page numbers and entity information)
    - Robustness to query variations
    - Rich context with source chunks, relationships, and similarity scores

    Each result can be:
    - **Entity**: Includes name, official name, description, type, related entities, and SOURCE CHUNKS with actual text
    - **Chunk**: Direct document text with page numbers, source file, and linked entities

    All results include:
    - RRF fusion score (higher = more relevant)
    - Original search score
    - Which strategies found this result (vector, chunk_text, text, entity_graph)
    - Source chunks with ACTUAL TEXT CONTENT from documents

    Use this tool for:
    - Factual lookups ("What is X?")
    - Finding specific information from documents
    - Relationship queries ("How is X related to Y?")
    - Comparisons ("Compare X and Y")
    - Explanations ("Explain how X works")
    - Exploratory queries ("Find information about X")
    - Complex multi-aspect questions

    Args:
        query: The search query to find relevant information
        limit: Maximum number of results to return (default: 5, recommended: 3-7)

    Returns:
        Formatted context with fused and ranked results from the knowledge graph,
        including entities with source chunks (actual text), chunk text, relationships,
        and RRF scores. Results include page numbers and source file information.

    Example:
        "What is 3M's market value?" -> Returns:
        - Entity: FinancialMetric with official name and description
        - Source Chunks: Actual text from 10-K filing with page numbers
        - Related Entities: Company, TimePeriod, etc.
    """
    retriever = get_retriever()

    # Use hybrid search with all strategies enabled
    result = retriever.hybrid_search(
        query=query,
        limit=limit,
        enable_vector=True,
        enable_text=True,
        enable_entity=True,
        enable_chunk=True
    )

    return result


# =============================================================================
# Graph Nodes
# =============================================================================

def preprocess_query_node(state: ChatState) -> ChatState:
    """
    Preprocessing node that detects intent and decomposes query into sub-questions.

    Args:
        state: Current chat state

    Returns:
        Updated state with intent, sub-questions, and original question
    """
    # Get the last user message
    messages = state["messages"]
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        # No user message found, skip preprocessing
        return {
            "intent": "unknown",
            "sub_questions": [],
            "original_question": ""
        }

    # Initialize LLM for preprocessing
    base_url = os.getenv("OPENAI_BASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")

    # If using custom base_url without api_key, use "EMPTY" as recommended by LangChain
    # See: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
    if base_url and not api_key:
        api_key = "EMPTY"

    llm_kwargs = {
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "temperature": 0.1,  # Low temperature for more consistent analysis
        "api_key": api_key
    }

    # Add base_url if provided
    if base_url:
        llm_kwargs["base_url"] = base_url

        # Add headers to help bypass Cloudflare protection
        llm_kwargs["default_headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }

    llm = ChatOpenAI(**llm_kwargs)

    # Intent detection prompt
    intent_prompt = f"""Analyze the following user question and classify its intent into ONE of these categories:
- factual_lookup: Looking for specific facts or information
- comparison: Comparing multiple entities or concepts
- explanation: Asking for explanation or understanding of a concept
- procedure: Asking how to do something
- troubleshooting: Trying to solve a problem
- general_conversation: General chat or greeting

Question: {last_user_message}

Respond with ONLY the intent category name (e.g., "factual_lookup").
"""

    intent_response = llm.invoke([HumanMessage(content=intent_prompt)])
    detected_intent = intent_response.content.strip()

    # Entity extraction prompt - focused on entities that can help answer the question
    entity_prompt = f"""Identify the TOP 3 MOST IMPORTANT entities and concepts that would be relevant to finding information to answer this question.

Question: {last_user_message}

Extract EXACTLY 3 entities from these categories:
1. **Main Entities**: The primary subjects, objects, or concepts mentioned in the question
   - Named entities (organizations, products, standards, technologies, methods)
   - Technical terms and domain-specific concepts

2. **Related Entities**: Entities that might exist in a knowledge graph that could help answer the question
   - Related concepts, methods, or processes
   - Standards, specifications, or documents that might contain relevant information
   - Categories or types that the main entities belong to

3. **Contextual Entities**: Background concepts that provide necessary context
   - Domain areas (e.g., "materials testing", "software engineering")
   - General categories or classifications

Focus on entities that likely exist as nodes in a knowledge graph and could provide useful information through their relationships.

IMPORTANT: Return EXACTLY 3 entities, prioritized by importance.
Return ONLY a comma-separated list of 3 entities (e.g., "temperature cycling, thermal shock, reliability testing").
If fewer than 3 clear entities exist, return only those found.
If no clear entities are found, return "NONE".

Entities:"""

    entity_response = llm.invoke([HumanMessage(content=entity_prompt)])
    entity_text = entity_response.content.strip()

    # Parse entities from the response
    entities = []
    if entity_text and entity_text.upper() != "NONE":
        # Split by comma and clean up
        for entity in entity_text.split(','):
            entity = entity.strip()
            if entity:
                entities.append(entity)

    print(f"\n[Preprocessing] Intent: {detected_intent}")
    print(f"[Preprocessing] Original: {last_user_message}")
    print(f"[Preprocessing] Entities ({len(entities)}): {', '.join(entities) if entities else 'None'}")
    print()

    return {
        "intent": detected_intent,
        "original_question": last_user_message,
        "entities": entities
    }


# =============================================================================
# ReAct Agent Setup
# =============================================================================

# Initialize LLM for the agent
_llm = None
_react_agent = None

def get_react_agent():
    """Get or create the ReAct agent instance."""
    global _llm, _react_agent

    if _react_agent is None:
        # Initialize ChatOpenAI
        base_url = os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("OPENAI_API_KEY")

        # If using custom base_url without api_key, use "EMPTY" as recommended by LangChain
        # See: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
        if base_url and not api_key:
            api_key = "EMPTY"

        llm_kwargs = {
            "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
            "api_key": api_key
        }

        # Add base_url if provided
        if base_url:
            llm_kwargs["base_url"] = base_url

            # Add headers to help bypass Cloudflare protection
            llm_kwargs["default_headers"] = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9"
            }

        _llm = ChatOpenAI(**llm_kwargs)

        # Define tools for the agent
        # Using hybrid search tool that combines vector, text, and entity search with RRF fusion
        tools = [
            # neo4j_hybrid_search_tool,  # Comprehensive hybrid search with RRF ranking
            neo4j_vector_search_tool,
            neo4j_entity_graph_search_tool,
            # neo4j_retrieval_tool,

        ]

        # Create ReAct agent
        _react_agent = create_react_agent(_llm, tools)

        print("[ReAct Agent] Initialized with Neo4j Hybrid Search tool (RRF fusion of vector, text, entity strategies)")

    return _react_agent


def agent_node(state: ChatState) -> ChatState:
    """
    Agent node that wraps the ReAct agent with preprocessing context injection.

    This node:
    1. Injects preprocessing context (intent and sub-questions) into messages
    2. Invokes the ReAct agent which handles tool calling and reasoning
    3. Returns the agent's response

    Args:
        state: Current chat state with preprocessing results

    Returns:
        Updated state with agent's response
    """
    # Get the ReAct agent
    agent = get_react_agent()

    # Prepare messages with preprocessing context
    messages = list(state["messages"])
    intent = state.get("intent", "")
    entities = state.get("entities", [])

    # Check if this is the first agent call (no AI messages yet)
    has_ai_response = any(isinstance(msg, AIMessage) for msg in messages)

    if entities and intent and not has_ai_response:
        # Create a system context message with preprocessing results
        entities_formatted = ', '.join(entities) if entities else 'None'

        context_message = HumanMessage(content=f"""[System Context - Query Preprocessing Results]

Intent: {intent}
Extracted Entities: {entities_formatted}

IMPORTANT INSTRUCTIONS:
Use the tool to retrieve information from the knowledge graph to answer the user's question.

The tool combines multiple strategies: vector similarity, text search, entity graph search, and chunk text search.
Results are fused using Reciprocal Rank Fusion (RRF) for optimal ranking.

CRITICAL RULES TO PREVENT RECURSION:
1. **Maximum 3 tool calls total** - Use at most 3 searches to gather information
2. **No repeated queries** - Do not call the tool with the exact same query multiple times
3. **Answer with retrieved information** - After tool calls, synthesize an answer from what you found
4. **Stop when sufficient** - If you have enough information after 1-2 tool calls, provide the answer immediately
5. **No endless searching** - If initial results don't contain the answer, say so and provide the best answer you can

Query Strategy by Intent:
- factual_lookup: 1 focused query → ANSWER immediately
- comparison: 1-2 queries (one per entity) → COMPARE → ANSWER
- explanation: 1 query on main concept → ANSWER with what you find
- procedure: 1 query → ANSWER
- troubleshooting: 1-2 queries max → ANSWER

Expected Flow:
1. Call tool once or twice (max 3 times)
2. Review retrieved information
3. Formulate complete answer based on what was found
4. Provide final answer to user (DO NOT call tool again)

DO NOT:
- Call tool more than 3 times
- Repeat the same query with minor variations
- Keep searching if you didn't find information
- Say "let me search again" - just work with what you retrieved

Now retrieve information and provide your final answer.""")

        # Insert context after the user message
        messages.insert(1, context_message)

        print(f"\n[Agent Node] Injected preprocessing context:")
        print(f"  Intent: {intent}")
        print(f"  Entities: {len(entities)} - {entities_formatted}")

    # Invoke the ReAct agent with the prepared messages
    print("\n[Agent Node] Invoking ReAct agent...")
    result = agent.invoke({"messages": messages})

    # The agent returns a state dict with 'messages' key
    return {"messages": result["messages"]}


# =============================================================================
# Graph Construction
# =============================================================================

def build_graph():
    """
    Build the RAG chat graph with Neo4j retrieval and query preprocessing using ReAct agent.

    Graph Flow:
    1. preprocess_query -> Detects intent and extracts relevant entities
    2. agent_node -> Invokes ReAct agent which handles:
       - Tool selection and calling (entity graph search, vector search)
       - Reasoning steps
       - Multiple tool iterations
       - Final answer synthesis
    3. END

    The ReAct agent internally manages the tool calling loop, prioritizing entity-based
    graph traversal for rich contextual understanding.

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(ChatState)

    # Add nodes
    workflow.add_node("preprocess_query", preprocess_query_node)
    workflow.add_node("agent", agent_node)

    # Set entry point to preprocessing
    workflow.set_entry_point("preprocess_query")

    # Add edge from preprocessing to agent
    workflow.add_edge("preprocess_query", "agent")

    # Add edge from agent to END
    # The ReAct agent handles all tool calling internally
    workflow.add_edge("agent", END)

    # Compile the graph
    print("\n[Graph] Building RAG graph with ReAct agent...")
    print("[Graph] Flow: preprocess_query → agent (ReAct) → END")

    return workflow.compile()


# =============================================================================
# Main Export
# =============================================================================

# Create the compiled graph for LangGraph server
graph = build_graph()


if __name__ == "__main__":
    """Test the graph locally."""
    print("Testing RAG Chat Graph with Query Preprocessing...")
    print("=" * 60)

    # Test with a complex question that should be decomposed
    test_question = "What are temperature cycling tests and how do they differ from thermal shock tests?"

    # Create test state
    test_state = {
        "messages": [
            HumanMessage(content=test_question)
        ],
        "retrieved_context": "",
        "intent": "",
        "original_question": "",
        "entities": []
    }

    # Run the graph
    print(f"\nUser: {test_question}")
    result = graph.invoke(test_state)

    # Print preprocessing results
    print("\n" + "=" * 60)
    print("PREPROCESSING RESULTS:")
    print(f"Intent: {result.get('intent', 'N/A')}")
    print(f"Original Question: {result.get('original_question', 'N/A')}")
    entities = result.get('entities', [])
    print(f"Extracted Entities ({len(entities)}): {', '.join(entities) if entities else 'None'}")
    print("=" * 60)

    # Print the conversation
    print("\nCONVERSATION:")
    for msg in result["messages"]:
        if isinstance(msg, HumanMessage):
            print(f"\nUser: {msg.content}")
        elif isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"\nAI: [Calling tools: {[tc['name'] for tc in msg.tool_calls]}]")
            else:
                print(f"\nAI: {msg.content}")
        elif isinstance(msg, ToolMessage):
            print(f"\nTool Result: {msg.content[:200]}...")

    print("\n" + "=" * 60)
    print("Test complete!")
