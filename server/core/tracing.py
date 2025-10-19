"""LangSmith tracing configuration."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import LangSmith, make optional
try:
    from langsmith import Client
    HAS_LANGSMITH = True
except ImportError:
    HAS_LANGSMITH = False
    logger.info("LangSmith not available")


def setup_langsmith_tracing() -> Optional[any]:
    """
    Setup LangSmith tracing configuration.

    Returns:
        LangSmith Client instance or None if not available
    """
    if not HAS_LANGSMITH:
        logger.info("LangSmith tracing disabled (not installed)")
        return None

    # Get LangSmith configuration from environment
    langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
    langsmith_project = os.getenv("LANGSMITH_PROJECT", "kag-langgraph-server")
    langsmith_endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    if not langsmith_api_key:
        logger.warning("LANGSMITH_API_KEY not set. LangSmith tracing disabled.")
        return None

    try:
        # Initialize LangSmith client
        client = Client(
            api_url=langsmith_endpoint,
            api_key=langsmith_api_key
        )

        # Set environment variables for LangChain integration
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = langsmith_project
        os.environ["LANGCHAIN_ENDPOINT"] = langsmith_endpoint
        os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key

        logger.info(f"LangSmith tracing enabled for project: {langsmith_project}")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith: {e}")
        return None


# Create traceable decorator (fallback if LangSmith not available)
if HAS_LANGSMITH:
    from langsmith import traceable
else:
    def traceable(name=None, **kwargs):
        """Dummy decorator when LangSmith is not available."""
        def decorator(func):
            return func
        return decorator
