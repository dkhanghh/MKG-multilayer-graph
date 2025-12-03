"""
RAG chatbot with Neo4j knowledge graph integration.

This package provides a modular RAG (Retrieval-Augmented Generation) chatbot
that uses a Neo4j knowledge graph for information retrieval and LangGraph for
orchestration.

Main exports:
- graph: The compiled LangGraph workflow (for langgraph.json)
- ChatState: State type definition
- Neo4jRetriever: Knowledge graph retriever
- build_graph: Function to build the graph workflow
"""
# Load environment variables
from dotenv import load_dotenv
load_dotenv(override=True)

from .state import ChatState
from .retrievers import Neo4jRetriever, get_retriever
from .tools import (
    neo4j_retrieval_tool,
    neo4j_vector_search_tool,
    neo4j_multi_query_search_tool,
    neo4j_entity_graph_search_tool,
    neo4j_hybrid_search_tool
)
from .nodes import preprocess_query_node
from .agent import get_react_agent, agent_node
from .graph import build_graph, graph

__all__ = [
    # State
    "ChatState",

    # Retriever
    "Neo4jRetriever",
    "get_retriever",

    # Tools
    "neo4j_retrieval_tool",
    "neo4j_vector_search_tool",
    "neo4j_multi_query_search_tool",
    "neo4j_entity_graph_search_tool",
    "neo4j_hybrid_search_tool",

    # Nodes
    "preprocess_query_node",

    # Agent
    "get_react_agent",
    "agent_node",

    # Graph
    "build_graph",
    "graph",  # Main export for langgraph.json
]
