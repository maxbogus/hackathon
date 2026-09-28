#!/usr/bin/env python3
"""Проверка сдаточного пакета `export/` (T-237).

Что делает:
1. Проверяет, что обязательные файлы пакета на месте.
2. Сверяет `export/checksums.sha256` (формат `sha256sum`) с фактическими хэшами.

Зачем: `export/README.md` обещал `make export-verify`, которого не существовало —
проверяющий запускал команду и получал `No rule to make target` (F-147).
Без этой проверки пакет можно отдать с устаревшими/битыми артефактами.

Запуск:
    make export-verify
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

EXPORT_DIR = Path("export")

REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "README_form.md",
    "checksums.sha256",
    "verification/verify_install.sh",
    "01-ml/artifacts_index.md",
    "02-external-data/normalized/manifest.json",
    "03-service/docker-compose.yml",
    "03-service/endpoints.md",
    "03-service/api/openapi.json",
    "04-architecture/schema.dbml",
    "04-architecture/MODEL_DOMAIN.md",
    "05-performance/load_profiles.md",
    "06-limitations-roadmap/BACKLOG.md",
    "06-limitations-roadmap/BUSINESS_VALUE.md",
)
"""Обязательные файлы пакета (по 6 пунктам формы — см. export/README.md)."""

EXCLUDED_FROM_CHECKSUMS: frozenset[str] = frozenset(
    {
        "checksums.sha256",
        # Создаётся при каждом прогоне `verify_install.sh` — не является
        # поставляемым артефактом, иначе пакет «ломается» после первой проверки.
        "verification/verification-report.txt",
    }
)
"""Файлы, которые не включаются в checksums.sha256 (генерируются при проверке)."""


def sha256_file(path: Path) -> str:
    """sha256 файла потоком (1 МБ) — без чтения целиком в память."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksums(path: Path) -> list[tuple[str, str]]:
    """Разобрать `sha256sum`-файл в список `(относительный путь, хэш)`."""
    entries: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, rel = parts
        if len(digest) != 64:
            continue
        entries.append((rel.lstrip("*").removeprefix("./"), digest))
    return entries


def check_required(export_dir: Path) -> list[str]:
    """Список отсутствующих обязательных файлов."""
    return [rel for rel in REQUIRED_FILES if not (export_dir / rel).is_file()]


def check_checksums(export_dir: Path) -> tuple[list[str], int]:
    """Сверить checksums.sha256 с фактом.

    Returns:
        (список расхождений, сколько записей проверено).
    """
    manifest = export_dir / "checksums.sha256"
    if not manifest.is_file():
        return ["checksums.sha256 отсутствует"], 0
    problems: list[str] = []
    entries = parse_checksums(manifest)
    for rel, expected in entries:
        target = export_dir / rel
        if not target.is_file():
            problems.append(f"нет файла: {rel}")
        elif sha256_file(target) != expected:
            problems.append(f"хэш не совпал: {rel}")
    return problems, len(entries)


def write_checksums(export_dir: Path) -> int:
    """Перегенерировать `checksums.sha256` по фактическому содержимому пакета.

    Returns:
        Число записанных записей.
    """
    lines: list[str] = []
    for path in sorted(export_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(export_dir).as_posix()
        if rel in EXCLUDED_FROM_CHECKSUMS or "__pycache__" in rel:
            continue
        lines.append(f"{sha256_file(path)}  ./{rel}")
    (export_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", default=str(EXPORT_DIR), help="каталог пакета")
    parser.add_argument("--write", action="store_true", help="перегенерировать checksums.sha256")
    args = parser.parse_args(argv)

    export_dir = Path(args.export_dir)
    if not export_dir.is_dir():
        print(f"FAIL  каталог {export_dir} не найден")
        return 1

    if args.write:
        written = write_checksums(export_dir)
        print(f"OK: checksums.sha256 перегенерирован ({written} файлов)")

    missing = check_required(export_dir)
    problems, checked = check_checksums(export_dir)

    for rel in missing:
        print(f"FAIL  обязательный файл отсутствует: {rel}")
    for problem in problems:
        print(f"FAIL  {problem}")

    if missing or problems:
        print(f"\nИТОГ: FAIL={len(missing) + len(problems)} (проверено хэшей: {checked})")
        return 1

    print(f"OK: обязательные файлы на месте ({len(REQUIRED_FILES)}), sha256 сверено ({checked})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
