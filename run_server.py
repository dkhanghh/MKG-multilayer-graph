#!/usr/bin/env python3
"""
KAG-LangGraph Pipeline Server Entry Point

This module serves as the main entry point for the server, exposing both:
- FastAPI app for REST API (uvicorn run_server:app)
- LangGraph workflow for development (langgraph dev)

Run with:
    python run_server.py
    uvicorn run_server:app --reload
    ./run_server.py
    langgraph dev
"""
import os
import sys
import logging

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    logging.info("Loaded environment variables from .env file")
except ImportError:
    logging.info("python-dotenv not available, using system environment variables")

# Import FastAPI app from modular server structure
from server.api.app import create_app
from server.core.config import DEFAULT_CONFIG

# Import LangGraph components
from knowledge_graphs.pipeline.langgraph_executor import LangGraphExecutor

# Create the FastAPI application (exposed for uvicorn)
app = create_app()

# Load pipeline configuration from file or use default
config_path = os.getenv("PIPELINE_CONFIG_PATH", "configs/financebench_pipeline.yaml")
pipeline_config = None

try:
    from knowledge_graphs.pipeline.config import load_config, resolve_environment_variables

    # Load config from YAML file
    raw_config = load_config(config_path)

    # Resolve environment variables (${VAR_NAME} syntax)
    pipeline_config = resolve_environment_variables(raw_config)

    logging.info(f"✅ Loaded pipeline config from {config_path}")
except FileNotFoundError:
    logging.warning(f"⚠️  Config file not found: {config_path}, using DEFAULT_CONFIG")
    pipeline_config = DEFAULT_CONFIG
except Exception as e:
    logging.error(f"❌ Error loading config from {config_path}: {e}, using DEFAULT_CONFIG")
    pipeline_config = DEFAULT_CONFIG

# Create the LangGraph workflow (exposed for langgraph dev)
try:
    executor = LangGraphExecutor(config=pipeline_config)
    graph = executor.compiled_workflow
    logging.info("✅ LangGraph workflow created successfully")
except Exception as e:
    logging.error(f"❌ Could not create graph export: {e}")
    graph = None


def main():
    """
    Main function to start the server with uvicorn.

    This function can be called directly when running as a script.
    """
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is not installed.")
        print("Please install it with: pip install uvicorn")
        return 1

    # Configuration from environment variables
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    reload = os.getenv("SERVER_RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger = logging.getLogger(__name__)
    logger.info(f"Starting KAG-LangGraph Pipeline Server on {host}:{port}")
    logger.info(f"API documentation available at: http://{host}:{port}/docs")
    logger.info(f"OpenAPI spec available at: http://{host}:{port}/redoc")

    # Start the server
    uvicorn.run(
        "run_server:app",  # Module and app variable
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True,
        loop="asyncio"  # Required for nest_asyncio to work with Uvicorn
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
