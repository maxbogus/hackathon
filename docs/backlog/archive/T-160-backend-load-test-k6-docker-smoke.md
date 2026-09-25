---
id: T-160
phase: 1
title: Backend load test setup — k6 в Docker-контейнере + smoke сценарий
priority: P0
effort: 3
unit: hours
rice:
  R: 8
  I: 3.0
  C: 1.0
  score: 8.00
depends_on: []
blocks: [T-161, T-162]
tags: [backend, loadtest, k6, docker, sla, r6, mandatory]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-160: k6 load test setup — Docker + smoke сценарий

## Context

R6 hackathon-rules (`.clinerules/05-hackathon-rules.md`):
> "Inference ≤ 2 секунды на запрос диспетчера (SLA из ТЗ)"

Сейчас **нет нагрузочных тестов**, нет проверки SLA. Невозможно доказать жюри,
что backend выдерживает реальную нагрузку ЕДЦ (по ТЗ хакатона — десятки
диспетчеров одновременно). Без load test есть риск, что production-нагрузка
убьёт backend на демо.

**Решение:** k6 (Grafana) в отдельном Docker-контейнере с CPU pinning для
изоляции наводящей нагрузки. Web dashboard + HTML-отчёты с графиками
(запрошено пользователем).

**Преимущества k6:**
- Нативный Docker-образ `grafana/k6` (34 MB)
- Web dashboard (`K6_WEB_DASHBOARD=true`) на порту 5665 — живой график
- HTML-отчёт (`K6_WEB_DASHBOARD_EXPORT=`) — self-contained с графиками
- JSON output для CI gate (T-161)
- Thresholds в JS-файле для SLA-проверки
- CPU pinning через `cpuset` в compose — не наводит нагрузку на backend

## Acceptance Criteria

- [ ] `docker-compose.yml` содержит профиль `loadtest` с сервисом `k6`:
  - [ ] image: `grafana/k6:0.54.0`
  - [ ] `network_mode: host` (прямой доступ к localhost:8000)
  - [ ] `deploy.resources`: `cpus: 2.0, mem_limit: 1g, cpuset: "0,1"` (CPU pinning)
  - [ ] volumes: `./tests/load:/scripts:ro`, `./docs/load-profiles/reports:/reports:rw`
  - [ ] env: `K6_WEB_DASHBOARD=true`, `K6_WEB_DASHBOARD_PORT=5665`, `K6_WEB_DASHBOARD_EXPORT=/reports/<name>.html`
- [ ] `tests/load/smoke_dispatcher.js`:
  - [ ] 10 VU × 30 сек
  - [ ] GET `/api/v1/predictions/stop/{1..10}?period_start=...&period_end=...`
  - [ ] Thresholds: `http_req_duration: ['p(95)<2000']` (R6 SLA)
  - [ ] check: `status === 200`
- [ ] `Makefile` targets (закоммичены в `.PHONY`):
  - [ ] `loadtest-smoke` — запускает smoke в контейнере
  - [ ] help: описание "10 VU × 30s smoke test (R6 SLA check)"
- [ ] RED test `tests/test_loadtest_makefile.py`:
  - [ ] `make -n loadtest-smoke` показывает правильную команду
  - [ ] Цель `loadtest-smoke` присутствует в `make help`
- [ ] `make loadtest-smoke` запускается с backend на :8000
- [ ] HTML-отчёт сохраняется в `docs/load-profiles/reports/smoke_<timestamp>.html`
- [ ] JSON-отчёт сохраняется в `docs/load-profiles/reports/smoke_<timestamp>.json`

## Technical Notes

**JS-скрипт (`tests/load/smoke_dispatcher.js`):**

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// === SLA thresholds (R6 hackathon-rules) ===
const SLA_P95_MS = 2000;
const SLA_ERROR_RATE = 0.01; // 1%

// === Custom metrics для графиков ===
const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'http_req_duration': [`p(95)<${SLA_P95_MS}`],
    'errors': [`rate<${SLA_ERROR_RATE}`],
    'http_req_failed': [`rate<${SLA_ERROR_RATE}`],
  },
};

const BASE_URL = __ENV.BACKEND_URL || 'http://localhost:8000';
const STOP_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export default function () {
  const stopId = STOP_IDS[Math.floor(Math.random() * STOP_IDS.length)];
  const now = new Date();
  const start = new Date(now.getTime() - 60 * 60 * 1000).toISOString();
  const end = now.toISOString();
  const url = `${BASE_URL}/api/v1/predictions/stop/${stopId}?period_start=${start}&period_end=${end}`;

  const res = http.get(url);
  dispatchLatency.add(res.timings.duration);
  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'has data array': (r) => {
      try {
        const body = JSON.parse(r.body as string);
        return Array.isArray(body.data);
      } catch {
        return false;
      }
    },
  });
  if (!ok) errorRate.add(1);
  else errorRate.add(0);

  sleep(1); // 1 req/sec per VU
}
```

**docker-compose.yml fragment (добавить к существующему):**

```yaml
  k6:
    image: grafana/k6:0.54.0
    container_name: transit-ai-k6
    profiles: ["loadtest"]
    network_mode: host
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
        reservations:
          cpus: "1.0"
          memory: 512M
    volumes:
      - ./tests/load:/scripts:ro
      - ./docs/load-profiles/reports:/reports:rw
    environment:
      K6_WEB_DASHBOARD: "true"
      K6_WEB_DASHBOARD_PORT: "5665"
      K6_WEB_DASHBOARD_EXPORT: "/reports/smoke_${TIMESTAMP}.html"
      K6_WEB_DASHBOARD_OPEN: "false"
    command: ["run", "/scripts/smoke_dispatcher.js"]
```

**Makefile fragment:**

```makefile
loadtest-smoke: ## 10 VU × 30s smoke (R6 SLA p95 ≤ 2s)
	@mkdir -p docs/load-profiles/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	  docker compose --profile loadtest run --rm \
	    -e K6_WEB_DASHBOARD_EXPORT=/reports/smoke_$$TIMESTAMP.html \
	    -e K6_WEB_DASHBOARD_OPEN=false \
	    k6 run /scripts/smoke_dispatcher.js
```

## Verification

```bash
# 1. RED test зелёный
uv run pytest tests/test_loadtest_makefile.py -v

# 2. Поднять backend (для реального прогона)
make up
# ждём ~30 сек пока backend healthy

# 3. Smoke load test
make loadtest-smoke
# → k6 выводит: "thresholds: http_req_duration........: p(95)=1.2s < 2000 OK"
# → HTML: docs/load-profiles/reports/smoke_<timestamp>.html
# → Web dashboard: http://localhost:5665

# 4. Проверить артефакты
ls -la docs/load-profiles/reports/
```

## Beneficiary Impact

**Жюри (⭐⭐⭐⭐⭐)** — доказательство что backend выдерживает реальную нагрузку.
**Команда (⭐⭐⭐⭐)** — регрессии SLA ловятся ДО демо.
**Диспетчеры (⭐⭐⭐⭐)** — система не падает под нагрузкой.

RICE: 8.00 — топ-1 приоритет, без этого нельзя сабмитить.
