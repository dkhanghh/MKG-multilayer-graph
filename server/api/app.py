"""FastAPI application factory."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.exceptions import register_exception_handlers
from server.api.middleware import RequestLoggingMiddleware
from server.api.routes import health, pipeline, config, auth, chat, graph
from server.core.settings import get_settings
from server.core.tracing import setup_langsmith_tracing
from server.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    setup_logging(level=settings.LOG_LEVEL)
    langsmith_client = setup_langsmith_tracing()

    app = FastAPI(
        title="KAG-LangGraph Pipeline Server",
        description="REST API server for running KAG-LangGraph knowledge extraction pipelines",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Health", "description": "Health check and status endpoints"},
            {"name": "Pipeline", "description": "Pipeline execution endpoints"},
            {"name": "Configuration", "description": "Configuration and component information"},
        ],
    )

    app.state.langsmith_client = langsmith_client

    # ── Middleware (order matters — outermost first) ──────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routes ───────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])
    app.include_router(config.router, prefix="/pipeline", tags=["Configuration"])
    app.include_router(auth.router, tags=["Authentication"])
    app.include_router(chat.router, prefix="/chat", tags=["Chat"])
    app.include_router(graph.router, prefix="/graph", tags=["Graph"])

    logger.info("FastAPI application created (CORS origins=%s)", settings.CORS_ORIGINS)
    return app
