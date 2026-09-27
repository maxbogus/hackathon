"""T-230: active/etalon switching + candidate ingest (service + API).

RED→GREEN: сначала проверяем инварианты сервиса, затем end-to-end через API:
  - validate_candidate (clinerule 23 R4) отклоняет мусор;
  - ingest → activate НЕ удваивает строки при чтении;
  - restore-etalon возвращает эталон;
  - /predictions/regenerate создаёт run (Celery замокан);
  - /predictions/runs/{id} переводит run в ready по Celery SUCCESS.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db import get_db
from app.main import create_app
from app.models import Base, Prediction, PredictionRun
from app.predictions_active import (
    build_recommendation,
    infer_model_kind,
    validate_candidate,
)

SUBMISSION_ID = "ui-test"
CSV_NAME = "submission_xgboost_v_ui_test_20251101_20251231_20260927T000000Z.csv"


def _write_candidate(
    directory: Path,
    *,
    rows: int = 4,
    expected_rows: int | None = None,
    holdout: float = 0.87,
    csv_name: str = CSV_NAME,
    submission_id: str = SUBMISSION_ID,
    route_id: int = 7,
) -> tuple[Path, Path]:
    """Создаёт CSV+manifest кандидата по контракту clinerule 23."""
    csv_path = directory / csv_name
    lines = ["route;date;hour;prediction"]
    for i in range(rows):
        lines.append(f"{route_id};2025-11-01;{i};{10.0 + i}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest_path = csv_path.with_suffix(".json")
    manifest_path.write_text(
        json.dumps(
            {
                "submission_id": submission_id,
                "csv_filename": csv_name,
                "model_id": "xgboost_v_ui_test",
                "model_uri": "ml/artifacts/xgboost_v_ui_test/model.pkl",
                "row_count": rows,
                "expected_rows": expected_rows if expected_rows is not None else rows,
                "holdout_wape_score": holdout,
                "coefficients": {"weather": 1.0, "event": 1.0, "season": 1.0},
                "git_commit": "deadbee",
            }
        ),
        encoding="utf-8",
    )
    return csv_path, manifest_path


class TestValidateCandidate:
    """clinerule 23 R4: что можно ingest'ить, а что нет."""

    def test_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "predictions_dir", tmp_path)
        csv_path, manifest_path = _write_candidate(tmp_path)
        check = validate_candidate(csv_path, manifest_path)
        assert check.ok
        assert check.row_count == 4
        assert check.holdout_wape_score == pytest.approx(0.87)

    def test_rejects_path_outside_predictions_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "predictions_dir", tmp_path / "inside")
        csv_path, manifest_path = _write_candidate(tmp_path)
        check = validate_candidate(csv_path, manifest_path)
        assert not check.ok
        assert "outside predictions_dir" in check.reason

    def test_rejects_missing_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "predictions_dir", tmp_path)
        csv_path, _ = _write_candidate(tmp_path)
        check = validate_candidate(csv_path, None)
        assert not check.ok
        assert "manifest not found" in check.reason

    def test_needs_fix_on_expected_rows_drift(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "predictions_dir", tmp_path)
        csv_path, manifest_path = _write_candidate(
            tmp_path, rows=4, expected_rows=14640
        )
        check = validate_candidate(csv_path, manifest_path)
        assert not check.ok
        assert "NEEDS_FIX" in check.reason


class TestRecommendation:
    """clinerule 24 R3: порог 0.005, WAPE-score: больше = лучше."""

    @pytest.mark.parametrize(
        ("candidate", "active", "expected"),
        [
            (None, 0.87, "READY_TO_UPLOAD"),
            (0.87, None, "READY_TO_UPLOAD"),
            (0.90, 0.87, "READY_TO_UPLOAD"),
            (0.80, 0.87, "WORSE_THAN_PREVIOUS"),
            (0.8712, 0.87, "IDENTICAL_TO_PREVIOUS"),
        ],
    )
    def test_thresholds(self, candidate, active, expected) -> None:
        assert build_recommendation(candidate, active) == expected

    @pytest.mark.parametrize(
        ("model_id", "kind"),
        [
            ("xgboost_v_ui_test", "xgboost"),
            ("catboost_v1", "catboost"),
            ("gru_v1", "gru"),
            ("hybrid_v1", "hybrid"),
            ("test_submission_baseline", "baseline"),
        ],
    )
    def test_infer_model_kind(self, model_id, kind) -> None:
        assert infer_model_kind(model_id) == kind


# ─────────────────────────── API: ingest / swap ─────────────────────────


