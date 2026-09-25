# 22-load-testing.md — k6 load testing rules

## Hard rules

- ❌ **НЕ** запускать k6 на хосте (только в Docker контейнере из профиля `loadtest`)
- ❌ **НЕ** превышать thresholds в JS-скриптах (если p95 > SLA — блокер для merge)
- ❌ **НЕ** использовать `npm install` / `pnpm install` для k6 (только Docker `grafana/k6`)
- ✅ **ВСЕГДА** `--out json` (или `K6_WEB_DASHBOARD_EXPORT`) для парсинга в SLA gate (T-161)
- ✅ **ВСЕГДА** сохранять HTML-отчёт в `docs/load-profiles/reports/`
- ✅ **ВСЕГДА** CPU pinning для k6 контейнера (`cpuset: "0,1"`) — не наводить нагрузку на backend
- ✅ **ВСЕГДА** запускать через `make loadtest-*` (не напрямую `k6 run`)

## Когда запускать

| Событие | Профиль | Команда | Время |
|---------|---------|---------|-------|
| Pre-push (CI hook) | smoke | `make loadtest-smoke` | ~30s |
| Перед PR | baseline | `make loadtest-baseline` | ~5min |
| Перед submission | stress | `make loadtest-stress` | ~3min |
| Еженедельно | soak | `make loadtest-soak` | ~30min |
| После deploy / регрессии | spike | `make loadtest-spike` | ~3min |
| Перед merge в main | all | `make loadtest-all` | ~12min |

## SLA thresholds (R6 hackathon-rules)

```
p95 latency  ≤ 2000ms   (smoke / baseline / soak)
p95 latency  ≤ 3000ms   (stress)
p95 latency  ≤ 4000ms   (spike)

error_rate   ≤ 1.0%     (smoke / baseline)
error_rate   ≤ 0.5%     (soak — строже для долгой стабильности)
error_rate   ≤ 2.0%     (stress / spike — допуск для экстремума)
```

CI gate: `make loadtest-check` парсит последний JSON и валидирует.

## Quick reference

```bash
# Запуск
make up                                    # поднять backend (8000)
make up-loadtest                           # backend + k6 контейнер
make loadtest-smoke                        # 10 VU × 30s (CI gate)
make loadtest-baseline                     # 50 VU × 5 min
make loadtest-stress                       # 100 VU × 3 min (submission prep)
make loadtest-spike                        # 10→200 VU (resilience test)
make loadtest-soak                         # 30 VU × 30 min (memory leak)
make loadtest-all                          # smoke + baseline + stress + spike
make loadtest-check                        # Parse latest JSON → PASS/FAIL

# Артефакты
ls docs/load-profiles/reports/             # HTML + JSON отчёты
open http://localhost:5665                 # web dashboard (во время прогона)
```

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

## Где применяется

| Файл/Цель | Назначение |
|------------|-----------|
| `tests/load/*.js` | k6 скрипты (smoke, baseline, stress, spike, soak) |
| `scripts/check_load_sla.py` | парсер JSON → PASS/FAIL (T-161) |
| `scripts/check_training_time.py` | R6 training time budget (T-165) |
| `docs/load-profiles/README.md` | справочник профилей |
| `docs/load-profiles/reports/` | HTML + JSON отчёты |
| `docker-compose.yml` | профиль `loadtest` с k6 сервисом |
| `Makefile` | targets `loadtest-*` |
| `.githooks/pre-push` | вызов `make loadtest-smoke` (опционально) |

## Типичные ошибки

- ❌ **k6 на хосте** — нет CPU pinning, нагружает backend, ломает измерения
- ❌ **Игнор thresholds** — k6 не падает на breach, нужно парсить JSON вручную (T-161)
- ❌ **Запуск без `--out json`** — нечего парсить для SLA gate
- ❌ **Забыть про HTML** — нет графиков для презентации жюри
- ❌ **Запустить soak в CI** — 30 мин блокирует PR-cycle
- ❌ **Сравнивать результаты разных профилей** — у них разные SLA, разные stages

## Don't do

- ❌ Менять thresholds без обновления `docs/load-profiles/README.md`
- ❌ Удалять `docs/load-profiles/reports/` (для истории + жюри)
- ❌ Использовать k6 ≤ 0.49 (нет `K6_WEB_DASHBOARD_EXPORT`)
- ❌ Коммитить `docs/load-profiles/reports/*.html` без gitignore review (могут быть 100MB+)

## Cross-references

- T-160 — k6 setup + smoke
- T-161 — SLA regression gate (`scripts/check_load_sla.py`)
- T-162 — 4 профиля нагрузки (baseline/stress/spike/soak)
- T-163 — docker-compose resources + loadtest profile
- T-164 — Dockerfile hardening (CPU/mem limits)
- T-165 — ML training time budget (R6 ≤ 60 мин)
- T-167 — HACKATHON_CHECKLIST дополнение
- `ai/skills/02-k6-load-testing.md` — длинная инструкция (use_skill)
- `.clinerules/05-hackathon-rules.md` — R6 SLA definition
- `.clinerules/21-runtime-uv.md` — uv как единый runner
