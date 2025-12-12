"""FastAPI application factory."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import health, pipeline, config, auth, chat, graph
from server.core.tracing import setup_langsmith_tracing
from server.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    # Setup logging
    setup_logging()

    # Setup LangSmith tracing
    langsmith_client = setup_langsmith_tracing()

    # Create FastAPI app
    app = FastAPI(
        title="KAG-LangGraph Pipeline Server",
        description="REST API server for running KAG-LangGraph knowledge extraction pipelines",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "Health",
                "description": "Health check and status endpoints"
            },
            {
                "name": "Pipeline",
                "description": "Pipeline execution endpoints"
            },
            {
                "name": "Configuration",
                "description": "Configuration and component information"
            }
        ]
    )

    # Store LangSmith client in app state for access in endpoints
    app.state.langsmith_client = langsmith_client

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])
    app.include_router(config.router, prefix="/pipeline", tags=["Configuration"])
    app.include_router(auth.router, tags=["Authentication"])
    app.include_router(chat.router, prefix="/chat", tags=["Chat"])
    app.include_router(graph.router, prefix="/graph", tags=["Graph"])

    logger.info("FastAPI application created successfully")

    return app
