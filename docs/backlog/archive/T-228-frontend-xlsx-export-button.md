---
id: T-228
phase: 4
title: "frontend: кнопка «Скачать XLSX» на дашборде Аналитик"
priority: P2
effort: 1
unit: hours
rice:
  R: 6
  I: 1.0
  C: 0.9
  score: 5.4
depends_on: []
blocks: []
tags: [frontend, ui, export, xlsx]
status: done
created: 2026-09-27
updated: 2026-09-27
assignee: "bogusov"
---

# T-228: XLSX-экспорт в UI Аналитика

## Context

Бэкенд-эндпоинт `GET /api/v1/predictions/export.xlsx` существовал с T-206
(openpyxl, headers `X-Row-Count` / `Content-Disposition`), но в UI кнопки не было —
критерий 4 ТЗ («CSV+XLSX») был закрыт только со стороны API.

## Acceptance Criteria

- [x] В `AnalystDashboard` две кнопки: «⬇️ Скачать CSV» и «⬇️ Скачать XLSX».
- [x] XLSX — бинарный ответ: `customInstance({responseType:'blob'})` + скачивание
      через Blob URL.
- [x] Параметры экспорта (from/to/coef_*) общие для CSV и XLSX (`buildExportQuery`).
- [x] Статус/ошибка экспорта отображаются (`data-testid="xlsx-status"`).
- [x] Тексты — через `t()`/`tf()` (clinerule 20), без хардкода в `.tsx`.

## Verification

```bash
cd apps/frontend && yarn vitest run src/api/downloadXlsx.test.ts
cd apps/frontend && yarn typecheck
make frontend-text-check
curl -sI localhost:8000/api/v1/predictions/export.xlsx | head -3
```

## Status

`done` (4 теста downloadXlsx + 7 тестов GeneratePanel зелёные).
