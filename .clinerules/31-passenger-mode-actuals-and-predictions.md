# 31-passenger-mode-actuals-and-predictions.md — PassengerMode показывает actuals + predictions

## Зачем

Экран диспетчера (`apps/frontend/src/pages/PassengerMode.tsx`) показывает
**два блока рядом**, чтобы можно было сравнить факт и прогноз по маршрутам:

| Блок | Источник | Эндпоинт | Период | i18n-ключ заголовка |
|---|---|---|---|---|
| «Фактическая нагрузка» (actuals) | таблица `actuals` (БД) | `GET /api/v1/historical/load` | последний день с данными (НЕ `now()-7d`!) | `passenger.actualsHeader` |
| «Прогнозируемая нагрузка» (predictions) | таблица `predictions` (БД) | `GET /api/v1/predictions/load` | submission period (`2025-11-01..2025-12-31`) | `passenger.predictionsHeader` |

> T-231: заголовки переименованы из разговорных «Как было (факт)» / «Как будет
> (прогноз)» в официальные термины (см. `.clinerules/32-ui-copy-standards.md`).
> Сам экран тоже переименован: `passenger.modeTitle` = «Пассажиропоток по маршрутам».

## Почему НЕ actuals + NOW()

- Dataset заканчивается `2025-10-31`. Реальное «сегодня» в системе (2026-09+) за пределами датасета.
- `_resolve_history_window` использует `datetime.now(UTC)` → окно пустое → фронт показывает «нет данных».
- **Fallback:** если окно пустое → `[MAX(period_start) - 7d, MAX(period_start)]` (см. `apps/backend/app/api/historical.py:_resolve_history_window`).
- Новый summary endpoint `/historical/load` всегда отдаёт данные, если в БД есть хоть 1 actual.

## Контракт summary endpoint

```python
# apps/backend/app/api/predictions_load.py
@router.get("/predictions/load", response_model=RouteLoadListResponse)
async def get_predictions_load(
    from_date: datetime | None = Query(default=None, alias="from"),  # default: submission period
    to_date: datetime | None = Query(default=None, alias="to"),
    model_id: str | None = Query(default=None),  # default: best (F-083)
    feature_set: str | None = Query(default=None),
    zeros_applied: bool | None = Query(default=None),
    horizon: Literal["day","month","year"] = "day",
    granularity: Literal["hour","day","month"] = "hour",
    session: AsyncSession = Depends(get_db),
) -> RouteLoadListResponse:
    """Avg boardings per route за период → load_pct → tier."""
    ...

class RouteLoadItem(BaseModel):
    route_id: int
    boardings_avg: float
    load_pct: float  # boardings_avg / TRAM_CAPACITY × 100
    tier: Literal["green","yellow","red","darkred"]
    period_start: datetime | None = None  # для actuals — последний час с данными
    period_end: datetime | None = None

class RouteLoadListResponse(BaseModel):
    loads: list[RouteLoadItem]
    count: int
```

## Tier пороги (вынесены в `apps/backend/app/load_tier.py`)

| load_pct (avg) | Tier | Цвет (фронт) |
|---|---|---|
| `< 70` | `green` | комфортно 🟢 |
| `70..90` | `yellow` | умеренно 🟡 |
| `90..110` | `red` | тесно 🟠 |
| `>= 110` | `darkred` | перегруз 🔴 |

Пороги **одинаковые** во фронте (`apps/frontend/src/lib/loadTier.ts`) и в backend
(`apps/backend/app/load_tier.py`). Single source of truth = комментарий в обоих файлах.

## Что НЕ делать

- ❌ Не брать данные из `/api/v1/historical/{route_id}?granularity=hour` (passenger mode) — это только для `AnalystDashboard`.
- ❌ Не смешивать actuals + predictions в одном блоке (разные источники = разные цвета/подписи).
- ❌ Не использовать `datetime.now(UTC)` как правую границу окна (drift).
- ❌ Не возвращать «нет данных» если в БД есть хоть 1 actual — fallback на MAX(period_start) обязателен.

## Frontend контракт

```typescript
// apps/frontend/src/lib/routeLoad.ts
export interface RouteLoad {
  readonly routeId: number;
  readonly boardings: number | null;
  readonly loadPct: number | null;
  readonly tier: LoadTier | 'unknown';
  readonly periodEnd?: string;  // ISO, для подписи «обновлено ...»
}

export async function fetchActualsLoad(): Promise<RouteLoad[]>;  // /api/v1/historical/load
export async function fetchPredictionsLoad(): Promise<RouteLoad[]>;  // /api/v1/predictions/load
```

Два блока в `PassengerMode.tsx`:

```tsx
<section>
  <h2>{t('passenger.actualsHeader')}</h2>
  <div data-testid="actuals-grid">{actuals.map(...)}</div>
  <h2>{t('passenger.predictionsHeader')}</h2>
  <div data-testid="predictions-grid">{predictions.map(...)}</div>
</section>
```

## Cross-references

- T-218 — этот тикет
- `.clinerules/02-architecture.md` — workspace boundaries
- `docs/MODEL_DOMAIN.md` — область определения модели
- F-NNN (findings) — находка про time-drift
- D-NNN (decisions) — решение «actual + prediction side-by-side»
- `apps/backend/app/api/historical.py:_resolve_history_window` (MAX(period_start) fallback)
- `apps/backend/app/load_tier.py` (пороги)
