# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-26T20:13:00+00:00
> Обновлено: Cline (агент) — F-083: 🎉🎉 ДВОЙНОЙ ПРОРЫВ! Submission A = 0.83455 (+0.01334), Submission B = 0.83348 (+0.01227). NEW BEST = Submission A. alias обновлён.

## Цель

Достичь WAPE-score ≥ 0.85 на платформе. Текущий best: **0.82121** (F-060).

## T-182 platform result (F-072)

T-182 (weekend_mult LAYERED на F-060): holdout 0.8270 (+0.0481), **platform 0.82121 (= F-060, drift -0.0058)**. Lift НЕ перенёсся на платформу (F-040 confirmed).

F-060 (0.82121) — confirmed PEAK. F-051..F-063 + F-067..F-074 = 12 проверок, 0 lift.
Стратегия зануления pred<=X в hours 0-4 почти исчерпана (Δ <0.0001 на сдвиг ±5).
Пользователь решил остановиться.

## Прогресс (финальный)

**Platform results (полная кривая зануления pred<=X в hours 0-4):**
| Submission | Platform | Δ vs base |
|---|---|---|
| base (v11_no_route5) | 0.82075 | — |
| B (8 пар p_zero>=30%) | 0.82092 | +0.00017 |
| D (pred<=20) | 0.82113 | +0.00038 |
| E (pred<=50) | 0.82114 | +0.00039 |
| G (pred<=25) | 0.82111 | +0.00036 |
| G (pred<=35) | 0.82111 | +0.00036 |
| H (pred<=45) | 0.82112 | +0.00037 |
| **H (pred<=55)** | **0.82121** | **+0.00046** ← BEST |
| F (pred<=100) | 0.82067 | -0.00008 |
| **F-063: pred55 h0-6** | **0.82099** | **+0.00024** |
| F-063: pred55 h0-5 | 0.82105 | +0.00030 |
| F-063: pred65 h0-4 | 0.82117 | +0.00042 |

**Общий прирост от стратегии зануления: +0.00046 (с учётом route 5: +0.08884).**

## Git state

```
branch: master
6 slots remaining (2 попытки использованы: A + B) (A1, A2 уже использованы)

**3 ablation готовы к заливке (F-078):**
- A1: route 7/50 evening (×0.7, -18k boardings) — lowest risk, рекомендую начать с него
- A2: holiday 3 ноября (×0.5, -111k boardings) — medium risk
- A3: route 5 partial restore (+324k boardings) — highest risk
~30h до дедлайна

## T-182 candidate (F-071)
- File: predictions/submission_route_baseline_v1_20251101_20251231_20260926T163020Z.csv
- Holdout WAPE-score: **0.8270** (+0.0481 vs F-060 0.8751)
- Post-processing: F-051 (route 5 zero) + F-060 (pred_cap 55 h0-4) + T-182 (weekend_mult Sat×0.5827, Sun×0.4846)
- Platform drift risk: -0.05..-0.14pp (F-040). Expected platform: 0.78-0.88.
```

## Финальный submission (alias)

`predictions/submission.csv` = `submission_v11_no_route5_nightzero_pred55_20251101_20251231_20260926T093655Z.csv` (F-060 BEST, 0.82121). Альтернативы с почти таким же score: F060_plus_pred65 (0.82117, чуть мягче).

Post-processing:
- per_route_log_bias_calibration
- zero_route_5_per_F-051
- zero_night_hours_pred55_per_F-059

## Что сделано (вся сессия)

