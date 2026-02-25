"""Tests for server.core.llm."""
import pytest


class TestCreateChatLLM:
    """Test the shared LLM factory."""

    def test_creates_instance(self, mock_llm, monkeypatch):
        """LLM factory should create a ChatOpenAI with settings values."""
        from server.core.llm import create_chat_llm

        llm = create_chat_llm()
        # The mock was returned by patching ChatOpenAI
        assert llm is mock_llm

    def test_override_model(self, mock_llm, mocker):
        """Model parameter should override the settings default."""
        from server.core.llm import create_chat_llm, ChatOpenAI

        create_chat_llm(model="gpt-4-turbo")
        # Check the kwargs passed to ChatOpenAI constructor
        call_kwargs = ChatOpenAI.call_args[1]
        assert call_kwargs["model"] == "gpt-4-turbo"

    def test_empty_api_key_with_base_url(self, mocker, monkeypatch):
        """When base_url is set but no api_key, should use 'EMPTY'."""
        monkeypatch.setenv("CHAT_OPENAI_BASE_URL", "http://localhost:8080")
        monkeypatch.setenv("CHAT_OPENAI_API_KEY", "")
        monkeypatch.setenv("OPENAI_API_KEY", "")

        mock_cls = mocker.patch("server.core.llm.ChatOpenAI")

        # Need to reimport to pick up changed env
        from server.core.settings import Settings
        mocker.patch("server.core.llm.get_settings", return_value=Settings(
            CHAT_OPENAI_BASE_URL="http://localhost:8080",
            CHAT_OPENAI_API_KEY="",
            OPENAI_API_KEY="",
            NEO4J_PASSWORD="pw",
        ))

        from server.core.llm import create_chat_llm
        create_chat_llm()

        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["api_key"] == "EMPTY"
        assert call_kwargs["base_url"] == "http://localhost:8080"
