"""Tests for server.api.exceptions."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.exceptions import (
    APIError,
    NotFoundError,
    ValidationError,
    register_exception_handlers,
)


@pytest.fixture
def client():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/api-error")
    async def raise_api_error():
        raise APIError(detail="something broke")

    @app.get("/not-found")
    async def raise_not_found():
        raise NotFoundError(detail="no such thing")

    @app.get("/validation")
    async def raise_validation():
        raise ValidationError(detail="bad input")

    @app.get("/unhandled")
    async def raise_unhandled():
        raise RuntimeError("oops")

    return TestClient(app, raise_server_exceptions=False)


class TestExceptionHandlers:
    def test_api_error(self, client):
        resp = client.get("/api-error")
        assert resp.status_code == 500
        assert resp.json() == {"error": "something broke"}

    def test_not_found(self, client):
        resp = client.get("/not-found")
        assert resp.status_code == 404
        assert resp.json() == {"error": "no such thing"}

    def test_validation_error(self, client):
        resp = client.get("/validation")
        assert resp.status_code == 422
        assert resp.json() == {"error": "bad input"}

    def test_unhandled_returns_500(self, client):
        resp = client.get("/unhandled")
        assert resp.status_code == 500
        # Should NOT leak the internal "oops" message
        assert resp.json() == {"error": "Internal server error"}
