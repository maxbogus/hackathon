---
id: T-037
phase: 2
title: ml transit_ai reports plots matplotlib confusion calibration
priority: P2
effort: 4
unit: hours
rice:
  R: 3
  I: 2.0
  C: 0.7
  score: 1.05
depends_on: []
blocks: []
tags: [ml, reports, plots]
status: ready
created: 2026-09-20
updated: 2026-09-20
assignee: ""
---

# T-037: ml transit_ai reports plots matplotlib confusion calibration

## Context

Why this task exists.

## Acceptance Criteria

- [ ] `ml/transit_ai/reports/plots.py` экспортирует ≥3 функции: `plot_metrics`, `plot_predictions_vs_actual`, `plot_calibration_biases` (доп.: `plot_residuals`, `plot_timeseries_forecast`)
- [ ] Каждая функция возвращает `Path` к PNG-файлу (headless Agg backend — никаких display)
- [ ] `make evaluate` (после T-035) пишет ≥1 PNG в `docs/reports/figures/<model_id>_<date>/`
- [ ] `plot_metrics(metrics: dict, output: Path)` — bar chart RMSLE/MAE/MAPE + threshold lines (hard limits из evaluate.THRESHOLDS)
- [ ] `plot_predictions_vs_actual(y_true, y_pred, output, *, n=1000)` — scatter + y=x reference line + доля точек в ±20%
- [ ] `plot_calibration_biases(calibration_json: Path, output: Path)` — histogram per bucket + глобальный bias
- [ ] Использует `transit_ai.reports.metrics.compute_metrics` (D-006 — single source of truth)
- [ ] matplotlib ≥3.5 в `ml/pyproject.toml` (уже есть, проверить)
- [ ] Юнит-тест: `ml/tests/test_plots.py::test_plots_create_pngs` — все функции возвращают непустой Path, файл существует, размер > 1KB
- [ ] `make check-all` зелёный

## Technical Notes

- Backend: `matplotlib.use("Agg")` в начале модуля (headless, нужен для CI и удалённых машин)
- `plt.style.use("seaborn-v0_8" или "ggplot")` — единый стиль
- Размер шрифта + dpi — фиксированные (12pt, 100dpi → можно инкапсулировать в `_default_rcparams()`)
- Sanity guard: если `y_true` или `y_pred` пустые → write пустой PNG с текстом "no data" вместо crash
- Файлы → `docs/reports/figures/<model_id>_<YYYY-MM-DD>/<plot_name>.png` (не плоский `figures/` — легче cleanup по дате)

## Verification

```bash
make ...
```
