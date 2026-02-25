"""Tests for server.core.database."""
import pytest
from unittest.mock import MagicMock, patch


class TestNeo4jManager:
    """Test the Neo4j singleton manager."""

    def setup_method(self):
        """Reset singleton between tests."""
        from server.core.database import Neo4jManager
        Neo4jManager._instance = None

    @patch("server.core.database.GraphDatabase")
    def test_singleton(self, mock_gdb):
        """Multiple get_instance calls should return the same object."""
        from server.core.database import Neo4jManager
        from server.core.settings import Settings

        settings = Settings(NEO4J_PASSWORD="pw")

        m1 = Neo4jManager.get_instance(settings)
        m2 = Neo4jManager.get_instance(settings)
        assert m1 is m2
        # Driver should only be created once
        assert mock_gdb.driver.call_count == 1

    @patch("server.core.database.GraphDatabase")
    def test_session_context_manager(self, mock_gdb):
        """session() should yield a session and close it."""
        from server.core.database import Neo4jManager
        from server.core.settings import Settings

        mock_session = MagicMock()
        mock_gdb.driver.return_value.session.return_value = mock_session

        settings = Settings(NEO4J_PASSWORD="pw")
        manager = Neo4jManager.get_instance(settings)

        with manager.session() as session:
            assert session is mock_session

        mock_session.close.assert_called_once()

    @patch("server.core.database.GraphDatabase")
    def test_close_resets_singleton(self, mock_gdb):
        """close() should allow a new instance to be created."""
        from server.core.database import Neo4jManager
        from server.core.settings import Settings

        settings = Settings(NEO4J_PASSWORD="pw")

        m1 = Neo4jManager.get_instance(settings)
        m1.close()
        assert Neo4jManager._instance is None

        m2 = Neo4jManager.get_instance(settings)
        assert m2 is not m1

    def test_raises_without_neo4j(self, mocker):
        """Should raise ImportError if neo4j is not installed."""
        mocker.patch("server.core.database.HAS_NEO4J", False)
        from server.core.database import Neo4jManager

        with pytest.raises(ImportError, match="neo4j"):
            Neo4jManager("bolt://localhost:7687", "neo4j", "pw")
