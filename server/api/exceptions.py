"""Structured exception handling for the API.

Provides typed HTTP exceptions and a global handler that returns
consistent JSON error responses without leaking internal details.
"""
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ── Typed exceptions ─────────────────────────────────────────────────

class APIError(Exception):
    """Base class for all API errors."""

    def __init__(self, status_code: int = 500, detail: str = "Internal server error"):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ValidationError(APIError):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=422, detail=detail)


class NotFoundError(APIError):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class AuthenticationError(APIError):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class ServiceUnavailableError(APIError):
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(status_code=503, detail=detail)


# ── Global exception handlers ────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
