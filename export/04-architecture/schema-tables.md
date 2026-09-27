# Schema Tables — entity & privacy overview

> Generated from `apps/backend/app/models` — do not edit by hand.
> Run `make arch-dbml` to regenerate.

| Table | Purpose | Privacy hints | Columns |
|-------|---------|---------------|---------|
| `actuals` | Historical boardings (one row per route × datetime). | — | 5 |
| `feature_toggles` | Один toggle: фича (например use_poi) включена или нет. | — | 6 |
| `predictions` | One prediction point: route × datetime → value. | — | 22 |
| `prediction_runs` | Один запуск ml_pipeline Celery task. | — | 14 |
| `zero_overrides` | Один override: zero_strategy + параметры. | — | 6 |