- **T-193** ✅: Celery pipeline (apps/harvester + apps/ml_pipeline). 7+3 tests зелёные, ruff 0 errors. `make pipeline-fetch` качает weather(365)/traffic(41)/poi(146)/events(8).
- **T-194** ✅: PostgreSQL schema + alembic migrations. 5 ORM моделей (Actual, Prediction, FeatureToggle, ZeroOverride, PredictionRun). 8 unit tests. Migration round-trip upgrade→downgrade→upgrade работает. TimescaleDB hypertable для actuals (best-effort, postgres-only). Seeds: 6 feature_toggles + 4 zero_overrides (F-051/F-060 best).
- **F-051/F-052**: zero route 5 → +0.08844 (8.84pp, biggest single win)
- **F-054**: B (8 пар p_zero>=30%) → +0.00017 ✅
- **F-054**: C (blend raw+cal) → -0.236 ❌ raw predictions штрафуются
- **F-056**: D pred<=20 → +0.00021 ✅
- **F-057**: E pred<=50 → +0.00001 ✅
- **F-058**: F pred<=100 → -0.00047 ❌ overreach
- **F-059**: G pred<=25/35 → -0.00003 (плато)
- **F-060**: H pred<=55 → +0.00007 ← BEST в занулении
- **F-061**: BUG агента (replay 6 вариантов) → clinerule #30 создан, D-027 формализован
- **F-062** ⚠️: T-178/T-179 standalone дали 0.72568/0.72823 (vs best 0.82121, Δ-0.09). Причина: route 5 zero ОТСУТСТВУЕТ. T-180/combined — НЕ лить.
- **F-063** ✅: 3 layered вариации (pred55_h06/h05/pred65) залиты: 0.82099/0.82105/0.82117 (Δ -0.00004..-0.00022). Подтверждено: F-060 = peak.

## Находки (главные)

- **F-060** 🏆: pred<=55 — peak зануления в hours 0-4
- **F-058**: pred<=100 overreach → pred=50-100 содержит реальный трафик
- **F-052**: route 5 = 1.31M чистого штрафа (физика: трамвай не выводят)
- **F-040**: local holdout ≠ platform (drift -0.05..-0.14pp)
- **F-067** (negative): нет структурных нулей per (route,hour) в Jan-Oct 2025 — гипотеза закрыта
- **F-068** (negative): bias×hour LAYERED — все α кроме 5000 дают регрессию на holdout. D-023 global bias is optimal.
- **F-069** (negative): LSTM blend с XGBoost — best = no-blend (w_lstm=0). Подтверждает F-064. Neural dead-end.
- **F-070** (risk-analysis): T-180 zero_weekends занулит 19.5% volume → F-062-style regression. Не залито (no-slot-spent).
- **F-071** (T-182): weekend_mult LAYERED на F-060 — holdout lift +0.0481, **PLATFORM 0.82121 = F-060 (F-072)**, drift -0.0058
- **F-073** (new data): route 5 ОТКРЫТ 16.12.2025. F-051 может быть over-zeroed (untestable).
- **F-074** (per-route weekend_mult): holdout lift +0.0434 — ХУЖЕ global +0.0481 (overfits in-sample). Negative.
- **F-075** (T-184): schedule_overrides (route 5 partial + 7/50 evening + 3 нояб) — submission готов, UNTESTABLE на holdout
- **F-076** (edge-case audit): 8 новых тестов на weekend_mult, 0 багов найдено. 1 реальный баг найден в schedule_overrides (duplicate param 'date') — исправлен
- **F-077** ❌ (T-184): platform 0.74360 = regression -0.0776. Route 5 partial = главный виновник. F-060 confirmed peak.
- **F-078**: 3 ablation (A1/A2/A3) готовы к заливке по одному слоту, attribution analysis
- **F-079**: KudaGo offline НЕВОЗМОЖНО без user data. R4 блокирует API. Нужен manual hardcoded JSON.
- **F-080**: A2 (3 нояб ×0.5) → 0.82533 (+0.00412) — предыдущий best
- **F-081**: B1/B2 candidates готовы. Holiday override strategy подтверждена.
- **F-082**: Phase 2 реализация — 3 новые функции (period/event/vacation), 10 RED-then-GREEN тестов
- **F-083** 🏆🎉: Submission A (conservative) = **0.83455 (+0.01334 vs F-060) = NEW BEST/home/maxbogus/Repositories/hackathon && uv run --directory ml ruff check transit_ai/calibration/schedule_overrides.py tests/test_schedule_overrides_extended.py 2>&1 | tail -3* Submission B (aggressive) = 0.83348 (+0.01227). Holiday + cold snap strategy WORKS.

