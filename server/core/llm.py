"""Shared LLM factory — single place to create ChatOpenAI instances."""
import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from server.core.settings import get_settings

logger = logging.getLogger(__name__)


def create_chat_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> ChatOpenAI:
    """Create a ChatOpenAI instance from centralised settings.

    Args:
        model: Override the default model name.
        temperature: Override the default temperature.

    Returns:
        Configured ChatOpenAI instance.
    """
    settings = get_settings()

    api_key = settings.CHAT_OPENAI_API_KEY or settings.OPENAI_API_KEY
    base_url = settings.CHAT_OPENAI_BASE_URL

    # LangChain requires a non-empty api_key even for custom endpoints.
    if base_url and not api_key:
        api_key = "EMPTY"

    llm_kwargs: dict = {
        "model": model or settings.CHAT_LLM_MODEL,
        "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
        "api_key": api_key,
    }

    if base_url:
        llm_kwargs["base_url"] = base_url
        llm_kwargs["default_headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

    logger.info("Creating ChatOpenAI (model=%s, base_url=%s)", llm_kwargs["model"], base_url)
    return ChatOpenAI(**llm_kwargs)
