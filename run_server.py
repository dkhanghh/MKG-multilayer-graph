#!/usr/bin/env python3
"""KAG-LangGraph Pipeline Server Entry Point.

Exposes both:
- FastAPI app for REST API (uvicorn run_server:app)
- LangGraph workflow for development (langgraph dev)

Run with::

    python run_server.py
    uvicorn run_server:app --reload
"""
import logging
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from server.api.app import create_app
from server.core.config import load_config, get_default_config
from server.core.settings import get_settings
from knowledge_graphs.pipeline.langgraph_executor import LangGraphExecutor

logger = logging.getLogger(__name__)

# ── FastAPI app (for uvicorn) ────────────────────────────────────────
app = create_app()

# ── Pipeline config ──────────────────────────────────────────────────
settings = get_settings()

pipeline_config = None
try:
    from knowledge_graphs.pipeline.config import load_config as load_yaml_config, resolve_environment_variables

    raw_config = load_yaml_config(settings.PIPELINE_CONFIG_PATH)
    pipeline_config = resolve_environment_variables(raw_config)
    logger.info("Loaded pipeline config from %s", settings.PIPELINE_CONFIG_PATH)
except FileNotFoundError:
    logger.warning("Config file not found: %s — using defaults", settings.PIPELINE_CONFIG_PATH)
    pipeline_config = get_default_config()
except Exception as exc:
    logger.error("Error loading config: %s — using defaults", exc)
    pipeline_config = get_default_config()

# ── LangGraph workflow (for langgraph dev) ───────────────────────────
try:
    executor = LangGraphExecutor(config=pipeline_config)
    graph = executor.compiled_workflow
    logger.info("LangGraph workflow created successfully")
except Exception as exc:
    logger.error("Could not create LangGraph workflow: %s", exc)
    graph = None


def main() -> int:
    """Start the server with uvicorn."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed. Install with: pip install uvicorn")
        return 1

    logger.info("Starting server on %s:%s", settings.SERVER_HOST, settings.SERVER_PORT)

    uvicorn.run(
        "run_server:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.SERVER_RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
