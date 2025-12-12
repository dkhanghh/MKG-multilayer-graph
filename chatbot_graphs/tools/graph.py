"""
Graph-based retrieval tools for Neo4j knowledge graph.
"""
from langchain_core.tools import tool
from chatbot_graphs.retrievers import get_retriever

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
        print(f"  Note: Relationship type filter '{path_relationship_types}' is not yet implemented")

    result = retriever.semantic_path_search(
        start_entity=start_entity,
        end_entity=end_entity,
        max_hops=max_hops
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
