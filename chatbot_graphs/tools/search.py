"""
Search-based retrieval tools for Neo4j knowledge graph.
"""
from langchain_core.tools import tool
from chatbot_graphs.retrievers import get_retriever

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
