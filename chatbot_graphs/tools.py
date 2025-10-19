"""
LangChain tool definitions for Neo4j knowledge graph retrieval.
"""
from langchain_core.tools import tool
from .retriever import get_retriever



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
def neo4j_entity_graph_search_tool(entities: list[str], depth: int = 1) -> str:
    """
    Search for relationships BETWEEN multiple entities in the knowledge graph.

    This tool finds entities from the input list using semantic similarity,
    then discovers relationships that connect these entities to each other.
    It extracts relationship properties and source chunks for the entities involved.

    This is the RECOMMENDED tool when you need to:
    - Find relationships between specific entities (e.g., Company and FinancialStatement)
    - Extract relationship properties (e.g., financial metrics on REPORTED_FINANCIALS edges)
    - Get source text evidence from both entities in a relationship
    - Understand how multiple entities are connected in the knowledge graph

    Example use cases:
    - "Find relationship between 3M Company and its financial statements"
      → entities: ["3M Company", "FinancialStatement"]
    - "Show connections between Company A and Product X"
      → entities: ["Company A", "Product X"]

    Args:
        entities: List of entity names to search for (e.g., ["3M", "Corning", "Product"])
        depth: Unused (kept for backward compatibility). Always searches for direct relationships.

    Returns:
        Formatted context showing:
        - All found entities with their types and descriptions
        - Relationships BETWEEN these entities with properties
        - Source chunks from BOTH entities involved in each relationship

    Note: If only 1 entity is provided, shows that entity's information.
          If 2+ entities provided, finds relationships between them.
    """
    retriever = get_retriever()

    # Handle both list and string inputs for backward compatibility
    if isinstance(entities, str):
        # If string is passed (e.g., from older API), split by comma
        entity_list = [e.strip() for e in entities.split(',') if e.strip()]
    else:
        # Already a list
        entity_list = [str(e).strip() for e in entities if str(e).strip()]

    if not entity_list:
        return "No valid entities provided"

    print(f"\n[Entity Graph Search] Finding {len(entity_list)} entities and relationships between them:")
    for i, e in enumerate(entity_list, 1):
        print(f"  {i}. {e}")

    # Use the updated entity_graph_search method that finds relationships BETWEEN entities
    # Pass as comma-separated string since the retriever method expects that
    entities_str = ", ".join(entity_list)
    result = retriever.entity_graph_search(entities_str, depth=depth)

    return result


@tool
def neo4j_typed_vector_search_tool(
    query: str,
    entity_types: list[str] = None,
    relationship_types: list[str] = None,
    limit: int = 5
) -> str:
    """
    Search the Neo4j knowledge graph using type-filtered semantic vector similarity (SPG-aware).

    This tool performs vector search with filtering by entity types and/or relationship types,
    leveraging the Semantic Property Graph (SPG) structure for precise, type-specific retrieval.

    **When to use this tool:**
    - When you need entities of SPECIFIC TYPES (e.g., only Company, only Executive)
    - When you need relationships of SPECIFIC TYPES (e.g., only REPORTED_FINANCIALS, only OWNS)
    - When you want to narrow down search results to specific categories
    - When exploring SPG schema-defined entity and relationship types

    **Entity Types in SPG Schema:**
    - Company, Executive, Product, BusinessSegment, GeographicRegion
    - FinancialStatement, FinancialEvent, RegulatoryFiling, MarketData
    - Industry, ExecutiveRole, ProductCategory, RegionType, EventCategory

    **Relationship Types in SPG Schema:**
    - REPORTED_FINANCIALS (with financial metric properties: revenue, profit, assets, etc.)
    - OWNS, EMPLOYS, PRODUCES, OPERATES_IN, HAS_SEGMENT
    - FILED, INVOLVED_IN, HAS_MARKET_DATA
    - WORKS_FOR, LEADS, BELONGS_TO, CONTAINS

    **Examples:**

    1. Find companies related to earnings:
       query: "earnings report Q4 2023"
       entity_types: ["Company", "FinancialStatement"]
       → Returns only Company and FinancialStatement entities

    2. Find executive compensation info:
       query: "executive compensation salary"
       entity_types: ["Executive"]
       relationship_types: ["EMPLOYS"]
       → Returns Executives with EMPLOYS relationship properties (salary, hireDate)

    3. Find financial reporting relationships:
       query: "revenue profit financial data"
       relationship_types: ["REPORTED_FINANCIALS"]
       → Returns entities with REPORTED_FINANCIALS edges showing all financial metrics

    4. Find ownership structures:
       query: "subsidiary acquisition ownership"
       entity_types: ["Company"]
       relationship_types: ["OWNS"]
       → Returns Companies with OWNS relationships (ownershipPercent, acquiredDate)

    Args:
        query: Search query text for semantic matching
        entity_types: List of entity type labels to filter by (default: None = all types)
        relationship_types: List of relationship type names to filter by (default: None = all types)
        limit: Maximum number of entity results to return (default: 5)

    Returns:
        Formatted context with:
        - Type-filtered entities with similarity scores
        - Filtered relationships with ALL SPG edge properties
        - Source chunks with actual document text
        - Entity and relationship type labels

    Note: All relationship properties are returned for SPG property-rich edges.
          This includes financial metrics, temporal data, and contextual information.
    """
    retriever = get_retriever()

    print(f"\n[Typed Vector Search] Query: {query}")
    if entity_types:
        print(f"  Entity Types Filter: {entity_types}")
    if relationship_types:
        print(f"  Relationship Types Filter: {relationship_types}")

    result = retriever.typed_vector_search(
        query=query,
        entity_types=entity_types,
        relationship_types=relationship_types,
        limit=limit,
        similarity_threshold=0.5
    )

    return result


