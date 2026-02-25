"""Shared test fixtures."""
import os
import pytest


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Set minimal environment variables for tests."""
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')


@pytest.fixture
def settings():
    """Return a fresh Settings instance for testing."""
    from server.core.settings import Settings
    return Settings(
        NEO4J_PASSWORD="test-password",
        OPENAI_API_KEY="test-key",
        SECRET_KEY="test-secret-key",
    )


@pytest.fixture
def mock_neo4j_driver(mocker):
    """Mock the Neo4j GraphDatabase.driver."""
    mock_driver = mocker.MagicMock()
    mock_session = mocker.MagicMock()
    mock_driver.session.return_value.__enter__ = mocker.MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = mocker.MagicMock(return_value=False)
    mocker.patch("neo4j.GraphDatabase.driver", return_value=mock_driver)
    return mock_driver


@pytest.fixture
def mock_llm(mocker):
    """Mock ChatOpenAI."""
    mock = mocker.MagicMock()
    mock.invoke.return_value.content = "Test response"
    mocker.patch("server.core.llm.ChatOpenAI", return_value=mock)
    return mock
