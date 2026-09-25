# 27-wape-score-vs-wape.md — WAPE vs WAPE-score (НЕ путать!)

## Что это

На хакатоне используются **две разные метрики** с похожими названиями. Их путаница
приводит к ошибкам в ledger, отчётах, и интерпретации результатов.

| Метрика | Формула | Диапазон | Направление | Цель жюри |
|---|---|---|---|---|
| **WAPE** | `Σ\|y − ŷ\| / Σy` | `[0, +∞)` | меньше = лучше | — |
| **WAPE-score** | `max(0, 1 − WAPE)` | `[0, 1]` | больше = лучше | **≥ 0.85** |

## Канонические имена в коде

| Файл | Имя в коде | Тип |
|---|---|---|
| `ml/transit_ai/reports/metrics.py:4` | `wape_score()` функция | snake_case |
| `ml/transit_ai/reports/metrics.py:11` | `compute_metrics()` возвращает dict с ключом `"wape_score"` | snake_case |
| `ml/scripts/make_submission.py:168,190` | print: `"Holdout WAPE-score"` | kebab-case (для человекочитаемости) |
| `predictions/submission.json` (manifest) | `"holdout_wape_score": 0.8751` | snake_case (clinerule 23) |
| Ledger (`docs/ledger/*.jsonl`) | в тексте: `"WAPE-score"` | kebab-case (читаемо) |
| **F-033 в ledger** | расшифровка: `WAPE-score = 1 - WAPE` | — |

## Частые ошибки

### ❌ "Цель жюри = WAPE ≤ 0.05" (F-026)

Это **ОШИБКА** в формулировке. Правильно:
- Цель жюри = **WAPE-score ≥ 0.85** (D-016, ml/transit_ai/reports/metrics.py:3-4)
- Что эквивалентно **WAPE ≤ 0.15**, НЕ 0.05
- WAPE ≤ 0.05 = WAPE-score ≥ 0.95 — нереалистично для этой задачи (baseline ≈ 0.48 score)

### ❌ "submission #3 WAPE=0.14734" (F-024)

Это **WAPE-score**, не WAPE. Написано `WAPE-score=0.14734` в F-024, но в тексте часто
сокращается до `WAPE`. Score=0.14734 — **ПЛОХОЙ** результат (ниже 0.5).

### ❌ "WAPE = 0.0639 (recursive) vs 0.2129 (lookup)" (F-027)

Это **WAPE-score**. Recursive=0.0639 — **очень плохо**, lookup=0.2129 — **ещё хуже**.

### ❌ "WAPE=0.8751 (holdout v8)"

Это **WAPE-score**, не WAPE. score=0.8751 — **отлично** (выше цели 0.85).

## Как читать платформенные метрики

Платформа хакатона выдаёт `Скор=...` в личном кабинете. По D-016 это **WAPE-score**.

| Платформенный скор | Интерпретация |
|---|---|
| 0.05–0.20 | Очень плохо (модель едва лучше baseline) |
| 0.20–0.50 | Плохо (baseline ≈ 0.48) |
| 0.50–0.70 | Средне |
| 0.70–0.85 | Хорошо |
| **0.85–0.95** | **Цель жюри выполнена** |
| 0.95+ | Отлично (теоретический максимум) |

## Правило для ledger и отчётов

При упоминании метрики в ledger/документации:

1. **В тексте** — используй `WAPE-score` (kebab-case) с дефисом
2. **В коде/JSON** — используй `wape_score` (snake_case)
3. **Всегда указывай** "WAPE-score" целиком, не сокращай до "WAPE" — иначе это уже другая метрика
4. **При сравнении** с платформенным скором — помни что score ∈ [0,1] больше = лучше

## Где смотреть эталонную реализацию

```python
# ml/transit_ai/reports/metrics.py:1-30
def wape(y_true, y_pred):
    """WAPE = Σ|y − ŷ| / Σy ∈ [0, +∞)."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    denom = np.abs(y_true).sum()
    if denom == 0:
        return 0.0
    return np.abs(y_true - y_pred).sum() / denom


def wape_score(y_true, y_pred):
    """WAPE-score = max(0, 1 − WAPE) ∈ [0, 1]. Больше = лучше."""
    return max(0.0, 1.0 - wape(y_true, y_pred))
```

## Cross-references

- D-016 в `docs/ledger/decisions.jsonl` — выбор WAPE-score как primary метрики
- F-033 в `docs/ledger/findings.jsonl` — major clarification по путанице WAPE/WAPE-score
- F-026 — ошибочная формулировка "WAPE ≤ 0.05", НЕ копировать
- `ml/transit_ai/reports/metrics.py` — каноническая реализация
- T-168 (submission #8) — первый submission с holdout WAPE-score=0.8751 (выше цели)
