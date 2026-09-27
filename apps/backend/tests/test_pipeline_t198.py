"""Tests for T-198: POST /api/v1/pipeline/full + GET /api/v1/pipeline/status/{task_id}.

T-198k: backend использует celery как lazy client (через _get_celery_app()).
Тесты мокают `_get_celery_app` вместо `celery_app` (которого теперь нет).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture()
def app():
    return create_app()


class TestPipelineTrigger:
    """POST /api/v1/pipeline/full — запускает Celery task."""

    @pytest.mark.asyncio
    async def test_trigger_returns_task_id(self, app) -> None:
        """POST /pipeline/full возвращает task_id и status=queued."""
        with patch("app.api.pipeline._get_celery_app") as mock_get:
            mock_celery = MagicMock()
            mock_result = MagicMock()
            mock_result.id = "abc-123-def"
            mock_celery.send_task = MagicMock(return_value=mock_result)
            mock_get.return_value = mock_celery

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post("/api/v1/pipeline/full")
                assert r.status_code == 200
                data = r.json()
                assert "task_id" in data
                assert data["task_id"] == "abc-123-def"
                assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_trigger_sends_correct_task(self, app) -> None:
        """POST вызывает _get_celery_app().send_task с правильным task name."""
        with patch("app.api.pipeline._get_celery_app") as mock_get:
            mock_celery = MagicMock()
            mock_result = MagicMock()
            mock_result.id = "xyz-789"
            mock_celery.send_task = MagicMock(return_value=mock_result)
            mock_get.return_value = mock_celery

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post("/api/v1/pipeline/full")

            mock_celery.send_task.assert_called_once()
            args, kwargs = mock_celery.send_task.call_args
            task_name = args[0] if args else kwargs.get("name")
            assert task_name == "ml_pipeline.full_pipeline"


class TestPipelineStatus:
    """GET /api/v1/pipeline/status/{task_id} — polling результата."""

    @pytest.mark.asyncio
    async def test_status_running(self, app) -> None:
        """Task в процессе → status=STARTED/RUNNING."""
        with patch("app.api.pipeline._get_celery_app") as mock_get:
            mock_celery = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "STARTED"
            mock_result.result = None
            mock_celery.AsyncResult.return_value = mock_result
            mock_get.return_value = mock_celery

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/api/v1/pipeline/status/abc-123")
                assert r.status_code == 200
                data = r.json()
                assert data["status"] == "STARTED"
                assert data["task_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_status_success(self, app) -> None:
        """Task завершён → status=SUCCESS с result."""
        with patch("app.api.pipeline._get_celery_app") as mock_get:
            mock_celery = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "SUCCESS"
            mock_result.result = {"status": "ok", "model_id": "xgboost_v_default"}
            mock_celery.AsyncResult.return_value = mock_result
            mock_get.return_value = mock_celery

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/api/v1/pipeline/status/abc-123")
                data = r.json()
                assert data["status"] == "SUCCESS"
                assert data["result"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_status_failure(self, app) -> None:
        """Task упал → status=FAILURE."""
        with patch("app.api.pipeline._get_celery_app") as mock_get:
            mock_celery = MagicMock()
            mock_result = MagicMock()
            mock_result.status = "FAILURE"
            mock_result.result = {"status": "error", "stage": "train"}
            mock_celery.AsyncResult.return_value = mock_result
            mock_get.return_value = mock_celery

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/api/v1/pipeline/status/abc-123")
                data = r.json()
                assert data["status"] == "FAILURE"
