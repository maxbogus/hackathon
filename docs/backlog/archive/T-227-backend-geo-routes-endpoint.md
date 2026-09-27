---
id: T-227
phase: 1
title: "backend: GET /api/v1/geo/routes — остановки маршрутов для карты"
priority: P1
effort: 2
unit: hours
rice:
  R: 6
  I: 2.0
  C: 0.9
  score: 5.4
depends_on: []
blocks: [T-122]
tags: [backend, api, map, geo]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: "boguslavsky"
---

# T-227: backend — гео-каталог остановок для карты маршрутов

## Context

ТЗ §3.1.4 требует карту Москвы с остановками и маршрутами, окрашенными по прогнозируемой
загрузке. Геометрия в проекте уже есть — `data/external/stops_routes.json`
(10 маршрутов, 142 остановки, пользовательская разметка T-168), но:

- фронт не читает `data/` напрямую (clinerule 02: только контракт через OpenAPI → Orval);
- в OpenAPI не было ни одного гео-эндпоинта (только прогнозы/история/alerts);
- `app/data/transit.py:STOP_ROUTES` — 4 мок-остановки без координат (для ETA-демо),
  для карты не годится.

T-122 (карта) зависит от этого контракта — поэтому «блокирующий» тикет сделан первым
(contract-first).

## Acceptance Criteria

- [x] `GET /api/v1/geo/routes` отдаёт `routes[]` (`route_id`, `n_stops`, `stops[]`), `count`, `source`
- [x] Каждая остановка: `name`, `lat`, `lon`, `order` (0-based, порядок следования)
- [x] Источник — `settings.data_dir/external/stops_routes.json` (в Docker: `/app/data`, смонтирован ro)
- [x] `lru_cache` по пути каталога (файл ~12 КБ, меняется редко)
- [x] Отсутствие/битый каталог → `200` + пустой `routes` (не `500`): карта деградирует, дашборд живёт
- [x] Битые строки каталога (нет `name`/`lat`/`lon`) пропускаются, `_comment` игнорируется
- [x] Маршруты отсортированы по `route_id` (детерминизм для фронта и тестов)
- [x] `settings.data_dir` вынесен в конфиг (типизированный путь + env-override)
- [x] `make api-gen` + `make fe-gen` — OpenAPI и TS-типы пересобраны (24 paths)
- [x] Тесты: `tests/test_geo_routes_api.py` (8 тестов) — парсер, bbox Москвы, graceful-режим, API
- [x] ruff + mypy strict на новых файлах — чисто
- [x] Запись в ledger: D-041 (контракт), F-103 (фикс api-gen/api-check)

## Technical Notes

```
apps/backend/app/schemas/geo.py   # GeoStop / GeoRoute / GeoRoutesResponse
apps/backend/app/data/geo.py      # load_route_geo(path) + get_route_geo(), lru_cache
apps/backend/app/api/geo.py       # APIRouter(prefix="/api/v1", tags=["geo"])
apps/backend/app/config.py        # settings.data_dir (REPO_ROOT/data, в Docker = /app/data)
apps/backend/app/main.py          # include_router(geo_router)
```

Почему геометрия отдельно от загрузки: `/predictions/load` — прогноз (меняется при каждом
submit), `geo/routes` — справочник (статичен). Фронт мёржит их по `route_id`
(`apps/frontend/src/lib/geoRoutes.ts:mergeRouteTiers`), поэтому у справочника отдельный кэш
и отдельная ответственность.

Побочный фикс (иначе `make check-all` не проходит): `PYTHONPATH=.` в целях
`api-gen`/`api-check` — editable `.pth` от `apps/assistant` перехватывал имя пакета `app`
при запуске скриптов (F-103).

## Verification

```bash
make api-gen && make api-check          # 24 paths, in sync
cd apps/backend && uv run pytest tests/test_geo_routes_api.py -q --no-cov   # 8 passed
cd apps/backend && PYTHONPATH=. uv run python -c \
  "from fastapi.testclient import TestClient; from app.main import create_app; \
   b = TestClient(create_app()).get('/api/v1/geo/routes').json(); \
   print(b['count'], sum(r['n_stops'] for r in b['routes']))"   # 10 142
```

## Status

`done` (2026-09-27). Артефакт: `docs/api/openapi.json` (path `/api/v1/geo/routes`),
TS-типы `apps/frontend/src/generated/api.schemas.ts` (`GeoRoutesResponse`).
