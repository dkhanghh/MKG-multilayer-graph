"""
Neo4j Retriever package.
"""
from .base import Neo4jRetrieverBase
from .search import SearchMixin
from .graph import GraphMixin

class Neo4jRetriever(Neo4jRetrieverBase, SearchMixin, GraphMixin):
    """
    Unified Neo4j Retriever class combining all capabilities.
    """
    pass

# Create global retriever instance
_retriever = None

def get_retriever() -> Neo4jRetriever:
    """Get or create the Neo4j retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = Neo4jRetriever()
    return _retriever
