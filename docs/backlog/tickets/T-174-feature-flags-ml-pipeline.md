---
id: T-174
phase: 2
title: Feature flags для ML pipeline (каждая фича/модель включается через YAML, без отката кода)
priority: P1
effort: 2
unit: hours
rice:
  R: 8
  I: 3.0
  C: 0.8
  score: 9.60
depends_on: [T-172, T-173]
blocks: [T-175]
tags: [ml, feature-flags, architecture, ablation, drift]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: maxim
---

# T-174: Feature flags для ML pipeline

## Context

После T-173 (CatBoost blend) видно: **local holdout 0.9047 → platform 0.18-0.35** (drift -0.5-0.7pp).
Local score НЕ предсказывает platform score. Это значит:

1. Новые фичи могут улучшить local holdout, но ухудшить platform score
2. Нельзя откатывать код — нужен механизм A/B через флаги
3. Чтобы понять, какие фичи реально работают — нужен ablation analysis

**Решение:** feature flags через YAML конфиг. `make_submission.py --flags-file <yaml>` позволяет
переключать любую группу фичей (POI, events, traffic, weather, calendar) и любую модель (xgb, catboost, gru)
без правки кода.

## Decision

**2 новых компонента:**

1. `ml/transit_ai/config/flags.py` — `FeatureFlags` dataclass с ~15 полями + `FlagsRegistry`
2. `ml/transit_ai/config/defaults.yaml` — baseline = текущий best (v8_poi конфигурация)

**3-й компонент (минимальная интеграция):**

`ml/transit_ai/models/xgboost_route.py` — `_make_features(df, flags=None)` пропускает
feature groups если `flags.use_xxx=False`.

## FeatureFlags schema

```yaml
# ml/transit_ai/config/defaults.yaml
features:
  use_calendar_rf: true         # T-148 holidays/weekend
  use_seasonal_calendar: true   # T-160 school/vacation
  use_weather: true             # T-161
  use_validators_lookup: true   # T-162
  use_geo_features: true        # T-156
  use_poi_features: true        # T-168 (146 POI per-route)
  use_events: true              # T-172 (8 infrastructure events)
  use_traffic: false            # T-124 (будет в T-175)

models:
  use_xgboost: true
  use_catboost: true
  use_gru: false                # T-029 (будет в T-175)

modes:
  blend_method: weighted_mean   # weighted_mean | rank_average
  use_recursive: false          # T-153
  use_per_route_bias: true      # T-147
```

## Acceptance Criteria

- [ ] `ml/transit_ai/config/flags.py` — FeatureFlags + FlagsRegistry
- [ ] `ml/transit_ai/config/defaults.yaml` — флаги = v8_poi baseline
- [ ] `ml/transit_ai/models/xgboost_route.py` — `_make_features(df, flags=None)` принимает flags
- [ ] `ml/scripts/make_submission.py` — `--flags-file <yaml>` аргумент
- [ ] `ml/tests/test_config_flags.py` — минимум 5 тестов:
      [ ] `test_flags_load_yaml` — YAML → dataclass
      [ ] `test_flag_disable_poi` — POI=off → 0 POI фичей в FEATURE_NAMES
      [ ] `test_flag_disable_events` — events=off → 0 event фичей
      [ ] `test_flag_disable_geo` — geo=off → 0 geo фичей
      [ ] `test_default_flags_match_v8_poi` — defaults.yaml = reproducible v8_poi
- [ ] `make check-all` зелёный
- [ ] 2 новых submission на платформе:
      [ ] `submission_xgboost_v11_flags_full` (все flags on, как v9_events) — sanity
      [ ] `submission_xgboost_v11_flags_no_events` (events off) — A/B test
- [ ] D-029 в ledger (feature flags architecture)

## Technical Notes

**Динамический FEATURE_NAMES:** если flags отключают фичи, FEATURE_NAMES должен
меняться без перезапуска Python. Решение — построение в `_make_features` из groups:
```python
def _make_features(df, target=None, lag_lookup=None, flags=None):
    flags = flags or FlagsRegistry.default().features
    feature_names = list(_BASE_FEATURES)
    if flags.use_geo_features: feature_names.extend(_GEO_FEATURES)
    if flags.use_seasonal_calendar: feature_names.extend(_SEASONAL_FEATURES)
    ...
```

**Совместимость:** если flags=None — старое поведение (все фичи on, как v9_events).

## Verification

```bash
make test
uv run --directory ml pytest tests/test_config_flags.py -v
uv run --directory ml python scripts/make_submission.py \
  --flags-file ml/transit_ai/config/defaults.yaml \
  --model-id xgboost_v11_flags_full --submission-id v11-flags-full
uv run --directory ml python scripts/make_submission.py \
  --flags-file ml/transit_ai/config/no_events.yaml \
  --model-id xgboost_v11_flags_no_events --submission-id v11-no-events
# → 2 SUBMISSION CANDIDATE blocks
```

## Status

`ready` → `in-progress` → `done` (после заливки или осознанного отказа)
