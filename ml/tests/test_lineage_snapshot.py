"""Tests for transit_ai.lineage.snapshot — git-trackable manifest датасетов.

Snapshot: {path, size_bytes, mtime_ns, sha256, rows, schema_hint?, captured_at}.
Пишется в docs/lineage/datasets/<name>.json (коммитится в git, поэтому маленький).

Запуск: uv run pytest ml/tests/test_lineage_snapshot.py -q
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


from transit_ai.lineage import snapshot as ls


def _write_csv(p: Path, body: bytes) -> Path:
    p.write_bytes(body)
    return p


def test_capture_returns_required_fields(tmp_path: Path) -> None:
    """Snapshot содержит sha256, size, mtime, rows, captured_at.

    Дефолт skip_header=True для CSV: 1 header + 2 data = rows=2.
    С skip_header=False: rows=3 (считаем все строки).
    """
    csv = _write_csv(tmp_path / "train.csv", b"a;b;c\n1;2;3\n4;5;6\n")

    snap = ls.capture(csv)  # skip_header=True по умолчанию
    assert snap.path == str(csv)
    assert snap.size_bytes == csv.stat().st_size
    assert snap.sha256  # non-empty
    assert len(snap.sha256) == 64
    assert snap.rows == 2  # 2 data-строки без header
    assert snap.captured_at  # ISO timestamp
    # Парсится как ISO
    datetime.fromisoformat(snap.captured_at)


def test_capture_counts_data_rows_excluding_header(tmp_path: Path) -> None:
    """rows = число data-строк (без header). train.csv имеет 49M+1 строк (header + 49M data)."""
    csv = _write_csv(tmp_path / "x.csv", b"h1;h2\n1;2\n3;4\n5;6\n")  # 1 header + 3 data
    snap = ls.capture(csv, skip_header=True)
    assert snap.rows == 3

    csv2 = _write_csv(tmp_path / "y.csv", b"h1\n1\n2\n3\n")
    snap2 = ls.capture(csv2, skip_header=True)
    assert snap2.rows == 3


def test_snapshot_is_serializable_to_json(tmp_path: Path) -> None:
    """Snapshot сериализуется в JSON без кастомных энкодеров."""
    csv = _write_csv(tmp_path / "z.csv", b"h\n1\n")
    snap = ls.capture(csv, skip_header=True)
    blob = snap.to_json()
    parsed = json.loads(blob)
    assert parsed["sha256"] == snap.sha256
    assert parsed["rows"] == 1


def test_write_to_path_creates_parent_dirs(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", b"h\n1\n")
    out = tmp_path / "nested" / "sub" / "manifest.json"
    snap = ls.capture(csv, skip_header=True)
    ls.write(snap, out)
    assert out.is_file()
    parsed = json.loads(out.read_text())
    assert parsed["sha256"] == snap.sha256


def test_read_roundtrip(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "data.csv", b"h\n1\n2\n")
    snap = ls.capture(csv, skip_header=True)
    out = tmp_path / "snap.json"
    ls.write(snap, out)
    loaded = ls.read(out)
    assert loaded.sha256 == snap.sha256
    assert loaded.rows == snap.rows
    assert loaded.size_bytes == snap.size_bytes


def test_diff_detects_changes(tmp_path: Path) -> None:
    """Diff: changed sha256 → changed; same sha256 → unchanged."""
    csv = _write_csv(tmp_path / "data.csv", b"h\n1\n")
    old = ls.capture(csv, skip_header=True)

    # Перезаписываем тем же содержимым → sha256 тот же
    csv.write_bytes(b"h\n1\n")
    new_same = ls.capture(csv, skip_header=True)
    assert ls.diff(old, new_same) == "unchanged"

    # Добавляем строку → sha256 другой
    csv.write_bytes(b"h\n1\n2\n")
    new_diff = ls.capture(csv, skip_header=True)
    assert ls.diff(old, new_diff) == "changed"


def test_snapshot_is_small_enough_for_git(tmp_path: Path) -> None:
    """Snapshot для 8 GB файла должен быть < 1 KB (git-trackable)."""
    # Создаём 50 MB файл (быстрее теста) — snapshot не должен расти с размером файла.
    big = tmp_path / "big.csv"
    big.write_bytes(b"h\n" + b"x\n" * (5 * 1024 * 1024))  # 50 MB+
    snap = ls.capture(big, skip_header=True)
    blob = snap.to_json()
    assert len(blob) < 1024, f"snapshot = {len(blob)} bytes (должен быть < 1KB)"


def test_captured_at_is_utc_iso8601(tmp_path: Path) -> None:
    csv = _write_csv(tmp_path / "x.csv", b"h\n1\n")
    snap = ls.capture(csv, skip_header=True)
    # Парсится и содержит timezone
    parsed = datetime.fromisoformat(snap.captured_at)
    assert parsed.tzinfo is not None
    # UTC (не локальное время)
    assert parsed.utcoffset().total_seconds() == 0
