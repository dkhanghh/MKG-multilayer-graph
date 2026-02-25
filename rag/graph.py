"""LangGraph workflow construction for RAG chatbot."""
import logging

from langgraph.graph import StateGraph, END

from .state import ChatState
from .agent import agent_node

logger = logging.getLogger(__name__)


def build_graph():
    """Build the RAG chat graph with a ReAct agent.

    Graph flow:  agent (ReAct) -> END

    The ReAct agent internally manages tool selection, calling, reasoning
    iterations, and final answer synthesis.

    Returns:
        Compiled StateGraph ready for execution.
    """
    workflow = StateGraph(ChatState)
    workflow.add_node("agent", agent_node)
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    logger.info("Built RAG graph: agent (ReAct) -> END")
    return workflow.compile()


# Main export for LangGraph server (langgraph.json)
graph = build_graph()
