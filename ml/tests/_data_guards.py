"""Guards для тестов, требующих локальные данные организаторов.

На хакатоне датасет и справочники поставляются отдельно (data/ в .gitignore),
поэтому часть тестов физически не может пройти на машине без этих файлов.
Такие тесты должны СКИПАТЬСЯ, а не падать: иначе `make test` становится
негерметичным (красный на чистом клоне) — ровно то, что происходило с 20 тестами
до этого guard'а (см. ledger F-127).

Использование:

    from _data_guards import requires_spravochnik

    @requires_spravochnik
    def test_build_route_geo_features_returns_all_10_routes() -> None:
        ...
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Справочник организаторов: координаты остановок 5 маршрутов + user-routes.
# Нужен geo-фичам (ml/transit_ai/data/spravochnik_geo.py), а значит и всему
# fit/predict у route-моделей (XGBoost / CatBoost).
SPRAVOCHNIK_XLSX = (
    REPO_ROOT
    / "data"
    / "real"
    / "spravochniki"
    / "Хакатон_справочники_трамвай_10_маршрутов.xlsx"
)

requires_spravochnik = pytest.mark.skipif(
    not SPRAVOCHNIK_XLSX.exists(),
    reason=(
        "нет справочника организаторов "
        f"({SPRAVOCHNIK_XLSX.relative_to(REPO_ROOT)}) — данные вне git; "
        "положить файл и перезапустить (см. ledger F-127)"
    ),
)
