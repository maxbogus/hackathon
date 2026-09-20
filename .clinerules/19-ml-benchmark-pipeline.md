# 19-ml-benchmark-pipeline.md — ML benchmark pipeline (offline tool)

## Что это

Пакет `ml/transit_ai/benchmark/` — **offline tool** для оценки ML-моделей
перед боевым deploy. Запускает walk-forward CV по нескольким историческим окнам,
собирает метрики, формирует лидерборд.

**Цель:** выбрать **лучшую модель для активного** артефакта перед `make predict`.
Без бенчмарка — выкатываем наугад.

**R9 hackathon-rules:** benchmark — dev-only tool, НЕ импортируется из runtime.

**Источники шаблонов:**
- `~/Repositories/contest/ecup26-user-value/scripts/benchmark_t3.py` — walk-forward CV
- `~/Repositories/contest/ecup26-user-value/scripts/ablation_matrix.py` — grid search
- `~/Repositories/study/diplomMagistrate/scripts/benchmark/` — структура пакета (configs/runners/compare)

## Структура пакета

```
ml/transit_ai/benchmark/
├── __init__.py
├── configs.py       # BenchmarkConfig + BenchmarkResult dataclasses
├── runner.py        # walk_forward_cv() + run_benchmark() entry
├── cli.py           # argparse CLI (--strategy, --max-configs, --output)
├── compare.py       # загрузка N JSON-репортов → leaderboard (ASCII table + CSV)
└── report.py        # экспорт BenchmarkResult → CSV+MD

ml/scripts/
├── benchmark_baseline.py    # smoke test (BaselineMean на synthetic, 2 folds)
└── benchmark_all.py         # полный grid (XGBoost + GRU + Hybrid)
```

## Контракт (BenchmarkConfig)

```python
@dataclass
class BenchmarkConfig:
    model_id: str                    # "baseline_v1", "xgboost_v2", "gru_v1"
    feature_set: str                 # "minimal", "extended", "all"
    hyperparams: dict[str, Any]
    cv_folds: int = 4                # walk-forward folds
    seed: int = 42
    horizons: tuple[str, ...] = ("day", "month")  # ("day", "month", "year")

@dataclass
class BenchmarkResult:
    config: BenchmarkConfig
    metrics: dict[str, float]        # {"rmsle": 0.42, "mae": 12.3, "mape": 0.18}
    fold_scores: list[float]         # per-fold RMSLE
    train_time_sec: float
    git_commit: str
    train_data_hash: str
```

## Walk-forward CV

Самый честный метод для timeseries (см. contest/benchmark_t3.py):

```python
def walk_forward_splits(dates: pd.DatetimeIndex, n_folds: int):
    """Генерирует (train_end, val_start, val_end) для каждого fold."""
    splits = []
    chunk = (dates.max() - dates.min()) // (n_folds + 1)
    for i in range(1, n_folds + 1):
        train_end = dates.min() + chunk * i
        val_start = train_end
        val_end = train_end + chunk
        splits.append((train_end, val_start, val_end))
    return splits
```

Никакого `train_test_split` для timeseries! Иначе — утечка будущего в прошлое.

## Команды Makefile

```bash
make benchmark-baseline   # smoke: BaselineMean на synthetic, ~30 сек
make benchmark-all        # full grid: 12 конфигов × 4 folds × 3 horizons = 144 fits
make benchmark-compare    # leaderboard из docs/reports/benchmark_*.json
```

## Метрики (как в contest)

| Метрика | Где важна | Hard limit (CI) |
|---|---|---|
| RMSLE | основная для count data (пассажиры ≥ 0) | ≤ 0.5 |
| MAE | для диспетчера (люди, не логарифмы) | ≤ 15 |
| MAPE | процент ошибки | ≤ 25% |

`RMSLE` (Root Mean Squared Log Error) — primary, потому что пассажиропоток —
это count data с тяжёлым правым хвостом (переполненные вагоны в час пик).

## Когда запускать

| Событие | Триггер |
|---|---|
| Добавил новую модель в `ml/transit_ai/models/` | `make benchmark-baseline` |
| Перед `make predict` на реальных данных | `make benchmark-all` |
| Перед демо / хакатон презентацией | `make benchmark-compare` → leaderboard → в slides |
| Эксперимент с гиперпараметрами | `--strategy random --max-configs 50` |

## Что НЕ делаем

- ❌ Запускать в Docker (R6 clinerule 10-ml-as-scripts.md)
- ❌ Импортировать `ml.transit_ai.benchmark` из runtime (`apps/*`)
- ❌ Использовать test set для выбора модели (только walk-forward CV)
- ❌ Публиковать `ml/artifacts/benchmark_*/` в git (.gitignore)
- ❌ Сравнивать модели с разными `horizons` (это разные задачи)

## Подводные камни

1. **Synthetic данные ≠ реальные** — BaselineMean на synthetic даст RMSLE=0.0,
   а на реальных может быть 0.6. Всегда указывай `train_data_hash` в результате.
2. **GRU + random search = 5 минут на 1 config** — лимитируй `--max-configs`
   в начале, не разоряй GPU.
3. **Сид не зафиксирован** → результаты не воспроизводятся, R6 нарушен.
   Всегда `seed=42` в `BenchmarkConfig`.
4. **Гиперпараметры в dataclass** должны быть JSON-serializable
   (без `torch.Tensor`, только int/float/str/list/dict).

## Reproducibility (R6)

Каждый `BenchmarkResult` содержит:
- `git_commit` — коммит, на котором запущен benchmark
- `train_data_hash` — sha256 датасета (sha256sum parquet)
- `seed` — random seed
- `config_hash` — sha256 от сериализованного BenchmarkConfig

Если любой изменился — результаты не должны считаться «тем же экспериментом».
См. clinerule `05-hackathon-rules.md` R3 (reproducible) и R6 (time limits).