## Не делать

- ❌ Не использовать `python3 -c "..."` с f-string
- ❌ Не использовать raw_v9 без bias calibration (C -0.236)
- ❌ Не заливать submission без sanity-check 5/5
- ❌ Не расширять pred порог выше 55 в hours 0-4
- ❌ Не расширять hours выше 0-4 (стратегия насыщена)
- ❌ Не предлагать варианты экспериментов без проверки ledger (F-061 → clinerule #30 R1-R6)
- ❌ **НЕ лить standalone вариации без route 5 zero** (F-062: drift −0.14). Только layered на F-060.
- ❌ **НЕ искать structural zeros per (route,hour)** (F-067 negative: ZERO пар, гипотеза закрыта).
- ❌ **НЕ реализовывать bias×hour calibration** (F-068: in-sample overfit, регрессия на holdout)
- ❌ **НЕ делать LSTM/GRU blend с XGBoost** (F-069: best blend = no-blend; F-064 GRU; neural dead-end)
- ❌ **НЕ лить T-180 zero_weekends/zero_holidays** (F-070: 19.5% volume занулено, F-062-style drift)
- ❌ **НЕ тратить слоты на negative гипотезы без sanity check** (F-068/F-069/F-070: sanity check BEFORE code)

## T-184 candidate (F-075, ready to upload)

**Platform scores history:**
- **F-083 Submission A (conservative)** = **0.83455 🏆 NEW BEST (+0.01334 vs F-060)**
- **F-083 Submission B (aggressive)** = **0.83348 (+0.01227)**
- F-080 A2 (3 нояб ×0.5) = 0.82533 (+0.00412)
- F-060 baseline = 0.82121

**Confirmed strategies:**
- ✅ Holiday override ×0.5 для федеральных праздников (A2 confirmed, расширен на 4 нояб + 31 дек)
- ✅ Cold snap ×0.92 (23-31 декабря) — снижение трафика в морозы
- ⚠️ School vacation ×0.85 в school hours — slightly negative (-0.001 в B)
- ⚠️ Event multipliers (1.05-1.15) — slightly negative (-0.001 в B)

**Lessons:**
- Conservative > Aggressive для UNTESTABLE overrides (A > B, в отличие от F-077 где multi был BAD)
- User data + правильный multiplier = lift
- Compounded overrides не всегда regression (если все правильные)

**KudaGo offline (F-079):** НЕВОЗМОЖНО без user data. R4 hackathon-rules блокирует online API. Hardcoded JSON требует manual event list от user. Educated guess = F-077-style regression risk.

**Результат T-184:** platform = **0.74360** (-0.0776 vs F-060). **РЕГРЕССИЯ** (F-077).

**Attribution analysis:**
- T-182 weekend_mult (отдельно) = 0.82121 (F-072, no improvement)
- T-184 = T-182 + 3 schedule overrides = **0.74360** (regression -0.0776)
- **Главный виновник:** route 5 partial restore. +324k boardings restored (после 16.12), реальный трафик вероятно = 0 (cold start продолжается). Effect: ~-0.05..-0.10 WAPE-score.
- Holiday 3 ноября (×0.5): -111k boardings. Effect: -0.01..-0.02 (если реальный трафик workday-уровень).
- Route 7/50 evening (×0.7): -24k boardings. Effect: ~-0.001 (minor).

**Урок (F-029 confirmed AGAIN):** UNTESTABLE на holdout overrides = HIGH RISK. User данные 'точные' по датам/маршрутам, но platform расходится с нашими предположениями о реальном трафике.

**Edge case coverage:** 32/32 tests passed (weekend_mult 15 + schedule_overrides 10 + route_bias 7). 1 real bug найден в schedule_overrides (duplicate param) → fixed via TDD.
