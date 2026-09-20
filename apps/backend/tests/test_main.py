"""Tests for the FastAPI application factory (app.main)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import __version__
from app.main import create_app


def test_create_app_returns_fastapi_instance() -> None:
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.title == "Transit-AI Backend"
    assert app.version == __version__


def test_app_has_health_router() -> None:
    """Routes registered under /api/v1 should appear in the OpenAPI schema."""
    app = create_app()
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/v1/healthz" in paths
    assert "/api/v1/version" in paths
    assert "/api/v1/readyz" in paths


def test_root_endpoint_returns_meta() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "transit-ai-backend"
    assert body["docs"] == "/docs"


def test_healthz_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_returns_version_and_commit() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    # git_commit is either a SHA string or None (not a git repo)
    assert "git_commit" in body
    assert body["app_env"] in {"dev", "test", "prod"}


def test_readyz_returns_ok_structure() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "checks" in body


def test_openapi_schema_is_generated() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Transit-AI Backend"
    assert "/api/v1/healthz" in schema["paths"]
