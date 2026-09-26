"""Tests for submission manifest (T-148a, F-021, clinerule 23).

RED phase: эти тесты должны ПАДАТЬ пока ml/transit_ai/submission/manifest.py не реализован.
GREEN phase: после реализации manifest.py все тесты зелёные.
"""

from __future__ import annotations

import json
from pathlib import Path

# ----- helpers --------------------------------------------------------------


def _write_dummy_csv(tmp_path: Path, csv_filename: str, rows: int = 14640) -> Path:
    """Создать фейковый submission CSV для тестов verify."""
    csv = tmp_path / csv_filename
    csv.write_text(
        "route;date;hour;prediction\n"
        + "\n".join(
            f"{r % 50 + 1};2025-11-{(r % 30) + 1:02d};{r % 24};1.5" for r in range(rows)
        )
    )
    return csv


# ----- write_manifest() -----------------------------------------------------


def test_write_manifest_creates_json_file(tmp_path: Path) -> None:
    """GREEN-1: write_manifest создаёт .json с basename = basename CSV."""
    from transit_ai.submission.manifest import write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    out = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1820456.32,
        coefficients={"weather": 1.0, "event": 1.0, "season": 1.0},
        post_processing=["clip_negatives"],
        holdout_wape_score=0.8751,
        submission_id="v2-bias",
    )

    assert out.exists()
    assert out.name == csv_filename.replace(".csv", ".json")
    assert out.parent == tmp_path


def test_write_manifest_includes_required_fields(tmp_path: Path) -> None:
    """R2 clinerule 23: обязательные поля в манифесте."""
    from transit_ai.submission.manifest import write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    out = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1820456.32,
        coefficients={"weather": 1.0, "event": 1.0, "season": 1.0},
        post_processing=["clip_negatives"],
        holdout_wape_score=0.8751,
        submission_id="v2-bias",
    )

    d = json.loads(out.read_text())
    required = {
        "submission_id",
        "csv_filename",
        "generated_at",
        "git_commit",
        "git_branch",
        "data_source",
        "model_id",
        "model_uri",
        "train_date_range",
        "submission_date_range",
        "row_count",
        "expected_rows",
        "total_predictions_sum",
        "coefficients",
        "post_processing",
        "platform_submitted",
        "platform_score",
        "platform_score_submitted_at",
        "holdout_wape_score",
    }
    missing = required - set(d.keys())
    assert not missing, f"missing required fields: {missing}"

    assert d["submission_id"] == "v2-bias"
    assert d["model_id"] == "x_v1"
    assert d["train_date_range"] == ["2025-01-01", "2025-08-31"]
    assert d["submission_date_range"] == ["2025-11-01", "2025-12-31"]
    assert d["row_count"] == 14640
    assert d["expected_rows"] == 14640
    assert d["coefficients"] == {"weather": 1.0, "event": 1.0, "season": 1.0}
    assert d["platform_submitted"] is False
    assert d["platform_score"] is None


def test_write_manifest_filename_has_three_ids_r1(tmp_path: Path) -> None:
    """R1 clinerule 23: csv_filename обязан содержать все 3 идентификатора."""
    from transit_ai.submission.manifest import write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    out = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )
    d = json.loads(out.read_text())
    fname = d["csv_filename"]

    # date-range: start_YYYYMMDD + end_YYYYMMDD (между ними _)
    assert "_20251101_20251231_" in fname, f"missing date range in {fname}"
    # run-ts: ISO compact YYYYMMDDTHHMMSSZ
    assert "T184500Z.csv" in fname, f"missing run_ts in {fname}"
    # model_id
    assert fname.startswith("submission_x_v1_"), f"missing model_id in {fname}"


def test_write_manifest_default_submission_id_is_model_id(tmp_path: Path) -> None:
    """R5: без submission_id используется model_id."""
    from transit_ai.submission.manifest import write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    out = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )
    d = json.loads(out.read_text())
    assert d["submission_id"] == "x_v1", "default submission_id must equal model_id"


# ----- verify_manifest() ----------------------------------------------------


def test_verify_manifest_passes_on_consistent(tmp_path: Path) -> None:
    """R4: verify возвращает 0 когда manifest соответствует CSV."""
    from transit_ai.submission.manifest import verify_manifest, write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    csv = _write_dummy_csv(tmp_path, csv_filename, rows=14640)
    manifest_path = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )

    rc = verify_manifest(manifest_path=manifest_path, csv_path=csv)
    assert rc == 0, "consistent manifest must verify cleanly"


def test_verify_manifest_fails_on_missing_json(tmp_path: Path) -> None:
    """R4: verify возвращает non-zero если manifest.json отсутствует."""
    from transit_ai.submission.manifest import verify_manifest

    csv = _write_dummy_csv(tmp_path, "submission_x_v1.csv")
    rc = verify_manifest(manifest_path=tmp_path / "submission_x_v1.json", csv_path=csv)
    assert rc != 0


