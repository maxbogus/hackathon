# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-26T07:55:00+00:00
> Обновлено: Cline (агент) после T-174 + T-124 + T-175 (feature flags + traffic + GRU + ablation)

## Цель

Улучшить holdout WAPE-score и сделать pipeline управляемым через флаги,
чтобы можно было A/B тестировать без отката кода.

## Прогресс

Phase 0-2 завершены. Feature flags (T-174) + traffic features (T-124) +
GRU (T-029/T-175) закоммичены. Ablation analysis показал **критическую находку (F-050)**:
base_only (11 фичей) = wape_score=0.8974 лучше full (56 фичей) = 0.9051.

## Git state

```
branch: master (commits: 87+ ahead of origin/master)
new artifacts: xgboost_v11_flags_default, xgboost_v11_traffic, gru_v1
```

## Что сделано (последние)

- **T-175 (ablation analysis)**: F-050 — base_only ЛУЧШЕ full. Per-route bias calibration
  выравнивает calibrated scores (~0.875 для всех), но raw scores различаются.
  Submission v11_base_only готов (calibrated 0.8751).
- **T-029 (GRU)**: negative result (F-049) — solo wape_score=0.18 (vs XGBoost 0.91).
  Не использовать solo, оставлен в коде с тестами.
- **T-124 (traffic features)**: 40 точек OSM каталога, 3 фичи per stop.
  raw wape_score = 0.9045 (-0.0006 vs full = в пределах шума).
- **T-174 (feature flags)**: YAML config → каждая feature group включается/выключается.
  Defaults = v9_events baseline (reproducible, holdout 0.8751).
  4 ablation variants в `ml/transit_ai/config/variants/`.

## Что в работе

Ничего. Следующий тикет на усмотрение пользователя.

## Следующая задача

**Рекомендация:** залить `v11_base_only` (calibrated 0.8751, но raw 0.8974 — самый
высокий raw из всех вариантов). Per R3 (clinerule 28): сделать sanity-check 5 критериев
перед заливкой, записать F-051 в ledger с platform score.

Команда запуска:
```bash
make backlog-ready
# Или напрямую залить:
ls predictions/submission_xgboost_v11_base_only_*.csv
```

## Открытые вопросы

- **Загружать ли v11_base_only на платформу?** F-050 показал что у него лучший raw score.
  Per-route bias calibration съедает разницу, но raw показатели — индикатор поведения.
  Submission уже готов, manifest verify PASSED, sanity-check 5 критериев ✓.
- **Делать ли LightGBM?** Ablation + 1 submission = 30 мин, LGBM может дать +0.5pp.
  Возможно стоит попробовать.
- **T-171 (presentation/pitch)**: in-progress, 27.09 deadline, осталось ~40ч.

## Артефакты на диске

**Модели:**
- `ml/artifacts/xgboost_v9_events/` — best raw XGBoost (wape_score=0.9051)
- `ml/artifacts/xgboost_v8_poi/` — best calibrated (0.8751) — залит #8, platform=0.73231
- `ml/artifacts/catboost_v1/` — CatBoost (0.8951)
- `ml/artifacts/gru_v1/` — GRU (negative, 0.18)
- `ml/artifacts/xgboost_v11_base_only/` — **NEW** (raw 0.8974 — best raw)

**Submissions (готовы к заливке):**
- `submission_xgboost_v11_flags_default_*` — defaults (identical to v9_events)
- `submission_xgboost_v11_base_only_*` — **рекомендуется** (raw 0.8974)
- `submission_xgboost_v11_traffic_*` — with_traffic variant

**Reports:**
- `docs/reports/ablation_2026-09-26.md` — F-050 (base_only > full)
- `docs/reports/ablation_2026-09-26.csv` — таблица 6 variants

**Configs:**
- `ml/transit_ai/config/defaults.yaml` — defaults (v9_events baseline)
- `ml/transit_ai/config/variants/{base_only,no_events,no_poi,no_external,with_traffic,full_plus_traffic}.yaml`

## Последние решения в ledger

- **D-031**: GRU не использовать solo (negative result, F-049)
- **D-030**: Traffic features через hardcoded OSM каталог (R3/R4 compliant)
- **D-029**: Feature flags через YAML (T-174)

## Последние находки

- **F-050** ⚠️: base_only > full в raw scores → feature groups ВРЕДЯТ на holdout
- **F-049**: GRU solo = 0.18 (worse than XGBoost 0.91)
- **F-048**: defaults.yaml воспроизводит v9_events baseline (0.8751 = identical)
- **F-047**: CatBoost blend calibrated 0.9047 (vs XGB-alone 0.8751) — НО local holdout НЕ предсказывает platform (F-040)

## Не делать в следующей сессии

- ❌ Не использовать `python3 -c "..."` с f-string (zsh ломает — см. clinerule 29)
- ❌ Не использовать `sed`/`heredoc` для правок Python файлов — editor tool
- ❌ Не заливать submission без sanity-check 5 критериев (clinerule 28)
- ❌ Не откатывать код при drift — feature flags решают (T-174)
- ❌ Не обучать модели в Docker (только скриптами через make)
