"""
LangGraph workflow construction for RAG chatbot.
"""
from langgraph.graph import StateGraph, END

from .state import ChatState
from .nodes import preprocess_query_node
from .agent import agent_node



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
    # workflow.add_node("preprocess_query", preprocess_query_node)
    workflow.add_node("agent", agent_node)

    # Set entry point to preprocessing
    workflow.set_entry_point("agent")

    # Add edge from preprocessing to agent
    # workflow.add_edge("preprocess_query", "agent")

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
