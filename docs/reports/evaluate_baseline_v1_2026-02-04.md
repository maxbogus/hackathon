# Evaluation Report — baseline_v1

Generated: 2026-09-22T19:21:03.797093+00:00
Git commit: 0d58869
Holdout: 2026-01-29T00:00:00 .. 2026-02-04T23:00:00
N points evaluated: 1488
Eval time: 0.49s

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| RMSLE | 0.6953 | ≤ 0.5 | ❌ |
| MAE | 29.5187 | ≤ 15.0 | ❌ |
| MAPE | 102.2259 | ≤ 25.0 | ❌ |

## Notes

- In-memory evaluation (predictor.predict on holdout, not parquet-based)
- Metrics from `transit_ai.reports.metrics` (single source of truth)
- Thresholds from clinerule 19 (CI gate values)
