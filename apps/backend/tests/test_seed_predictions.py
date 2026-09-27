"""Tests for T-198: seed_predictions script.

RED phase: пишем тесты ДО проверки реализации. Все тесты должны ПРОЙТИ
с уже написанной реализацией (это GREEN-проверка). Если какие-то падают
— значит в seed_predictions.py баг.

Покрывает:
  - Парсеры (_parse_route_id, _parse_int, _parse_float) — unit
  - aggregate_actuals_csv — fake CSV → dict
  - load_predictions_csv — формат test_submission.csv (separator=";")
  - Идемпотентность — skip если таблицы не пустые (через mock session)
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.scripts.seed_predictions import (
    _parse_float,
    _parse_int,
    _parse_route_id,
    aggregate_actuals_csv,
    load_predictions_csv,
)

# === Парсеры (unit) ===


class TestParseRouteId:
    """Парсит поле ngpt_route из train.csv ("25 трамвай" → 25)."""

    def test_typical_tram_route(self) -> None:
        assert _parse_route_id("25 трамвай") == 25

    def test_single_digit(self) -> None:
        assert _parse_route_id("7 автобус") == 7

    def test_just_number(self) -> None:
        assert _parse_route_id("42") == 42

    def test_with_leading_whitespace(self) -> None:
        assert _parse_route_id("  17 автобус") == 17

    def test_empty_string_returns_none(self) -> None:
        assert _parse_route_id("") is None

    def test_none_returns_none(self) -> None:
        assert _parse_route_id(None) is None

    def test_garbage_returns_none(self) -> None:
        assert _parse_route_id("трамвай") is None  # No digits
        assert _parse_route_id("abc") is None

    def test_negative_returns_none(self) -> None:
        # Не поддерживаем отрицательные route_id
        assert _parse_route_id("-5") is None


class TestParseInt:
    def test_normal(self) -> None:
        assert _parse_int("42") == 42

    def test_empty(self) -> None:
        assert _parse_int("") is None

    def test_none(self) -> None:
        assert _parse_int(None) is None

    def test_garbage(self) -> None:
        assert _parse_int("abc") is None


class TestParseFloat:
    def test_normal(self) -> None:
        assert _parse_float("3.14") == pytest.approx(3.14)

    def test_comma_decimal(self) -> None:
        # test_submission.csv может иметь запятую в зависимости от locale
        assert _parse_float("3,14") == pytest.approx(3.14)

    def test_empty(self) -> None:
        assert _parse_float("") is None

    def test_garbage(self) -> None:
        assert _parse_float("xyz") is None


# === aggregate_actuals_csv (integration с tmp файлами) ===


class TestAggregateActualsCsv:
    """Читает train.csv chunked → {(route_id, hour_start): count}."""

    def _write_csv(self, tmp_path: Path, rows: list[dict]) -> Path:
        path = tmp_path / "train.csv"
        cols = [
            "tran_no",
            "device_no",
            "tran_date_time",
            "begin_date_time",
            "input_date_time",
            "crd_hashcode",
            "validation_result",
            "tran_type_id",
            "place_id",
            "good_type",
            "pass_route",
            "ngpt_route",
            "bus_exit_no",
            "garage_number",
        ]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cols, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_basic_aggregation(self, tmp_path: Path) -> None:
        rows = [
            {
                "tran_no": "1",
                "device_no": "1",
                "tran_date_time": "2025-01-01 08:00:00",
                "begin_date_time": "2025-01-01 08:00:00",
                "input_date_time": "2025-01-01 08:00:00",
                "crd_hashcode": "a",
                "validation_result": "1",
                "tran_type_id": "52",
                "place_id": "1",
                "good_type": "30 дней",
                "pass_route": "НГПТ",
                "ngpt_route": "7 трамвай",
                "bus_exit_no": "1",
                "garage_number": "1",
            },
            {
                "tran_no": "2",
                "device_no": "1",
                "tran_date_time": "2025-01-01 08:15:00",
                "begin_date_time": "2025-01-01 08:00:00",
                "input_date_time": "2025-01-01 08:00:00",
                "crd_hashcode": "b",
                "validation_result": "1",
                "tran_type_id": "52",
                "place_id": "1",
                "good_type": "30 дней",
                "pass_route": "НГПТ",
                "ngpt_route": "7 трамвай",
                "bus_exit_no": "1",
                "garage_number": "1",
            },
        ]
        path = self._write_csv(tmp_path, rows)
        result = aggregate_actuals_csv(path)
        ts = datetime(2025, 1, 1, 8, 0, 0)
        assert result == {(7, ts): 2}

    def test_skip_invalid_validation(self, tmp_path: Path) -> None:
        rows = [
            {
                "tran_no": "1",
                "device_no": "1",
                "tran_date_time": "2025-01-01 08:00:00",
                "begin_date_time": "2025-01-01 08:00:00",
                "input_date_time": "2025-01-01 08:00:00",
                "crd_hashcode": "a",
                "validation_result": "0",  # FAILED validation
                "tran_type_id": "52",
                "place_id": "1",
                "good_type": "30 дней",
                "pass_route": "НГПТ",
                "ngpt_route": "7 трамвай",
                "bus_exit_no": "1",
                "garage_number": "1",
            },
        ]
        path = self._write_csv(tmp_path, rows)
        assert aggregate_actuals_csv(path) == {}

    def test_skip_non_ngpt(self, tmp_path: Path) -> None:
        rows = [
            {
                "tran_no": "1",
                "device_no": "1",
                "tran_date_time": "2025-01-01 08:00:00",
                "begin_date_time": "2025-01-01 08:00:00",
                "input_date_time": "2025-01-01 08:00:00",
                "crd_hashcode": "a",
                "validation_result": "1",
                "tran_type_id": "52",
                "place_id": "1",
                "good_type": "30 дней",
                "pass_route": "МЦК",  # Not НГПТ
                "ngpt_route": "7 трамвай",
                "bus_exit_no": "1",
                "garage_number": "1",
            },
        ]
        path = self._write_csv(tmp_path, rows)
        assert aggregate_actuals_csv(path) == {}

    def test_skip_unparseable_route(self, tmp_path: Path) -> None:
        rows = [
            {
                "tran_no": "1",
                "device_no": "1",
                "tran_date_time": "2025-01-01 08:00:00",
                "begin_date_time": "2025-01-01 08:00:00",
                "input_date_time": "2025-01-01 08:00:00",
                "crd_hashcode": "a",
                "validation_result": "1",
                "tran_type_id": "52",
                "place_id": "1",
                "good_type": "30 дней",
                "pass_route": "НГПТ",
                "ngpt_route": "трамвай",  # No digits!
                "bus_exit_no": "1",
                "garage_number": "1",
            },
        ]
        path = self._write_csv(tmp_path, rows)
        assert aggregate_actuals_csv(path) == {}

    def test_hour_bucketing(self, tmp_path: Path) -> None:
        # 08:15 и 08:45 → один bucket [08:00, 09:00)
        rows = []
        for minute in [15, 45]:
            rows.append(
                {
                    "tran_no": str(minute),
                    "device_no": "1",
                    "tran_date_time": f"2025-01-01 08:{minute}:00",
                    "begin_date_time": "2025-01-01 08:00:00",
                    "input_date_time": "2025-01-01 08:00:00",
                    "crd_hashcode": "a",
                    "validation_result": "1",
                    "tran_type_id": "52",
                    "place_id": "1",
                    "good_type": "30 дней",
                    "pass_route": "НГПТ",
                    "ngpt_route": "7 трамвай",
                    "bus_exit_no": "1",
                    "garage_number": "1",
                }
            )
        path = self._write_csv(tmp_path, rows)
        result = aggregate_actuals_csv(path)
        ts = datetime(2025, 1, 1, 8, 0, 0)
        assert result == {(7, ts): 2}

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert aggregate_actuals_csv(tmp_path / "nonexistent.csv") == {}


# === load_predictions_csv (test_submission формат) ===


class TestLoadPredictionsCsv:
    """Читает test_submission.csv (separator=";", route 5 = 0 cold start)."""

    def _write_csv(self, tmp_path: Path, rows: list[dict]) -> Path:
        path = tmp_path / "test_submission.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["route", "date", "hour", "prediction"], delimiter=";"
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_basic_load(self, tmp_path: Path) -> None:
        rows = [
            {"route": "7", "date": "2025-11-01", "hour": "8", "prediction": "42"},
            {"route": "7", "date": "2025-11-01", "hour": "9", "prediction": "55"},
        ]
        path = self._write_csv(tmp_path, rows)
        result = load_predictions_csv(path)
        assert len(result) == 2
        assert result[0]["route_id"] == 7
        assert result[0]["period_start"] == datetime(2025, 11, 1, 8, 0, tzinfo=UTC)
        assert result[0]["value"] == pytest.approx(42.0)
        assert result[1]["value"] == pytest.approx(55.0)

    def test_route_5_zero(self, tmp_path: Path) -> None:
        # F-051 cold start: route 5 = 0 всегда
        rows = [
            {"route": "5", "date": "2025-11-01", "hour": "8", "prediction": "0"},
        ]
        path = self._write_csv(tmp_path, rows)
        result = load_predictions_csv(path)
        assert result[0]["route_id"] == 5
        assert result[0]["value"] == 0.0

    def test_separator_is_semicolon(self, tmp_path: Path) -> None:
        # Если separator="," (а не ";"), DictReader прочитает одну колонку.
        # Тест: создаём CSV с "," → должно вернуть пустой список (skip).
        path = tmp_path / "wrong_sep.csv"
        with path.open("w") as f:
            f.write("route,date,hour,prediction\n")
            f.write("7,2025-11-01,8,42\n")
        result = load_predictions_csv(path)
        assert result == []

    def test_skip_malformed_rows(self, tmp_path: Path) -> None:
        rows = [
            {"route": "7", "date": "2025-11-01", "hour": "8", "prediction": "42"},
            {"route": "abc", "date": "2025-11-01", "hour": "8", "prediction": "42"},
            {"route": "7", "date": "bad", "hour": "8", "prediction": "42"},
            {"route": "7", "date": "2025-11-01", "hour": "8", "prediction": ""},
        ]
        path = self._write_csv(tmp_path, rows)
        result = load_predictions_csv(path)
        assert len(result) == 1
        assert result[0]["route_id"] == 7

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert load_predictions_csv(tmp_path / "nonexistent.csv") == []


# === Идемпотентность (mock session) ===


class TestSeedIdempotency:
    """Проверяет что seed skip если таблица уже заполнена."""

    @pytest.mark.asyncio
    async def test_actuals_skip_when_table_not_empty(self) -> None:
        from app.scripts.seed_predictions import _seed_actuals

        # Mock session: count_actuals returns 100
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar=MagicMock(return_value=100))
        )
        # Если бы seed реально пытался INSERT, мы бы провалили тест.
        # Но _seed_actuals должен skip и вернуть 0.

        result = await _seed_actuals(
            mock_session, Path("/nonexistent"), 50_000, dry_run=True
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_predictions_skip_when_table_not_empty(self) -> None:
        from app.scripts.seed_predictions import _seed_predictions

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar=MagicMock(return_value=14640))
        )
        result = await _seed_predictions(
            mock_session, Path("/nonexistent"), dry_run=True
        )
        assert result == 0
