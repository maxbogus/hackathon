"""T-229: маппинг UI-параметров (тогглы/zeros/coefs) → CLI ML-скриптов.

RED→GREEN: проверяем чистые функции без Celery/DB.
"""

from __future__ import annotations

from pathlib import Path

from app.ml_cli import (
    build_flags_payload,
    build_predict_args,
    build_zero_args,
    write_flags_file,
)
import pytest
import yaml


class TestBuildFlagsPayload:
    """DB feature_toggles → ml/transit_ai/config/flags.yaml."""

    def test_maps_known_toggles(self) -> None:
        payload = build_flags_payload({"use_poi": True, "use_seasonal": False, "use_traffic": True})
        assert payload == {
            "features": {
                "use_poi_features": True,
                "use_seasonal_calendar": False,
                "use_traffic": True,
            }
        }

    def test_use_lag_has_no_ml_flag(self) -> None:
        """use_lag не влияет на генерацию (lag встроен в xgboost_route, F-020)."""
        assert build_flags_payload({"use_lag": True}) is None

    @pytest.mark.parametrize("empty", [None, {}])
    def test_empty_returns_none(self, empty) -> None:
        """Пусто → None, чтобы make_submission взял defaults.yaml."""
        assert build_flags_payload(empty) is None


class TestBuildZeroArgs:
    """zero_overrides → CLI-аргументы make_submission.py."""

    def test_route_5(self) -> None:
        assert build_zero_args({"zero_route_5": {"route_id": 5}}) == [
            "--zero-route",
            "5",
        ]

    def test_night_pred_cap_with_hours(self) -> None:
        args = build_zero_args({"zero_night_pred_cap": {"pred_cap": 55, "hours": [0, 1, 2, 3, 4]}})
        assert args == ["--pred-cap", "55", "--cap-hours", "0", "1", "2", "3", "4"]

    def test_night_pred_cap_default_hours(self) -> None:
        args = build_zero_args({"zero_night_pred_cap": {"pred_cap": 30}})
        assert args[:2] == ["--pred-cap", "30"]
        assert args[2] == "--cap-hours"
        assert args[3:] == ["0", "1", "2", "3", "4"]

    def test_weekend_and_holidays(self) -> None:
        args = build_zero_args({"zero_weekend": {}, "zero_holidays": {}})
        assert "--zero-weekends" in args
        assert "--zero-holidays" in args

    def test_all_together(self) -> None:
        args = build_zero_args(
            {
                "zero_route_5": {},
                "zero_night_pred_cap": {"pred_cap": 55, "hours": [0, 1]},
                "zero_weekend": {},
                "zero_holidays": {},
            }
        )
        assert args == [
            "--zero-route",
            "5",
            "--pred-cap",
            "55",
            "--cap-hours",
            "0",
            "1",
            "--zero-weekends",
            "--zero-holidays",
        ]

    @pytest.mark.parametrize("empty", [None, {}])
    def test_empty_returns_no_args(self, empty) -> None:
        assert build_zero_args(empty) == []


class TestBuildPredictArgs:
    def test_core_args(self) -> None:
        args = build_predict_args(
            model_id="xgboost_v_ui",
            start_date="2025-11-01",
            end_date="2025-12-31",
            submission_id="ui-1",
            coef_weather=1.2,
            coef_event=1.0,
            coef_season=0.9,
        )
        assert args == [
            "--model-id",
            "xgboost_v_ui",
            "--model-kind",
            "xgboost_route",
            "--start-date",
            "20251101",
            "--end-date",
            "20251231",
            "--coef-weather",
            "1.2",
            "--coef-event",
            "1.0",
            "--coef-season",
            "0.9",
            "--submission-id",
            "ui-1",
        ]

    def test_flags_and_zero_args_appended(self, tmp_path: Path) -> None:
        flags = tmp_path / "flags.yaml"
        args = build_predict_args(
            model_id="m",
            start_date="2025-11-01",
            end_date="2025-11-02",
            submission_id=None,
            coef_weather=1.0,
            coef_event=1.0,
            coef_season=1.0,
            model_kind="route_baseline",
            flags_file=flags,
            zero_args=["--zero-route", "5"],
        )
        assert "--flags-file" in args
        assert args[args.index("--flags-file") + 1] == str(flags)
        assert args[-2:] == ["--zero-route", "5"]
        assert "--submission-id" not in args


class TestWriteFlagsFile:
    def test_writes_yaml_and_creates_dir(self, tmp_path: Path) -> None:
        path = write_flags_file(
            tmp_path / "nested" / "flags.yaml", {"features": {"use_poi_features": False}}
        )
        assert path.exists()
        assert yaml.safe_load(path.read_text()) == {"features": {"use_poi_features": False}}
