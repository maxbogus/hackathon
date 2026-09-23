---
id: T-130
phase: 4
title: бизнес-логика рекомендации «ехать сейчас или подождать» в frontend (TypeScript)
priority: P0
effort: 1
unit: hours
rice:
  R: 5
  I: 3.0
  C: 0.9
  score: 13.5
depends_on: [T-129, T-127]
blocks: []
tags: [frontend, react, passenger, business-logic, beneficiary]
status: ready
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-130: бизнес-логика рекомендации «ехать сейчас или подождать» в frontend (TypeScript)

## Context

Боль пассажира: «Ехать сейчас или подождать следующий?» Недостаточно показать данные
(ETA + загрузка) — нужно дать action-oriented рекомендацию. Это превращает UI из «информации»
в «инструмент принятия решения», что и хочет Департамент транспорта.

**Архитектурное решение (D-009):** реализация на TypeScript, не на Python. Чистая
функция `recommend(trams)` лежит в `apps/frontend/src/lib/recommend.ts` — типобезопасная,
покрывается vitest-тестами. UI в режиме «Пассажир» (T-129) импортирует и вызывает её,
показывает результат через React-компонент с цветной иконкой.

## Acceptance Criteria

- [ ] Функция `recommend(trams: ETAPrediction[]): { text: string; emoji: string; severity: 'success' | 'warning' | 'info' }` реализована в `apps/frontend/src/lib/recommend.ts`
- [ ] Логика: если ближайший рейс загружен <70% → рекомендует «Садитесь» (severity: success)
- [ ] Логика: если загружен 70-90% И следующий приходит <10 мин → рекомендует «Подождите X мин — будет свободнее» (severity: info)
- [ ] Логика: если загружен >90% → рекомендует «Обязательно подождите» (severity: warning, emoji ⚠️)
- [ ] Логика: если ближайший уже ушёл (ETA = 0) → рекомендует следующий
- [ ] Метрика под рекомендацией: «Экономия ~N мин времени ожидания в комфорте»
- [ ] Покрытие vitest-тестами: `apps/frontend/src/lib/recommend.test.ts` (5+ кейсов)
- [ ] `PassengerMode.tsx` (из T-129) вызывает `recommend()` и отображает через `<Alert severity={r.severity}>`
- [ ] TypeScript strict: `yarn typecheck` без ошибок

## Technical Notes

Простая decision tree — никаких ML, чистая бизнес-логика. Это показывает жюри, что мы
понимаем не только данные, но и user experience.

```typescript
// apps/frontend/src/lib/recommend.ts
export interface ETAPrediction {
  route_id: number;
  route_name: string;
  eta_min: number;
  predicted_load_pct: number;
  model_id: string;
}

export type Severity = 'success' | 'warning' | 'info';

export interface Recommendation {
  text: string;
  emoji: string;
  severity: Severity;
}

export function recommend(trams: ETAPrediction[]): Recommendation {
  if (trams.length === 0) {
    return { text: 'Нет данных о ближайших рейсах', emoji: '❓', severity: 'info' };
  }
  const current = trams[0]!;
  const nextTram = trams[1];

  if (current.predicted_load_pct < 70) {
    return { text: '✅ Садитесь — будет комфортно', emoji: '✅', severity: 'success' };
  }

  if (current.predicted_load_pct >= 90) {
    if (nextTram && nextTram.eta_min <= 10) {
      return {
        text: `⚠️ Подождите ${nextTram.eta_min} мин — будет значительно свободнее`,
        emoji: '⚠️',
        severity: 'warning',
      };
    }
    return { text: '⚠️ Будет тесно — но вариантов нет', emoji: '⚠️', severity: 'warning' };
  }

  // 70-90%
  if (nextTram && nextTram.eta_min <= 8 && nextTram.predicted_load_pct < current.predicted_load_pct - 15) {
    return {
      text: `⏳ Подождите ${nextTram.eta_min} мин — будет свободнее`,
      emoji: '⏳',
      severity: 'info',
    };
  }
  return { text: '✅ Садитесь — загрузка приемлемая', emoji: '✅', severity: 'success' };
}
```

## Verification

```bash
cd apps/frontend
yarn test:run src/lib/recommend.test.ts
# Должно быть >= 5 тестов, все зелёные

yarn dev
# В режиме Пассажир, остановка 1: должна появиться рекомендация
```

## Beneficiary Impact

**Пассажиры (⭐⭐⭐⭐⭐)** — превращает информацию в действие. Action-oriented UX.
**Департамент транспорта** — демонстрирует продуктовое мышление, а не «ML ради ML».

RICE: 13.5 — **топ-3 приоритет** вместе с T-129.
