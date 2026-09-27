# Load Profiles — Transit-AI

k6 (Grafana) load testing methodology for the Transit-AI backend.
See `.clinerules/22-load-testing.md` for hard rules.

## Profiles

| Профиль | VU | Длительность | SLA p95 | Когда запускать |
|---------|----|--------------|---------|-----------------|
| smoke | 10 | 30s | ≤ 2s | pre-push hook |
| baseline | 50 | 5min | ≤ 2s | перед каждым PR |
| stress | 100 | 3min | ≤ 3s | перед submission |
| spike | 10→200 | 3min | ≤ 4s | еженедельно |
| soak | 30 | 30min | ≤ 2s, err ≤ 0.5% | раз в неделю |

## Архитектура

```
host machine (CPU 0-1)         host machine (CPU 2+)
┌─────────────────┐             ┌─────────────────┐
│  k6 контейнер   │   HTTP      │  backend        │
│  grafana/k6     │ ──────────► │  FastAPI :8000  │
│  cpuset: 0,1    │             │  CPU pinning off│
│  network: host  │             │                 │
│  mem: 1G        │             │  mem: 512M      │
└─────────────────┘             └─────────────────┘
```

**Изоляция:** k6 жмёт только ядра 0-1, backend работает на остальных.
Нагрузка НЕ наводится на измеряемый сервис.

## Использование

```bash
# Запуск (требует поднятый backend)
make up                              # backend на :8000
make loadtest-smoke                  # 10 VU × 30s (CI gate)
make loadtest-baseline               # 50 VU × 5 min
make loadtest-stress                 # 100 VU × 3 min
make loadtest-spike                  # 10→200 VU (resilience)
make loadtest-soak                   # 30 VU × 30 min (memory leak)
make loadtest-check                  # parse latest JSON → PASS/FAIL
```

## Артефакты

После каждого запуска создаются:

| Файл | Формат | Назначение |
|------|--------|------------|
| `docs/load-profiles/reports/<profile>_<timestamp>.html` | HTML (self-contained) | Жюри, презентация (графики latency, RPS, errors) |
| `docs/load-profiles/reports/<profile>_<timestamp>.json` | JSON | Парсинг в `check_load_sla.py` |

Web dashboard: `http://localhost:5665` (открывается во время прогона)

## Интерпретация графиков

**Latency trend** (HTTP Request Duration):
- Если растёт линейно → memory leak
- Если staircase → GC pauses
- Flat → healthy

**RPS** (HTTP Requests):
- Flat → backend справляется
- Drop → bottleneck (DB, CPU, connection pool)

**Error rate** (HTTP Request Failed):
- Любые 5xx = блокер для merge
- Spike в начале = cold start (норма)

## SLA thresholds (R6 hackathon-rules)

```
p95 latency  ≤ 2000ms  (smoke / baseline / soak)
p95 latency  ≤ 3000ms  (stress)
p95 latency  ≤ 4000ms  (spike)

error_rate   ≤ 1.0%    (smoke / baseline)
error_rate   ≤ 0.5%    (soak)
error_rate   ≤ 2.0%    (stress / spike)
```

CI gate: `make loadtest-check` парсит последний JSON и валидирует.

## Cross-references

- `.clinerules/22-load-testing.md` — hard rules для агентов
- `ai/skills/02-k6-load-testing.md` — длинная инструкция по k6
- `T-160..T-167` — тикеты в `docs/backlog/tickets/`
- `docs/HACKATHON_CHECKLIST.md` (T-137) — submission readiness
