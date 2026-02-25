"""RAG chatbot with Neo4j knowledge graph integration.

This package provides a modular RAG (Retrieval-Augmented Generation) chatbot
that uses a Neo4j knowledge graph for information retrieval and LangGraph for
orchestration.
"""
from dotenv import load_dotenv

load_dotenv(override=True)

from .state import ChatState
from .retrievers import Neo4jRetriever, get_retriever
from .tools import (
    neo4j_retrieval_tool,
    neo4j_vector_search_tool,
    neo4j_multi_query_search_tool,
    neo4j_entity_graph_search_tool,
    neo4j_hybrid_search_tool,
)
from .agent import get_react_agent, agent_node
from .graph import build_graph, graph

__all__ = [
    "ChatState",
    "Neo4jRetriever",
    "get_retriever",
    "neo4j_retrieval_tool",
    "neo4j_vector_search_tool",
    "neo4j_multi_query_search_tool",
    "neo4j_entity_graph_search_tool",
    "neo4j_hybrid_search_tool",
    "get_react_agent",
    "agent_node",
    "build_graph",
    "graph",
]
