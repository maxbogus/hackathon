"""External ETL (шаг 0, T-231): raw → normalized JSON для обучения.

Пакет не делает сетевых вызовов: `builders` читают локальные raw-файлы и
пишут `data/external/normalized/*.json` + `manifest.json` (sha256 каждого
артефакта). Celery-таски `app.tasks.fetch_*` делегируют сюда.

Подмодули: `builders` (чистые builders), `pipeline` (сборка + verify),
`cli` (`python -m app.build`), `schema` (JSON Schema валидация).
"""

from __future__ import annotations

__all__ = ["builders", "cli", "pipeline", "schema"]

