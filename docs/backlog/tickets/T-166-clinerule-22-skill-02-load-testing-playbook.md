---
id: T-166
phase: 7
title: clinerule 22 (load-testing) + skill 02 (k6 playbook) — повторяемая методология для агентов
priority: P2
effort: 2
unit: hours
rice:
  R: 3
  I: 2.0
  C: 1.0
  score: 4.00
depends_on: [T-162]
blocks: []
tags: [docs, clinerule, skill, load-testing, methodology]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-166: clinerule 22 + skill 02 — load testing playbook

## Context

После T-160..T-165 у нас есть 5 профилей нагрузки, k6 в Docker, SLA gate,
docker resources, training budget. Но **нет документации для следующего агента**,
который придёт работать с проектом через месяц.

Без clinerule + skill агент может:
- Случайно запустить k6 на хосте (а не в Docker) — сломает CPU pinning
- Пренебречь thresholds — пропустит SLA breach
- Забыть про HTML-отчёты — потеряет графики для жюри

Решение: clinerule 22 (краткие hard rules) + skill 02 (длинная инструкция).

## Acceptance Criteria

- [ ] .clinerules/22-load-testing.md (новый, формат как 17-pyscn-quality-gate.md):
  - [ ] Hard rules: ❌ k6 на хосте, ❌ игнорировать thresholds, ✅ JSON output, ✅ HTML артефакты
  - [ ] Когда запускать: pre-push (smoke), перед submission (stress), раз в неделю (soak)
  - [ ] Quick reference: команды make loadtest-*
  - [ ] Cross-references на T-160, T-161, T-162, T-163, T-165
- [ ] ai/skills/02-k6-load-testing.md (длинная инструкция):
  - [ ] Шаблон JS-скрипта (smoke/stress/spike/soak)
  - [ ] Как парсить thresholds
  - [ ] Как читать HTML-отчёт
  - [ ] Troubleshooting: высокий p95 → где искать bottleneck
- [ ] docs/load-profiles/README.md — справочник профилей (кратко из clinerule)
- [ ] .clinerules/00-AGENTS.md обновлён (новый индекс)
- [ ] Скрипт scripts/promote_note.py поддерживает --target clinerule/skill
- [ ] uv run pytest tests/test_clinerule_index.py зелёный (проверка индекса)

## Technical Notes

**.clinerules/22-load-testing.md (skeleton):**

```markdown
# 22-load-testing.md — k6 load testing rules

## Hard rules

- ❌ НЕ запускать k6 на хосте (только в Docker контейнере из профиля loadtest)
- ❌ НЕ превышать thresholds в JS-скриптах (если p95 > SLA — блокер для merge)
- ✅ ВСЕГДА --out json для парсинга в SLA gate (T-161)
- ✅ ВСЕГДА сохранять HTML-отчёт в docs/load-profiles/reports/
- ✅ CPU pinning для k6 контейнера (cpuset: "0,1") — не наводить нагрузку на backend

## Когда запускать

| Событие | Профиль | Команда |
|---------|---------|---------|
| Pre-push (CI hook) | smoke | make loadtest-smoke |
| Перед PR | baseline | make loadtest-baseline |
| Перед submission | stress | make loadtest-stress |
| Еженедельно | soak | make loadtest-soak |
| После deploy | spike | make loadtest-spike |

## SLA thresholds (R6 hackathon-rules)

- p95 latency ≤ 2000ms (smoke/baseline)
- p95 latency ≤ 3000ms (stress)
- p95 latency ≤ 4000ms (spike)
- p95 latency ≤ 2000ms + err ≤ 0.5% (soak)
- error_rate ≤ 1% (smoke/baseline)
- error_rate ≤ 2% (stress/spike)
- error_rate ≤ 0.5% (soak)

## Quick reference

```bash
make loadtest-smoke    # 10 VU × 30s (CI gate)
make loadtest-baseline # 50 VU × 5 min
make loadtest-stress   # 100 VU × 3 min (submission prep)
make loadtest-spike    # 10→200 VU (resilience test)
make loadtest-soak     # 30 VU × 30 min (memory leak detection)
make loadtest-check    # Parse latest JSON, verify SLA
```

## Cross-references

- T-160 — k6 setup + smoke
- T-161 — SLA regression gate
- T-162 — 4 профиля нагрузки
- T-163 — docker-compose resources + loadtest profile
- T-165 — training time budget
- ai/skills/02-k6-load-testing.md — длинная инструкция
- .clinerules/05-hackathon-rules.md — R6 SLA definition
```

**ai/skills/02-k6-load-testing.md (skeleton, сокращённо):**

```markdown
# Skill: k6 Load Testing Playbook

Подключать через `use_skill("02-k6-load-testing")` при работе с нагрузочными тестами.

## 1. Структура проекта

- `tests/load/*.js` — k6 скрипты (smoke, baseline, stress, spike, soak)
- `tests/load/*.json` — отчёты (генерируются автоматически)
- `docs/load-profiles/README.md` — справочник профилей
- `docs/load-profiles/reports/*.html` — HTML отчёты с графиками
- `scripts/check_load_sla.py` — парсер JSON → PASS/FAIL

## 2. Шаблон скрипта

[полный шаблон с примерами для каждого профиля]

## 3. Запуск

Всегда через `make loadtest-*` (не напрямую k6).

## 4. Troubleshooting

[частые проблемы + решения]
```

## Verification

```bash
# 1. clinerule в индексе
grep "22-load-testing" .clinerules/00-AGENTS.md
# → "22 | `22-load-testing.md` | k6 load testing rules"

# 2. Skill доступен
ls ai/skills/02-k6-load-testing.md

# 3. Документация
cat docs/load-profiles/README.md
```

## Beneficiary Impact

Агенты (5/5) — следующий агент сразу понимает как работать с load tests.
Команда (4/5) — воспроизводимая методология.

RICE: 4.00 — внутренний процесс, не блокер.