@tool
def neo4j_semantic_path_search_tool(
    start_entity: str,
    end_entity: str,
    max_hops: int = 3,
    path_relationship_types: list[str] = None
) -> str:
    """
    Find semantic paths between two entities with property-rich relationships (SPG-aware).

    This tool discovers meaningful connections between entities by finding paths through
    the knowledge graph, extracting ALL relationship properties along each path.
    Leverages Semantic Property Graph (SPG) structure for multi-hop traversal.

    **When to use this tool:**
    - When user asks "how is X related to Y" or "find connection between X and Y"
    - To discover indirect relationships through intermediate entities
    - To trace chains of relationships (e.g., Company → FinancialStatement → RegulatoryFiling)
    - To analyze paths with specific relationship types
    - To understand multi-hop dependencies in financial reporting

    **Path Scoring:**
    Paths are ranked by:
    - Semantic similarity of start/end entities to query
    - Path length (shorter paths rank higher)
    - Property richness (paths with more SPG properties rank higher)

    **Examples:**

    1. Find how a company connects to its financial data:
       start_entity: "3M Company"
       end_entity: "Q4 2023 revenue"
       max_hops: 3
       → Returns paths like: 3M -[REPORTED_FINANCIALS{revenue:$X}]→ FinancialStatement

    2. Trace executive to financial statement:
       start_entity: "CEO"
       end_entity: "Income Statement"
       max_hops: 2
       → Returns paths like: Executive -[WORKS_FOR]→ Company -[REPORTED_FINANCIALS]→ FinancialStatement

    3. Find regulatory filing chain:
       start_entity: "Apple Inc"
       end_entity: "10-K filing"
       path_relationship_types: ["FILED", "PART_OF"]
       → Returns paths using only FILED and PART_OF relationships

    4. Discover ownership structure:
       start_entity: "Parent company"
       end_entity: "Subsidiary"
       path_relationship_types: ["OWNS"]
       max_hops: 2
       → Returns ownership chains with ownershipPercent, acquiredDate properties

    **Path Output Includes:**
    - Visual path representation with all nodes and relationship types
    - Similarity scores for start and end entity matches
    - Path length and overall path score
    - ALL SPG relationship properties along the path (revenue, profit, dates, etc.)
    - Entity type labels at each node in the path

    Args:
        start_entity: Name or description of starting entity (will use vector similarity to find)
        end_entity: Name or description of ending entity (will use vector similarity to find)
        max_hops: Maximum path length to search (1-5 recommended, default: 3)
        path_relationship_types: Filter paths to only use these relationship types (default: None = all types)

    Returns:
        Formatted context with:
        - Multiple paths ranked by relevance score
        - Path visualization showing all nodes and edges
        - Complete SPG relationship properties for each edge in the path
        - Semantic similarity scores and path metrics

    Note: This tool uses vector similarity to find entities matching the start/end descriptions,
          then finds all paths between them. Great for exploratory "how are these connected?" queries.
    """
    retriever = get_retriever()

    print(f"\n[Semantic Path Search] Finding paths: '{start_entity}' → '{end_entity}'")
    print(f"  Max hops: {max_hops}")
    if path_relationship_types:
        print(f"  Relationship type filter: {path_relationship_types}")

    result = retriever.semantic_path_search(
        start_entity=start_entity,
        end_entity=end_entity,
        max_hops=max_hops,
        path_relationship_types=path_relationship_types,
        return_all_paths=True,
        limit_paths=10
    )

    return result


