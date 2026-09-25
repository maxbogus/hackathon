# Skill: k6 Load Testing Playbook (02-k6-load-testing)

> Длинная инструкция для AI-агентов по нагрузочному тестированию Transit-AI через k6.
> Загружается по требованию через `use_skill("02-k6-load-testing")`.
> Короткая версия правил — в `.clinerules/22-load-testing.md`.

## Назначение

Этот скилл нужен при работе с:
- `tests/load/*.js` — k6 скрипты (smoke/baseline/stress/spike/soak)
- `scripts/check_load_sla.py` — SLA gate (R6 ≤ 2000ms p95, ≤ 1% errors)
- `docker-compose.yml` — профиль `loadtest` с k6 контейнером
- `docs/load-profiles/reports/` — HTML/JSON артефакты для жюри

## Структура

```
hackathon/
├── tests/load/                        # k6 скрипты
│   ├── smoke_dispatcher.js            # 10 VU × 30s (CI gate)
│   ├── baseline_dispatcher.js         # 50 VU × 5min (round-robin 3 endpoints)
│   ├── stress_dispatcher.js           # 100 VU × 3min (stages)
│   ├── spike_dispatcher.js            # 10→200 VU (resilience)
│   └── soak_dispatcher.js             # 30 VU × 30min (memory leak)
├── scripts/
│   └── check_load_sla.py              # парсер JSON → PASS/FAIL
├── docs/load-profiles/
│   ├── README.md                      # справочник профилей
│   └── reports/                       # HTML + JSON отчёты (gitignore?)
├── docker-compose.yml                 # профиль loadtest с k6 сервисом
└── Makefile                           # targets loadtest-*
```

## Шаблон скрипта

### Smoke (без stages, fixed VU)

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    // Effective thresholds (for grep / code review):
    //   p(95)<2000
    //   rate<0.01
    'http_req_duration': ['p(95)<2000'],
    'http_req_failed': ['rate<0.01'],
    'errors': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BACKEND_URL || 'http://localhost:8000';
const STOP_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export default function () {
  const stopId = STOP_IDS[Math.floor(Math.random() * STOP_IDS.length)];
  const res = http.get(`${BASE_URL}/api/v1/predictions/stop/${stopId}`);
  dispatchLatency.add(res.timings.duration);
  const ok = check(res, { 'status is 200': (r) => r.status === 200 });
  errorRate.add(ok ? 0 : 1);
  sleep(1);
}
```

### Stress / Spike (со stages — ramp-up + hold + ramp-down)

```javascript
export const options = {
  stages: [
    { duration: '30s', target: 100 },  // ramp-up
    { duration: '3m', target: 100 },   // hold
    { duration: '30s', target: 0 },    // ramp-down
  ],
  thresholds: { /* те же */ },
};
```

**Spike:** добавить recovery stage (target: 10 после 200).

## Запуск (ВСЕГДА через Makefile)

```bash
make up                                # backend + db + redis
make loadtest-smoke                    # 30s
make loadtest-check                     # SLA gate
```

**❌ Не запускать** `k6 run` напрямую — без CPU pinning и в обход профиля.

## Чтение результатов

### JSON артефакт (для SLA gate)

```json
{
  "metrics": {
    "http_req_duration": { "p(95)": 1234.5 },
    "http_req_failed": { "rate": 0.005 }
  }
}
```

`scripts/check_load_sla.py` парсит это и валидирует thresholds.

### HTML отчёт (для жюри)

`docs/load-profiles/reports/smoke_<timestamp>.html` — self-contained файл с графиками:
- **HTTP Request Duration** (p50/p95/p99 тренд)
- **HTTP Requests** (RPS, drop = bottleneck)
- **HTTP Request Failed** (rate по времени)

Открыть в браузере: `xdg-open docs/load-profiles/reports/smoke_*.html`

## Troubleshooting

| Симптом | Диагноз | Решение |
|---------|---------|---------|
| p95 > SLA, RPS flat | backend CPU-bound | Увеличить `--workers` в Dockerfile, профилировать |
| p95 растёт линейно | memory leak в backend | Запустить soak, проверить RSS |
| RPS падает на hold-стадии | connection pool exhaustion | Увеличить `pool_size` в SQLAlchemy |
| Много 5xx в начале | cold start | `--start-period=15s` в HEALTHCHECK (есть) |
| k6 не запускается в Docker | cpuset не поддерживается на хосте | Убрать `cpuset`, оставить `mem_limit` |
| `make loadtest-check` FAIL | thresholds breach | Смотреть JSON: какой metric, какое значение |

## Где применяется

| Файл/Цель | Назначение |
|------------|-----------|
| `tests/load/*.js` | k6 скрипты |
| `scripts/check_load_sla.py` | SLA gate |
| `docs/load-profiles/reports/` | артефакты |
| `docker-compose.yml` | k6 сервис в профиле loadtest |
| `Makefile` | targets `loadtest-*` |

## Don't do

- ❌ Запускать k6 на хосте (нет CPU pinning)
- ❌ Менять thresholds без обновления `docs/load-profiles/README.md`
- ❌ Коммитить `docs/load-profiles/reports/*.html` (могут быть 100MB+)
- ❌ Запускать soak в CI (30 мин блокирует PR)
- ❌ Сравнивать результаты разных профилей (разные SLA, stages)

## Cross-references

- `.clinerules/22-load-testing.md` — короткие hard rules
- T-160..T-165 — тикеты load testing
- T-167 — HACKATHON_CHECKLIST дополнение
