"""Tests for T-198: GET /api/v1/predictions/status.

Возвращает информацию о состоянии predictions в БД:
  - has_predictions: bool (для UI — показывать EmptyPredictions или графики)
  - predictions_count: int (14640 если есть test_submission baseline)
  - actuals_count: int (68801 если загружены из train.csv)
  - model_ids: list[str] (уникальные model_id в БД)
  - running_pipeline: bool (есть ли активные Celery tasks)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture()
def app():
    return create_app()


class TestPredictionsStatusEndpoint:
    """GET /api/v1/predictions/status — endpoint registration + response shape."""

    @pytest.mark.asyncio
    async def test_endpoint_registered(self, app) -> None:
        """Endpoint существует (даже если БД недоступна — mock)."""

        from app.api.predictions_status import _get_redis
        from app.db import get_db

        # Mock get_db
        async def mock_db():
            session = AsyncMock()
            # SELECT count(Prediction.id) → 0
            # SELECT count(Actual.id) → 0
            # SELECT distinct(model_id) → []
            count_result = MagicMock()
            count_result.scalar = MagicMock(return_value=0)
            distinct_result = MagicMock()
            distinct_result.scalars = MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[]))
            )
            session.execute = AsyncMock(
                side_effect=[count_result, count_result, distinct_result]
            )
            yield session

        # Mock redis
        async def mock_redis():
            client = AsyncMock()
            client.keys = AsyncMock(return_value=[])
            yield client

        app.dependency_overrides[get_db] = mock_db
        app.dependency_overrides[_get_redis] = mock_redis
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/api/v1/predictions/status")
                assert r.status_code == 200
                data = r.json()
                assert "has_predictions" in data
                assert "predictions_count" in data
                assert "actuals_count" in data
                assert "model_ids" in data
                assert "running_pipeline" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_empty_db_has_predictions_false(self, app) -> None:
        """Если БД пустая → has_predictions=false, count=0."""
        from app.api.predictions_status import _get_redis
        from app.db import get_db

        async def mock_db():
            session = AsyncMock()
            count_result = MagicMock()
            count_result.scalar = MagicMock(return_value=0)
            distinct_result = MagicMock()
            distinct_result.scalars = MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[]))
            )
            session.execute = AsyncMock(
                side_effect=[count_result, count_result, distinct_result]
            )
            yield session

        async def mock_redis():
            client = AsyncMock()
            client.keys = AsyncMock(return_value=[])
            yield client

        app.dependency_overrides[get_db] = mock_db
        app.dependency_overrides[_get_redis] = mock_redis
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/api/v1/predictions/status")
                data = r.json()
                assert data["has_predictions"] is False
                assert data["predictions_count"] == 0
                assert data["model_ids"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_seeded_has_predictions_true(self, app) -> None:
        """Если predictions есть → has_predictions=true, count=14640."""
        from app.api.predictions_status import _get_redis
        from app.db import get_db

        async def mock_db():
            session = AsyncMock()
            count_pred = MagicMock()
            count_pred.scalar = MagicMock(return_value=14640)
            count_act = MagicMock()
            count_act.scalar = MagicMock(return_value=68801)
            distinct_result = MagicMock()
            distinct_result.scalars = MagicMock(
                return_value=MagicMock(
                    all=MagicMock(return_value=["test_submission_baseline"])
                )
            )
            session.execute = AsyncMock(
                side_effect=[count_pred, count_act, distinct_result]
            )
            yield session

        async def mock_redis():
            client = AsyncMock()
            client.keys = AsyncMock(return_value=[])
            yield client

        app.dependency_overrides[get_db] = mock_db
        app.dependency_overrides[_get_redis] = mock_redis
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/api/v1/predictions/status")
                data = r.json()
                assert data["has_predictions"] is True
                assert data["predictions_count"] == 14640
                assert data["actuals_count"] == 68801
                assert data["model_ids"] == ["test_submission_baseline"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_running_pipeline_flag(self, app) -> None:
        """running_pipeline=true если в Redis есть celery-task-meta-* ключи."""
        from app.api.predictions_status import _get_redis
        from app.db import get_db

        async def mock_db():
            session = AsyncMock()
            count_result = MagicMock()
            count_result.scalar = MagicMock(return_value=14640)
            distinct_result = MagicMock()
            distinct_result.scalars = MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[]))
            )
            session.execute = AsyncMock(
                side_effect=[count_result, count_result, distinct_result]
            )
            yield session

        async def mock_redis_with_tasks():
            client = AsyncMock()
            # Имитируем активные Celery tasks
            client.keys = AsyncMock(
                return_value=["celery-task-meta-abc123", "celery-task-meta-def456"]
            )
            yield client

        app.dependency_overrides[get_db] = mock_db
        app.dependency_overrides[_get_redis] = mock_redis_with_tasks
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/api/v1/predictions/status")
                data = r.json()
                assert data["running_pipeline"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_redis_failure_does_not_crash(self, app) -> None:
        """Если Redis недоступен — running_pipeline=false (best-effort)."""
        from app.api.predictions_status import _get_redis
        from app.db import get_db

        async def mock_db():
            session = AsyncMock()
            count_result = MagicMock()
            count_result.scalar = MagicMock(return_value=0)
            distinct_result = MagicMock()
            distinct_result.scalars = MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=[]))
            )
            session.execute = AsyncMock(
                side_effect=[count_result, count_result, distinct_result]
            )
            yield session

        async def mock_redis_fail():
            client = AsyncMock()
            client.keys = AsyncMock(side_effect=ConnectionError("Redis down"))
            yield client

        app.dependency_overrides[get_db] = mock_db
        app.dependency_overrides[_get_redis] = mock_redis_fail
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                r = await client.get("/api/v1/predictions/status")
                # Не должно вернуть 500
                assert r.status_code == 200
                data = r.json()
                assert data["running_pipeline"] is False
        finally:
            app.dependency_overrides.clear()
