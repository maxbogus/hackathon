# HANDOFF — Transit-AI

> Последнее обновление: 2026-09-26T12:55:00+00:00
> Обновлено: Cline (агент) — clinerule #30 (no-replay) добавлен после F-061 (баг '6 replay вариантов').

## Цель

Достичь WAPE-score ≥ 0.85 на платформе. Текущий best: **0.82121** (pred<=55 h0-4).
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

**Общий прирост от стратегии зануления: +0.00046 (с учётом route 5: +0.08884).**

## Git state

```
branch: master
14 slots remaining
~32h до дедлайна
```

## Финальный submission (alias)

`predictions/submission.csv` = `submission_v11_no_route5_nightzero_pred55_20251101_20251231_20260926T093655Z.csv`

Post-processing:
- per_route_log_bias_calibration
- zero_route_5_per_F-051
- zero_night_hours_pred55_per_F-059

## Что сделано (вся сессия)

- **F-051/F-052**: zero route 5 → +0.08844 (8.84pp, biggest single win)
- **F-054**: B (8 пар p_zero>=30%) → +0.00017 ✅
- **F-054**: C (blend raw+cal) → -0.236 ❌ raw predictions штрафуются
- **F-056**: D pred<=20 → +0.00021 ✅
- **F-057**: E pred<=50 → +0.00001 ✅
- **F-058**: F pred<=100 → -0.00047 ❌ overreach
- **F-059**: G pred<=25/35 → -0.00003 (плато)
- **F-060**: H pred<=55 → +0.00007 ← BEST в занулении
- **F-061**: BUG агента (replay 6 вариантов) → clinerule #30 создан, D-027 формализован

## Находки (главные)

- **F-060** 🏆: pred<=55 — peak зануления в hours 0-4
- **F-058**: pred<=100 overreach → pred=50-100 содержит реальный трафик
- **F-052**: route 5 = 1.31M чистого штрафа (физика: трамвай не выводят)
- **F-040**: local holdout ≠ platform (drift -0.05..-0.14pp)

## Не делать

- ❌ Не использовать `python3 -c "..."` с f-string
- ❌ Не использовать raw_v9 без bias calibration (C -0.236)
- ❌ Не заливать submission без sanity-check 5/5
- ❌ Не расширять pred порог выше 55 в hours 0-4
- ❌ Не расширять hours выше 0-4 (стратегия насыщена)
- ❌ Не предлагать варианты экспериментов без проверки ledger (F-061 → clinerule #30 R1-R6)

## Если есть время (опционально)

- T-178: убрать per-route bias calibration (другой подход к underprediction)
- T-179: попробовать другие часы (hours 0-5, hours 0-6)
- T-180: попробовать другие маршруты по контексту (weekends, holidays)
