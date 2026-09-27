"""Snapshot manifest: компактное описание файла данных для git.

Формат (JSON, коммитится в docs/lineage/datasets/<name>.json):
    {
      "path": "/abs/path/to/train.csv",
      "size_bytes": 8160068959,
      "mtime_ns": 1727000000000000000,
      "sha256": "ab12cd34...",
      "rows": 49051926,           # data rows, без header
      "skip_header": true,
      "captured_at": "2026-09-27T19:58:33+00:00"
    }

Snapshot НЕ зависит от содержимого файла — один и тот же JSON для одного и того же
содержимого. Используется в meta.json как `train_data_hash` (замена "pending").
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import json

from transit_ai.lineage.hashing import count_lines, streaming_sha256


@dataclass(frozen=True)
class Snapshot:
    """Манифест датасета. Маленький (≤1 KB даже для 8 GB файла)."""

    path: str
    size_bytes: int
    mtime_ns: int
    sha256: str
    rows: int
    captured_at: str
    skip_header: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)


def capture(path: str | Path, skip_header: bool = True) -> Snapshot:
    """Снять snapshot с файла: sha256 + size + mtime + rows (streaming).

    По умолчанию skip_header=True — для CSV с заголовком rows считаются без него.
    """
    target = Path(path).resolve()
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target}")

    stat = target.stat()
    sha = streaming_sha256(target)
    raw_lines = count_lines(target)

    # Если skip_header=True — вычитаем 1 строку (header).
    rows = max(0, raw_lines - 1) if skip_header and raw_lines > 0 else raw_lines

    return Snapshot(
        path=str(target),
        size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sha256=sha,
        rows=rows,
        captured_at=datetime.now(UTC).isoformat(),
        skip_header=skip_header,
    )


def write(snapshot: Snapshot, dest: str | Path) -> Path:
    """Сохранить snapshot в JSON-файл (коммитится в git)."""
    target = Path(dest)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(snapshot.to_json(), encoding="utf-8")
    return target


def read(source: str | Path) -> Snapshot:
    """Прочитать snapshot из JSON-файла."""
    target = Path(source)
    data = json.loads(target.read_text(encoding="utf-8"))
    return Snapshot(**data)


def diff(old: Snapshot, new: Snapshot) -> str:
    """Сравнить два snapshot-а: 'unchanged' если sha256 совпал, иначе 'changed'.

    Также возвращает 'changed' если size_bytes или rows изменились (на случай коллизий).
    """
    if (
        old.sha256 == new.sha256
        and old.size_bytes == new.size_bytes
        and old.rows == new.rows
    ):
        return "unchanged"
    return "changed"
