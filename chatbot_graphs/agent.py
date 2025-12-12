"""
ReAct agent setup for RAG chatbot.
"""
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from .state import ChatState
from .tools import (
    neo4j_retrieval_tool,
    neo4j_vector_search_tool,
    neo4j_multi_query_search_tool,
    neo4j_entity_graph_search_tool,
    neo4j_hybrid_search_tool,
    neo4j_typed_vector_search_tool,
    neo4j_semantic_path_search_tool,
    neo4j_question_subgraph_tool
)



# Initialize LLM for the agent
_llm = None
_react_agent = None

def get_react_agent():
    """Get or create the ReAct agent instance."""
    global _llm, _react_agent

    if _react_agent is None:
        # Initialize ChatOpenAI
        base_url = os.getenv("CHAT_OPENAI_BASE_URL")
        api_key = os.getenv("CHAT_OPENAI_API_KEY")

        # If using custom base_url without api_key, use "EMPTY" as recommended by LangChain
        # See: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
        if base_url and not api_key:
            api_key = "EMPTY"

        llm_kwargs = {
            "model": os.getenv("CHAT_LLM_MODEL", "gpt-4o-mini"),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
            "api_key": api_key,
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
        # SPG-aware tools for Semantic Property Graph queries
        tools = [
            # neo4j_question_subgraph_tool,  # Intelligent 5-stage subgraph retrieval (AUTO)
            neo4j_hybrid_search_tool,      # Comprehensive hybrid search with RRF ranking
            # neo4j_entity_graph_search_tool,  # Find relationships between specific entities
            # neo4j_typed_vector_search_tool,  # Type-filtered vector search (SPG-aware)
            # neo4j_semantic_path_search_tool,  # Multi-hop path search with properties
            # neo4j_vector_search_tool,
            # neo4j_retrieval_tool,
        ]

        # Create ReAct agent
        _react_agent = create_react_agent(_llm, tools)

        print("[ReAct Agent] Initialized with SPG-aware tools:")
        if neo4j_question_subgraph_tool in tools:
            print("  - Question Subgraph Tool: Intelligent 5-stage subgraph retrieval (AUTO)")
        if neo4j_hybrid_search_tool in tools:
            print("  - Hybrid Search Tool: Vector + Text + Entity Graph + Chunk Search (RRF)")
        if neo4j_entity_graph_search_tool in tools:
            print("  - Entity Graph Search: Find relationships between specific entities (with auto-expansion)")
        if neo4j_typed_vector_search_tool in tools:
            print("  - Typed Vector Search: Type-filtered semantic search (Company, Executive, etc.)")
        if neo4j_semantic_path_search_tool in tools:
            print("  - Semantic Path Search: Multi-hop connection discovery with properties")

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
You have access to the **neo4j_question_subgraph_tool** - the MOST INTELLIGENT tool for SPG (Semantic Property Graph) retrieval.

**What neo4j_question_subgraph_tool Does:**

This tool uses a **5-stage intelligent pipeline** to retrieve the optimal subgraph for answering questions:

1. **Entity Identification**: Automatically finds seed entities from the question using vector similarity
2. **Type Inference**: Infers required entity/relationship types from question keywords
3. **Subgraph Expansion**: Expands k-hop neighborhood with relevance-based filtering (up to max_hops)
4. **Property Highlighting**: Highlights properties mentioned in the question with ⭐
5. **Context Enrichment**: Includes source chunks for textual evidence

**Automatic Type Inference:**
The tool automatically detects relationship types from keywords:
- "revenue", "profit", "earnings", "financial", "income" → REPORTED_FINANCIALS
- "owns", "subsidiary", "acquisition", "ownership" → OWNS
- "executive", "CEO", "CFO", "employee", "officer" → EMPLOYS
- "filed", "filing", "10-K", "10-Q", "report" → FILED

**How to Use:**

Simply pass the COMPLETE user question to the tool:

```python
neo4j_question_subgraph_tool(
    question="What was 3M's revenue in Q4 2023?",
    max_hops=2  # Optional: 1-3 hops, default is 2
)
```

The tool will:
✅ Automatically extract entities ("3M", "Q4 2023", "revenue")
✅ Detect relationship type (REPORTED_FINANCIALS)
✅ Expand subgraph up to 2 hops
✅ Highlight revenue and period properties
✅ Return complete context with ALL SPG properties

**Output Includes:**
- All relevant entities (nodes) with types and descriptions
- All relationships (edges) with COMPLETE SPG properties
- Source chunks with actual text evidence
- Properties mentioned in question highlighted with ⭐

**Examples:**

1. Financial metric question:
   ```python
   question = "What was 3M's revenue in Q4 2023?"
   # Auto-detects: 3M entity + REPORTED_FINANCIALS + highlights revenue, period
   ```

2. Multi-entity comparison:
   ```python
   question = "Compare Apple and Microsoft's profit margins in 2023"
   # Auto-detects: Apple + Microsoft + REPORTED_FINANCIALS + highlights profit
   ```

3. Ownership question:
   ```python
   question = "What companies does Google own?"
   # Auto-detects: Google + OWNS relationships
   ```

4. Executive question:
   ```python
   question = "Who is the CEO of 3M?"
   # Auto-detects: 3M + EMPLOYS + filters for CEO role
   ```

**SPG Property-Rich Results:**
- ALL relationship properties are returned (revenue, profit, dates, ownership%, etc.)
- Financial metrics are stored as edge properties on REPORTED_FINANCIALS relationships
- ALWAYS include property values in your answer when available

**CRITICAL RULES TO PREVENT RECURSION:**
1. **ONLY 1 tool call** - The question_subgraph_tool retrieves comprehensive context in ONE call
2. **NO repeated queries** - Do NOT call the tool multiple times with the same or similar questions
3. **Answer immediately** - After ONE tool call, synthesize answer from retrieved subgraph
4. **Use ALL information** - The subgraph contains complete context, use it all

**Expected Flow:**
1. Call neo4j_question_subgraph_tool ONCE with the user's complete question
2. Review the comprehensive subgraph with entities, relationships, and properties
3. Formulate complete answer using:
   - Entity information
   - Relationship properties (especially highlighted ones ⭐)
   - Source chunk evidence
4. Provide final answer to user (DO NOT call tool again)

**Query Strategy by Intent:**
- factual_lookup: 1 tool call → Extract specific values → ANSWER
- comparison: 1 tool call → Compare properties from subgraph → ANSWER
- relationship_query: 1 tool call → Describe relationships → ANSWER
- explanation: 1 tool call → Explain using subgraph context → ANSWER

**DO NOT:**
- Call the tool more than ONCE
- Call the tool again with rephrased questions
- Say "let me search again" - the first result contains everything needed
- Ignore the highlighted properties (⭐) - they are question-relevant

**Property Values in Answers:**
✓ GOOD: "3M's Q4 2023 revenue was $8.23 billion (from REPORTED_FINANCIALS relationship)"
✗ BAD: "The company reported financial data"

Now call neo4j_question_subgraph_tool ONCE and provide your complete answer.""")

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


