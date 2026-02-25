"""LangSmith tracing configuration."""
import logging
import os
from typing import Optional

from server.core.settings import get_settings

logger = logging.getLogger(__name__)

try:
    from langsmith import Client
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False
    logger.info("LangSmith not available")


def setup_langsmith_tracing() -> Optional[Client]:
    """Setup LangSmith tracing configuration.

    Returns:
        LangSmith Client instance or None if not available/configured.
    """
    if not HAS_LANGSMITH:
        logger.info("LangSmith tracing disabled (not installed)")
        return None

    settings = get_settings()

    if not settings.LANGSMITH_API_KEY:
        logger.warning("LANGSMITH_API_KEY not set — tracing disabled")
        return None

    try:
        client = Client(
            api_url=settings.LANGSMITH_ENDPOINT,
            api_key=settings.LANGSMITH_API_KEY,
        )

        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY

        logger.info("LangSmith tracing enabled for project: %s", settings.LANGSMITH_PROJECT)
        return client
    except Exception as exc:
        logger.error("Failed to initialise LangSmith: %s", exc)
        return None


# Traceable decorator (no-op fallback if LangSmith unavailable)
if HAS_LANGSMITH:
    from langsmith import traceable
else:
    def traceable(name=None, **kwargs):
        """Dummy decorator when LangSmith is not available."""
        def decorator(func):
            return func
        return decorator
