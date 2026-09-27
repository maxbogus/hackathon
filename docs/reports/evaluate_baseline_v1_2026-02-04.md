# Evaluation Report — baseline_v1

Generated: 2026-09-27T00:04:18.116898+00:00
Git commit: 21d991a
Holdout: 2026-01-29T00:00:00 .. 2026-02-04T23:00:00
N points evaluated: 1488
Eval time: 0.53s

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| RMSLE | 0.2335 | ≤ 0.5 | ✅ |
| MAE | 3.5167 | ≤ 15.0 | ✅ |
| MAPE | 19.3295 | ≤ 25.0 | ✅ |

## Notes

- In-memory evaluation (predictor.predict on holdout, not parquet-based)
- Metrics from `transit_ai.reports.metrics` (single source of truth)
- Thresholds from clinerule 19 (CI gate values)
