"""Root conftest: resolves `tests` package shadow conflict.

Проблема: pytest использует `rootdir` (=hackathon) как стартовую точку sys.path.
Когда задано несколько `apps/*/tests/`, pytest пытается резолвить каждый как
пакет `tests`, что вызывает `ModuleNotFoundError: No module named 'tests.test_X'`.

Решения:
  1. Не добавляем корневую `tests/` директорию (см. testpaths в pyproject.toml).
  2. При запуске pytest с apps/*/tests/ не используем `--rootdir=`.
  3. Этот conftest гарантирует, что apps/*/ доступны как топ-уровневые пакеты.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root → `apps.*`, `ml.*` импортируются
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Убираем корневую `tests/` если она в sys.path — она shadow'ит `apps/*/tests/`
ROOT_TESTS = ROOT / "tests"
if str(ROOT_TESTS) in sys.path:
    sys.path.remove(str(ROOT_TESTS))
