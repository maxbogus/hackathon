"""Валидация normalized-артефактов по JSON Schema (T-231, контракт-фёрст).

Схема лежит в `docs/schemas/external_dataset.schema.json`. Если схемы или
библиотеки `jsonschema` нет (например, в контейнере harvester), валидация
мягко пропускается — структурные проверки в `pipeline.verify()` остаются.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT

SCHEMA_DIR_RELATIVE = Path("docs") / "schemas"
DATASET_SCHEMA_NAME = "external_dataset.schema.json"


def schema_path(name: str = DATASET_SCHEMA_NAME, repo_root: Path | str | None = None) -> Path:
    """Путь к файлу схемы (по умолчанию — в корне репозитория)."""
    root = Path(repo_root) if repo_root else REPO_ROOT
    return root / SCHEMA_DIR_RELATIVE / name


def load_schema(
    name: str = DATASET_SCHEMA_NAME, repo_root: Path | str | None = None
) -> dict[str, Any] | None:
    """Прочитать схему; None, если файла нет."""
    path = schema_path(name, repo_root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def validate_payload(
    payload: dict[str, Any], source: str, repo_root: Path | str | None = None
) -> list[str]:
    """Ошибки схемы для артефакта источника (пустой список — всё ок)."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - контейнер без jsonschema
        return []

    schema = load_schema(repo_root=repo_root)
    if schema is None:
        return []

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    return [f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors]
