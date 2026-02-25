"""Singleton Neo4j driver manager.

Ensures a single driver (= single connection pool) is shared
across all retrievers and writers in the application.
"""
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Optional import — allows the app to start without neo4j installed.
try:
    from neo4j import GraphDatabase, Driver
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    GraphDatabase = None  # type: ignore[assignment, misc]
    Driver = None  # type: ignore[assignment, misc]


class Neo4jManager:
    """Singleton manager for the Neo4j driver.

    Usage::

        manager = Neo4jManager.get_instance(settings)
        driver  = manager.driver

        # or use the context manager for sessions:
        with manager.session() as session:
            session.run("MATCH (n) RETURN count(n)")
    """

    _instance: Optional["Neo4jManager"] = None
    _driver: Optional["Driver"] = None

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        if not HAS_NEO4J:
            raise ImportError(
                "neo4j package is not installed. "
                "Install it with: pip install neo4j"
            )
        self._uri = uri
        self._username = username
        self._password = password
        self._database = database
        self._driver = GraphDatabase.driver(uri, auth=(username, password))
        logger.info("Neo4j driver created (uri=%s, database=%s)", uri, database)

    # ── Class-level singleton access ─────────────────────────────────

    @classmethod
    def get_instance(cls, settings=None) -> "Neo4jManager":
        """Return the singleton instance, creating it if needed."""
        if cls._instance is None:
            if settings is None:
                from server.core.settings import get_settings
                settings = get_settings()
            cls._instance = cls(
                uri=settings.NEO4J_URI,
                username=settings.NEO4J_USERNAME,
                password=settings.NEO4J_PASSWORD,
                database=settings.NEO4J_DATABASE,
            )
        return cls._instance

    # ── Public API ───────────────────────────────────────────────────

    @property
    def driver(self) -> "Driver":
        return self._driver

    @property
    def database(self) -> str:
        return self._database

    @contextmanager
    def session(self, database: Optional[str] = None):
        """Yield a Neo4j session scoped to a `with` block."""
        db = database or self._database
        session = self._driver.session(database=db)
        try:
            yield session
        finally:
            session.close()

    def close(self):
        """Close the driver and release the singleton."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j driver closed")
        Neo4jManager._instance = None
        Neo4jManager._driver = None

    @classmethod
    def reset(cls):
        """Reset the singleton (useful for testing)."""
        if cls._instance:
            cls._instance.close()
        cls._instance = None
