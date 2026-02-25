"""Tests for server.core.settings."""
import pytest
from server.core.settings import Settings


class TestSettings:
    """Test the centralised Settings class."""

    def test_defaults(self):
        s = Settings(NEO4J_PASSWORD="pw")
        assert s.NEO4J_URI == "bolt://localhost:7687"
        assert s.NEO4J_USERNAME == "neo4j"
        assert s.SERVER_PORT == 8000
        assert s.LLM_TEMPERATURE == 0.1

    def test_neo4j_password_can_be_empty_string(self):
        s = Settings(NEO4J_PASSWORD="")
        assert s.NEO4J_PASSWORD == ""

    def test_cors_origins_default(self):
        s = Settings(NEO4J_PASSWORD="pw")
        assert "http://localhost:3000" in s.CORS_ORIGINS

    def test_custom_values(self):
        s = Settings(
            NEO4J_PASSWORD="secret",
            NEO4J_DATABASE="mydb",
            CHAT_LLM_MODEL="gpt-4",
            SERVER_PORT=9000,
        )
        assert s.NEO4J_DATABASE == "mydb"
        assert s.CHAT_LLM_MODEL == "gpt-4"
        assert s.SERVER_PORT == 9000
