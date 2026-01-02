"""
Base Neo4j Retriever class.
"""
import os
from .embeddings import EmbeddingHandler

# Optional Neo4j import
try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False


class Neo4jRetrieverBase:
    """Handles Neo4j database connections and embedding generation."""

    def __init__(self):
        """Initialize Neo4j connection and embedding model."""
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

        # Initialize embedding handler
        self.embedding_handler = EmbeddingHandler()
        
        # Expose embedding properties for compatibility
        self.embedding_model = self.embedding_handler.embedding_model
        self.embedding_type = self.embedding_handler.embedding_type

    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text using the configured model."""
        return self.embedding_handler.generate_embedding(text)

    def _get_or_generate_embedding(self, text: str, cache_key: str = None) -> list:
        """
        Generate embedding with caching to avoid duplicate generation.

        Delegates to the embedding handler which manages the cache.
        """
        return self.embedding_handler._get_or_generate_embedding(text, cache_key)

    def clear_embedding_cache(self):
        """Clear the embedding cache to free memory."""
        return self.embedding_handler.clear_embedding_cache()

    def close(self):
        """Close the Neo4j connection."""
        if hasattr(self, 'driver'):
            self.driver.close()