@tool
def neo4j_question_subgraph_tool(
    question: str,
    max_hops: int = 2,
    property_filters: dict = None
) -> str:
    """
    Retrieve the optimal subgraph for answering a specific question.

    This is the MOST INTELLIGENT tool for complex questions. It uses a 5-stage approach:
    1. **Entity Identification**: Find seed entities from the question using vector similarity
    2. **Type Inference**: Automatically infer required entity/relationship types from keywords
    3. **Subgraph Expansion**: Expand from seeds with relevance-based k-hop traversal
    4. **Property Highlighting**: Highlight properties mentioned in the question
    5. **Context Enrichment**: Include source chunks for evidence

    **When to use this tool:**
    - Complex questions requiring multiple entities and relationships
    - Questions with temporal constraints (e.g., "Q4 2023", "2022")
    - Questions requiring reasoning across multiple hops
    - When you need a complete subgraph for comprehensive answers

    **Automatic Type Inference:**
    The tool automatically detects required relationship types from keywords:
    - "revenue", "profit", "earnings" → REPORTED_FINANCIALS
    - "owns", "subsidiary", "acquisition" → OWNS
    - "executive", "CEO", "employee" → EMPLOYS
    - "filed", "filing", "10-K" → FILED

    **Examples:**

    1. Financial metric question:
       question: "What was 3M's revenue in Q4 2023?"
       → Automatically finds: 3M entity + REPORTED_FINANCIALS relationships + Q4 2023 filter
       → Returns subgraph with highlighted revenue and period properties

    2. Multi-entity comparison:
       question: "Compare Apple and Microsoft's profit margins in 2023"
       → Finds: Apple + Microsoft + REPORTED_FINANCIALS
       → Returns subgraph with both companies and their financial data

    3. Ownership question:
       question: "What companies does Google own?"
       → Finds: Google + OWNS relationships
       → Returns subgraph showing all subsidiaries with ownership details

    4. With property filters:
       question: "Show me financial data for Q1 2023"
       property_filters: {"period": "Q1 2023"}
       → Filters subgraph to only include Q1 2023 data

    **Subgraph Output:**
    - All relevant entities (nodes) with descriptions
    - All relationships (edges) with COMPLETE SPG properties
    - Source chunks for textual evidence
    - Properties mentioned in question are highlighted with ⭐

    Args:
        question: The user's complete question
        max_hops: Maximum subgraph expansion depth (default: 2, range: 1-3)
        property_filters: Optional filters for relationship properties (e.g., {"period": "Q4 2023"})

    Returns:
        Comprehensive subgraph containing:
        - Entities relevant to the question
        - Relationships with all SPG properties
        - Source text evidence
        - Highlighted question-relevant properties

    Note: This tool is ideal for questions that require understanding relationships
          between multiple entities or need context from a broader graph structure.
    """
    retriever = get_retriever()

    print(f"\n[Question-Aware Subgraph] Retrieving optimal subgraph for question")

    result = retriever.question_aware_subgraph_retrieval(
        question=question,
        entities=None,  # Auto-extract from question
        max_hops=max_hops,
        include_context=True,
        property_filters=property_filters
    )

    return result


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


