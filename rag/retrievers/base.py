"""Base Neo4j Retriever class."""
import logging

from server.core.database import Neo4jManager, HAS_NEO4J
from .embeddings import EmbeddingHandler

logger = logging.getLogger(__name__)


class Neo4jRetrieverBase:
    """Handles Neo4j database connections and embedding generation.

    Uses the shared Neo4jManager singleton so all retrievers share
    a single connection pool.
    """

    def __init__(self):
        if not HAS_NEO4J:
            raise ImportError("neo4j package is not installed")

        manager = Neo4jManager.get_instance()
        self.driver = manager.driver
        self.database = manager.database
        self.uri = manager._uri
        self.username = manager._username

        # Initialize embedding handler
        self.embedding_handler = EmbeddingHandler()
        self.embedding_model = self.embedding_handler.embedding_model
        self.embedding_type = self.embedding_handler.embedding_type

        logger.info("Neo4jRetrieverBase initialised (database=%s)", self.database)

    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text using the configured model."""
        return self.embedding_handler.generate_embedding(text)

    def _get_or_generate_embedding(self, text: str, cache_key: str = None) -> list:
        """Generate embedding with caching to avoid duplicate generation."""
        return self.embedding_handler._get_or_generate_embedding(text, cache_key)

    def clear_embedding_cache(self):
        """Clear the embedding cache to free memory."""
        return self.embedding_handler.clear_embedding_cache()

    def close(self):
        """Close is now a no-op — the driver lifecycle is managed by Neo4jManager."""
        pass
