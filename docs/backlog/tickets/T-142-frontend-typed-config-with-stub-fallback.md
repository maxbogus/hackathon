---
id: T-142
phase: 4
title: Frontend typed config with stub-fallback
priority: P2
effort: 2
unit: hours
rice:
  R: 4
  I: 1.5
  C: 0.9
  score: 2.7
depends_on: []
blocks: [T-122, T-138]
tags: [frontend, config, infra, env, typing]
status: done
created: 2026-09-23
updated: 2026-09-23
assignee: "maxim"
---

# T-142: Frontend typed config with stub-fallback

> Связанное решение: **D-015** в `docs/ledger/decisions.jsonl`.

## Context

Перед реализацией MapProvider (T-122) и assistant (T-138) нужна **единая точка проверки
`.env`-ключей**. Без неё каждый компонент (Map, Search, LLM) парсит `import.meta.env`
по-своему, не знает реальный ключ это или плейсхолдер из `.env.example`, и не может
actionable подсказать разработчику «как починить».

Проблемы без типизированного config-слоя:
1. **Нет единого контракта** — Yandex/2GIS/OpenRouter/Anthropic/GigaChat разбросаны
   по разным компонентам, разные проверки.
2. **Нет stub-детекции** — `loadConfig()` в MapProvider может вернуть `your_key_here`,
   карта упадёт в рантайме с непонятной ошибкой.
3. **Нет actionable reason** — даже если компонент видит stub, он не может сказать
   «скопируйте .env.example → .env и подставьте реальный ключ».
4. **Нет типобезопасности** — строки в `import.meta.env` всегда `string | undefined`,
   нужно явно делать union с ConfigEntry.

## Acceptance Criteria

- [x] `apps/frontend/src/lib/config.ts` создан (136 строк)
- [x] `ConfigEntry<T>` union: `{source: 'real', value} | {source: 'stub', value, reason}`
- [x] Stub-детекция по 2 условиям: пустая строка ИЛИ regex `^your_.*_here$`
- [x] 5 секретных полей обёрнуты в ConfigEntry: yandexMapsKey, yandexGeocoderKey,
      twogisKey, openrouterKey, anthropicKey, gigachatCredentials (6 — это норма)
- [x] Plain типы для не-секретов: impl/provider/type/model/temperature/maxTokens/reasoningEnabled
- [x] Helpers: `hasRealYandexMapsKey()`, `getYandexMapsKeyOrNull()`, `getStubMessage()`
- [x] 23 теста в `config.test.ts` — RED → GREEN цикл
- [x] `yarn test:run` → 23/23 зелёные (один файл, 455ms)
- [x] `yarn typecheck` → 0 errors (TypeScript strict, generic, union types)
- [x] `yarn prettier --check` → clean

## Technical Notes

**Контракт `ConfigEntry<T>`:**

```typescript
export type ConfigEntry<T> =
  | { source: 'real'; value: T }
  | { source: 'stub'; value: T; reason: string };
```

**Stub-детекция** в `entryFor(envKey, friendlyAction)`:
- `raw === ''` → stub с reason про пустоту
- `PLACEHOLDER_RE.test(raw)` (`/^your_.*_here$/`) → stub с reason про плейсхолдер
- иначе → `{source: 'real', value: raw}`

**Структура `AppConfig`:**

```typescript
{
  map:    { impl, yandexMapsKey, yandexGeocoderKey, geocoderUrl },
  search: { provider, twogisKey },
  llm:    { type, model, temperature, maxTokens, reasoningEnabled,
            openrouterKey, anthropicKey, gigachatCredentials }
}
```

**Почему не inline `import.meta.env` в каждом компоненте:**
- Дублирование в Map/Search/LLM/Assistant → 4× правки при изменении `.env` имён
- Нет единого места для actionable error messages
- Невозможно протестировать stub-сценарии (без `vi.stubEnv` в каждом тесте)

**Почему не DI через React Context:**
- Один singleton `loadConfig()` проще для tree-shaking
- Тестируется без `renderHook` / `Provider`-обёртки
- При `vi.stubEnv()` изменения видны сразу, без перерендера

**Downstream потребители:**
- **T-122 MapProvider** — `loadConfig().map.yandexMapsKey.source === 'real'`
  → подключаем YandexMap, иначе LeafletMap.
- **T-138 Assistant** — `loadConfig().llm.openrouterKey.source === 'real'`
  → реальный OpenRouter, иначе demo-режим с заглушкой ответов.

## Verification

```bash
cd /home/maxbogus/Repositories/hackathon

# Изолированный прогон новых тестов
cd apps/frontend && yarn test:run src/lib/config.test.ts
# → 23 passed (455ms)

# Полный test suite (не должно быть регрессий)
cd /home/maxbogus/Repositories/hackathon
cd apps/frontend && yarn test:run
# → было 60+23 = 83/83 (реально 23 в config.test.ts, остальные — i18n, roles, etaClient, ...)

# TypeScript strict
cd apps/frontend && yarn typecheck
# → 0 errors

# Prettier
cd apps/frontend && yarn prettier --check src/lib/config.ts src/lib/config.test.ts
# → All matched files use Prettier code style!
```

## Files

- **Created:** `apps/frontend/src/lib/config.ts` (136 строк)
- **Created:** `apps/frontend/src/lib/config.test.ts` (179 строк, 23 теста)

## Status

`ready` → `in-progress` → `done` (выполнено в этой сессии, ~2ч).
