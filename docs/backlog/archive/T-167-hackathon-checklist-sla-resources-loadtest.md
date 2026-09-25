---
id: T-167
phase: 7
title: HACKATHON_CHECKLIST — добавить секции SLA + Container resources + Load test
priority: P1
effort: 0.5
unit: hours
rice:
  R: 4
  I: 2.0
  C: 1.0
  score: 6.00
depends_on: [T-137, T-161]
blocks: []
tags: [docs, hackathon, checklist, sla, r3, r6]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-167: HACKATHON_CHECKLIST — секции SLA + Container resources + Load test

## Context

T-137 (RICE 6.0, ready) создаёт docs/HACKATHON_CHECKLIST.md с базовыми секциями.
Но после T-160..T-165 появляются новые требования:
- SLA p95 ≤ 2 сек (R6) — нужно документировать + ссылка на доказательство
- Container resources (R3 reproducible) — нужно показать что есть лимиты
- Load test reports — нужна ссылка на HTML/JSON отчёты

Без этих секций в чек-листе жюри не увидит compliance с R3 + R6.

## Acceptance Criteria

- [ ] docs/HACKATHON_CHECKLIST.md содержит дополнительные секции:
  - [ ] Секция "SLA Compliance (R6)":
    - [ ] p95 latency ≤ 2000ms verified via make loadtest-check
    - [ ] Ссылка на docs/load-profiles/reports/<latest>.html
    - [ ] Ссылка на scripts/check_load_sla.py
  - [ ] Секция "Container Resources (R3)":
    - [ ] docker compose config показывает deploy.resources для всех сервисов
    - [ ] k6 контейнер с CPU pinning (cpuset)
    - [ ] Ссылка на docker-compose.yml
  - [ ] Секция "Load Testing Methodology":
    - [ ] 5 профилей: smoke / baseline / stress / spike / soak
    - [ ] Каждый профиль — отдельный JS-скрипт в tests/load/
    - [ ] HTML-отчёты в docs/load-profiles/reports/
- [ ] Каждая секция содержит:
  - [ ] Статус: ✅ / ⚠️ / ❌
  - [ ] Ссылка на доказательство (артефакт)
  - [ ] Команду для проверки

## Technical Notes

**Секция "SLA Compliance (R6)":**

```markdown
## Секция 12. SLA Compliance (R6)

| Требование | Статус | Доказательство |
|------------|--------|----------------|
| p95 latency ≤ 2000ms | ⬜ | `make loadtest-check` |
| error_rate ≤ 1% | ⬜ | `make loadtest-check` |
| HTML-отчёт с графиками | ⬜ | `docs/load-profiles/reports/<latest>.html` |
| Smoke test в CI gate | ⬜ | T-160, T-161 |

Команды:
```bash
make loadtest-smoke    # 10 VU × 30s
make loadtest-check    # парсинг JSON → PASS/FAIL
```
```

**Секция "Container Resources (R3)":**

```markdown
## Секция 13. Container Resources (R3 reproducible)

| Сервис | CPU limit | Memory limit | Доказательство |
|--------|-----------|--------------|----------------|
| backend | 1.0 | 512MB | `docker compose config` |
| postgres | 1.0 | 1GB | `docker compose config` |
| redis | 0.25 | 256MB | `docker compose config` |
| frontend | 0.25 | 128MB | `docker compose config` |
| k6 (loadtest) | 2.0 + cpuset 0,1 | 1GB | `docker compose config` |

Команды:
```bash
docker compose config | grep -A 5 "deploy:"
docker compose --profile loadtest config | grep cpuset
```
```

**Секция "Load Testing Methodology":**

```markdown
## Секция 14. Load Testing Methodology

| Профиль | VU | Длительность | Когда запускать |
|---------|----|--------------|-----------------|
| smoke | 10 | 30s | pre-push |
| baseline | 50 | 5min | перед PR |
| stress | 100 | 3min | перед submission |
| spike | 10→200 | 3min | еженедельно |
| soak | 30 | 30min | раз в неделю |

Скрипты: `tests/load/{smoke,baseline,stress,spike,soak}_dispatcher.js`
Документация: `docs/load-profiles/README.md`
HTML-отчёты: `docs/load-profiles/reports/*.html`
```

## Verification

```bash
# 1. Чек-лист содержит 14 секций (было 11)
grep -c "^## Секция" docs/HACKATHON_CHECKLIST.md
# → 14

# 2. Каждая новая секция имеет доказательство
grep -A 3 "SLA Compliance" docs/HACKATHON_CHECKLIST.md | grep "Доказательство"
```

## Beneficiary Impact

Жюри (5/5) — full compliance evidence в одном месте.
Команда (4/5) — чек-лист перед submission.

RICE: 6.00 — обязательный для submission.