def _seed_etalon(factory) -> None:
    """Эталон: 2 строки + etalon-run (как seed_predictions + миграция)."""

    async def run() -> None:
        async with factory() as s:
            for hour in (8, 9):
                s.add(
                    Prediction(
                        route_id=7,
                        period_start=datetime(2025, 11, 1, hour, tzinfo=UTC),
                        period_end=datetime(2025, 11, 1, hour + 1, tzinfo=UTC),
                        horizon="day",
                        granularity="hour",
                        value=100.0 + hour,
                        model_id="test_submission_baseline",
                        model_kind="baseline",
                        model_version="v0.0.1",
                        feature_set="with_all",
                        feature_flags={},
                        zeros_applied=True,
                        zero_config={},
                        coef_weather=1.0,
                        coef_event=1.0,
                        coef_season=1.0,
                        submission_id="seed-test-submission",
                        is_active=True,
                        is_etalon=True,
                    )
                )
            s.add(
                PredictionRun(
                    celery_task_id="seed-etalon-test",
                    task_name="seed.etalon",
                    status="loaded",
                    submission_id="seed-test-submission",
                    model_id="test_submission_baseline",
                    feature_set="with_all",
                    params={},
                    row_count=2,
                    holdout_wape_score=0.8751,
                    is_etalon=True,
                )
            )
            await s.commit()

    asyncio.run(run())


def _create_ready_run(factory, tmp_path: Path) -> int:
    """Создаёт run со статусом ready + CSV кандидата. Returns run_id."""
    csv_path, manifest_path = _write_candidate(tmp_path, rows=3, holdout=0.90)
    holder: dict[str, int] = {}

    async def run() -> None:
        async with factory() as s:
            row = PredictionRun(
                celery_task_id="task-ingest-1",
                task_name="ml_pipeline.predict_window",
                status="ready",
                submission_id=SUBMISSION_ID,
                model_id="xgboost_v_ui_test",
                feature_set="with_all",
                pipeline_kind="predict",
                row_count=3,
                holdout_wape_score=0.90,
                csv_path=str(csv_path),
                manifest_path=str(manifest_path),
                params={
                    "feature_set": "with_all",
                    "zeros_applied": True,
                    "feature_flags": {"use_poi": True},
                    "zero_config": {"zero_route_5": {}},
                    "coef_weather": 1.0,
                    "coef_event": 1.0,
                    "coef_season": 1.0,
                },
            )
            s.add(row)
            await s.commit()
            await s.refresh(row)
            holder["run_id"] = row.id

    asyncio.run(run())
    return holder["run_id"]


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """(client, tmp_path, factory) с seed-эталоном и in-memory БД."""
    monkeypatch.setattr(settings, "predictions_dir", tmp_path)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}
    )

    async def init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    _seed_etalon(factory)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), tmp_path, factory


PERIOD = {"from": "2025-11-01T00:00:00", "to": "2025-11-02T00:00:00"}


class TestApiSwap:
    """Подмена набора: активация, отсутствие дублей, возврат эталона."""

    def test_active_set_is_etalon(self, api) -> None:
        client, _, _ = api
        r = client.get("/api/v1/predictions/active")
        assert r.status_code == 200
        data = r.json()
        assert data["submission_id"] == "seed-test-submission"
        assert data["is_etalon"] is True
        assert data["row_count"] == 2

    def test_ingest_activate_does_not_duplicate_rows(self, api) -> None:
        client, tmp_path, factory = api
        run_id = _create_ready_run(factory, tmp_path)

        r = client.post(
            f"/api/v1/predictions/runs/{run_id}/ingest", json={"activate": True}
        )
        assert r.status_code == 200, r.text
        assert r.json()["rows"] == 3

        points = client.get("/api/v1/predictions/db/7", params=PERIOD).json()["points"]
        # 3 (кандидат), а НЕ 5 (кандидат+эталон) — иначе дубли на каждый timestamp
        assert len(points) == 3

        active = client.get("/api/v1/predictions/active").json()
        assert active["submission_id"] == SUBMISSION_ID
        assert active["model_id"] == "xgboost_v_ui_test"
        assert active["is_etalon"] is False
        assert active["row_count"] == 3

    def test_ingest_twice_conflicts(self, api) -> None:
        client, tmp_path, factory = api
        run_id = _create_ready_run(factory, tmp_path)
        first = client.post(
            f"/api/v1/predictions/runs/{run_id}/ingest", json={"activate": True}
        )
        assert first.status_code == 200
        second = client.post(
            f"/api/v1/predictions/runs/{run_id}/ingest", json={"activate": True}
        )
        assert second.status_code == 409

    def test_ingest_before_ready_conflicts(self, api) -> None:
        client, tmp_path, factory = api
        run_id = _create_ready_run(factory, tmp_path)

        async def mark_running() -> None:
            async with factory() as s:
                row = await s.get(PredictionRun, run_id)
                row.status = "running"
                await s.commit()

        asyncio.run(mark_running())
        r = client.post(
            f"/api/v1/predictions/runs/{run_id}/ingest", json={"activate": True}
        )
        assert r.status_code == 409

    def test_restore_etalon_after_activate(self, api) -> None:
        client, tmp_path, factory = api
        run_id = _create_ready_run(factory, tmp_path)
        client.post(
            f"/api/v1/predictions/runs/{run_id}/ingest", json={"activate": True}
        )

        r = client.post("/api/v1/predictions/restore-etalon")
        assert r.status_code == 200, r.text
        assert r.json()["active_submission_id"] == "seed-test-submission"

        points = client.get("/api/v1/predictions/db/7", params=PERIOD).json()["points"]
        assert len(points) == 2
        active = client.get("/api/v1/predictions/active").json()
        assert active["model_id"] == "test_submission_baseline"
        assert active["is_etalon"] is True

    def test_reject_keeps_active_set(self, api) -> None:
        client, tmp_path, factory = api
        run_id = _create_ready_run(factory, tmp_path)
        r = client.post(f"/api/v1/predictions/runs/{run_id}/reject")
        assert r.status_code == 200
        assert r.json()["active_submission_id"] == "seed-test-submission"
        assert client.get("/api/v1/predictions/active").json()["row_count"] == 2

    def test_load_endpoint_uses_active_set(self, api) -> None:
        """PassengerMode (/predictions/load) тоже следует за активным набором."""
        client, tmp_path, factory = api
        run_id = _create_ready_run(factory, tmp_path)
        client.post(
            f"/api/v1/predictions/runs/{run_id}/ingest", json={"activate": True}
        )
        r = client.get("/api/v1/predictions/load")
        assert r.status_code == 200, r.text
        loads = r.json()["loads"]
        assert len(loads) == 1
        assert loads[0]["route_id"] == 7
        assert loads[0]["sample_size"] == 3


