"""Health check endpoints."""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/")
async def root():
    """
    Root endpoint with API information.

    Returns:
        API metadata and documentation links
    """
    return {
        "message": "KAG-LangGraph Pipeline Server",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "kag-langgraph-server"
    }