def test_verify_manifest_fails_on_row_count_mismatch(tmp_path: Path) -> None:
    """R4: verify падает если row_count не совпадает с реальным CSV."""
    from transit_ai.submission.manifest import verify_manifest, write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    csv = _write_dummy_csv(tmp_path, csv_filename, rows=100)
    # в manifest заявлено 14640 строк, в CSV — 100
    manifest_path = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )
    rc = verify_manifest(manifest_path=manifest_path, csv_path=csv)
    assert rc != 0, "row_count mismatch must fail verification"


def test_verify_manifest_fails_on_wrong_csv_filename(tmp_path: Path) -> None:
    """R4: verify падает если в manifest указан другой csv_filename."""
    from transit_ai.submission.manifest import verify_manifest, write_manifest

    csv_filename_a = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    csv_a = _write_dummy_csv(tmp_path, csv_filename_a, rows=14640)
    # manifest утверждает другой файл
    manifest_path = write_manifest(
        out_dir=tmp_path,
        csv_filename="submission_other_20251101_20251231_20260925T184500Z.csv",
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )
    rc = verify_manifest(manifest_path=manifest_path, csv_path=csv_a)
    assert rc != 0


# ----- verify_manifest() negative/corner cases (R4 coverage) ----------------


def test_verify_manifest_fails_on_missing_csv(tmp_path: Path) -> None:
    """R4 negative: verify падает если csv_path не существует."""
    from transit_ai.submission.manifest import verify_manifest, write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    # Создаём manifest, но НЕ создаём CSV
    manifest_path = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14640,
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )
    csv_path = tmp_path / csv_filename  # НЕ создаём
    rc = verify_manifest(manifest_path=manifest_path, csv_path=csv_path)
    assert rc != 0, "missing CSV must fail verification"


def test_verify_manifest_fails_on_malformed_json(tmp_path: Path) -> None:
    """R4 negative: verify падает если manifest.json — невалидный JSON."""
    from transit_ai.submission.manifest import verify_manifest

    csv_filename = "submission_x_v1.csv"
    csv = _write_dummy_csv(tmp_path, csv_filename)
    manifest_path = tmp_path / csv_filename.replace(".csv", ".json")
    manifest_path.write_text("{not valid json, missing quote")

    rc = verify_manifest(manifest_path=manifest_path, csv_path=csv)
    assert rc != 0, "malformed JSON must fail verification"


def test_verify_manifest_fails_on_expected_rows_mismatch(tmp_path: Path) -> None:
    """R4 negative: verify падает если expected_rows != row_count (drift detect)."""
    from transit_ai.submission.manifest import verify_manifest, write_manifest

    csv_filename = "submission_x_v1_20251101_20251231_20260925T184500Z.csv"
    csv = _write_dummy_csv(tmp_path, csv_filename, rows=14640)
    # manifest говорит row_count=14640, но expected_rows=14000 → drift
    manifest_path = write_manifest(
        out_dir=tmp_path,
        csv_filename=csv_filename,
        model_id="x_v1",
        model_uri="ml/artifacts/x_v1/model.pkl",
        train_range=("2025-01-01", "2025-08-31"),
        sub_range=("2025-11-01", "2025-12-31"),
        row_count=14640,
        expected_rows=14000,  # drift
        total_predictions=1.0,
        coefficients={},
        post_processing=[],
    )
    rc = verify_manifest(manifest_path=manifest_path, csv_path=csv)
    assert rc != 0, "expected_rows != row_count must fail verification"


def test_dataset_hash_returns_hex_for_empty_list(tmp_path: Path) -> None:
    """Corner case: dataset_hash на пустом списке возвращает валидный hex (не падает)."""
    from transit_ai.submission.manifest import dataset_hash

    result = dataset_hash([])
    assert isinstance(result, str)
    assert len(result) == 16  # hex sha256 truncated to 16 chars
    # Пустой sha256 начинается с consistent pattern
    assert all(c in "0123456789abcdef" for c in result)


def test_dataset_hash_changes_with_different_files(tmp_path: Path) -> None:
    """Corner case: dataset_hash разный для разных файлов (sanity)."""
    from transit_ai.submission.manifest import dataset_hash

    f1 = tmp_path / "a.csv"
    f1.write_text("a,b\n1,2\n")
    f2 = tmp_path / "b.csv"
    f2.write_text("a,b\n3,4\n")

    h1 = dataset_hash([f1])
    h2 = dataset_hash([f2])
    h_combo = dataset_hash([f1, f2])
    assert h1 != h2
    assert h_combo not in (h1, h2)


def test_git_commit_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Corner case: git_commit возвращает string даже без .git repo."""
    from transit_ai.submission.manifest import git_commit

    result = git_commit()
    assert isinstance(result, str)
    assert len(result) > 0


def test_git_branch_returns_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Corner case: git_branch возвращает string даже без .git repo."""
    from transit_ai.submission.manifest import git_branch

    result = git_branch()
    assert isinstance(result, str)
    assert len(result) > 0