class TestApiRegenerate:
    """Celery-запуск генерации + перевод run в ready по SUCCESS."""

    def _mock_celery(self, task_id: str) -> MagicMock:
        mock_celery = MagicMock()
        mock_result = MagicMock()
        mock_result.id = task_id
        mock_celery.send_task.return_value = mock_result
        return mock_celery

    def test_regenerate_creates_run_with_params(self, api) -> None:
        client, _, _ = api
        with patch("app.api.predictions_runs._get_celery_app") as mock_get:
            mock_get.return_value = self._mock_celery("task-regen-1")
            r = client.post(
                "/api/v1/predictions/regenerate",
                json={"coef_weather": 1.2, "coef_event": 1.0, "coef_season": 1.0},
            )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["task_id"] == "task-regen-1"
        assert body["submission_id"].startswith("ui-")

        _args, kwargs = mock_get.return_value.send_task.call_args
        assert kwargs["kwargs"]["coef_weather"] == pytest.approx(1.2)
        assert kwargs["kwargs"]["submission_id"] == body["submission_id"]
        assert "feature_flags" in kwargs["kwargs"]

        runs = client.get("/api/v1/predictions/runs").json()["runs"]
        assert runs[0]["submission_id"] == body["submission_id"]
        assert runs[0]["status"] == "running"
        assert runs[0]["is_active"] is False

    def test_regenerate_503_when_celery_down(self, api) -> None:
        client, _, _ = api
        with patch(
            "app.api.predictions_runs._get_celery_app",
            side_effect=OSError("no broker"),
        ):
            r = client.post("/api/v1/predictions/regenerate", json={})
        assert r.status_code == 503
        assert "Celery" in r.json()["detail"]

    def test_status_ready_on_celery_success(self, api) -> None:
        client, tmp_path, _ = api
        with patch("app.api.predictions_runs._get_celery_app") as mock_get:
            mock_get.return_value = self._mock_celery("task-regen-2")
            body = client.post("/api/v1/predictions/regenerate", json={}).json()

        _write_candidate(
            tmp_path, rows=5, holdout=0.93, submission_id=body["submission_id"]
        )
        with patch(
            "app.api.predictions_runs._celery_status", return_value=("SUCCESS", None)
        ):
            r = client.get(f"/api/v1/predictions/runs/{body['run_id']}")

        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "ready"
        assert data["row_count"] == 5
        assert data["holdout_wape_score"] == pytest.approx(0.93)
        # 0.93 > 0.8751 (эталон) → лучше
        assert data["recommendation"] == "READY_TO_UPLOAD"
        assert data["csv_filename"]

    def test_status_failed_when_manifest_missing(self, api) -> None:
        client, _, _ = api
        with patch("app.api.predictions_runs._get_celery_app") as mock_get:
            mock_get.return_value = self._mock_celery("task-regen-3")
            body = client.post("/api/v1/predictions/regenerate", json={}).json()

        with patch(
            "app.api.predictions_runs._celery_status", return_value=("SUCCESS", None)
        ):
            r = client.get(f"/api/v1/predictions/runs/{body['run_id']}")

        assert r.status_code == 200
        assert r.json()["status"] == "failed"
        assert client.get("/api/v1/predictions/active").json()["row_count"] == 2

    def test_unknown_run_returns_404(self, api) -> None:
        client, _, _ = api
        assert client.get("/api/v1/predictions/runs/9999").status_code == 404
