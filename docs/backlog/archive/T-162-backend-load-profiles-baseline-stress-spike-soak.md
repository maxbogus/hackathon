---
id: T-162
phase: 1
title: 4 профиля нагрузки (baseline 50VU/5m, spike 10→200, stress 100VU/3m, soak 30VU/30m)
priority: P1
effort: 3
unit: hours
rice:
  R: 4
  I: 2.0
  C: 1.0
  score: 6.00
depends_on: [T-160]
blocks: []
tags: [backend, loadtest, k6, profiles, soak, spike, stress]
status: done
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-162: 4 профиля нагрузки k6 — повторяемая методология

## Context

T-160 даёт только smoke (10 VU × 30s). Для submission prep нужны 4 профиля,
покрывающие разные сценарии:
- **Baseline** — нормальная нагрузка ЕДЦ (50 VU × 5 мин)
- **Stress** — экстремум (100 VU × 3 мин, как просил пользователь)
- **Spike** — резкий скачок (10 → 200 VU за 10 сек)
- **Soak** — долговременная стабильность (30 VU × 30 мин, ищет memory/connection leaks)

Каждый профиль — отдельный JS-скрипт в tests/load/. Документация — docs/load-profiles/README.md.

## Acceptance Criteria

- [x] tests/load/baseline_dispatcher.js: 50 VU × 5 мин, 3 эндпоинта (round-robin), p95 ≤ 2s, error_rate ≤ 1%
- [x] tests/load/stress_dispatcher.js: 100 VU × 3 мин (по запросу пользователя), p95 ≤ 3s
- [x] tests/load/spike_dispatcher.js: 10 VU → 200 VU за 10 сек → 10 VU, p95 ≤ 4s
- [x] tests/load/soak_dispatcher.js: 30 VU × 30 мин, p95 ≤ 2s, error_rate ≤ 0.5%
- [x] Makefile targets (в .PHONY):
  - [x] loadtest-baseline (50 VU × 5 мин)
  - [x] loadtest-stress (100 VU × 3 мин)
  - [x] loadtest-spike (резкий скачок)
  - [x] loadtest-soak (30 мин)
  - [x] loadtest-all — последовательно все 4 профиля
- [x] docs/load-profiles/README.md — справочник:
  - [x] Таблица: профиль / VU / duration / thresholds / когда
  - [x] Интерпретация графиков (latency trend, error rate trend, RPS)
- [x] HTML-отчёты в docs/load-profiles/reports/<profile>_<timestamp>.html
- [x] JSON-отчёты для CI gate (T-161)

## Technical Notes

**tests/load/stress_dispatcher.js:**

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const SLA_P95_MS = 3000;
const SLA_ERROR_RATE = 0.02;
const dispatchLatency = new Trend('dispatch_latency_ms', true);
const successCounter = new Counter('successful_requests');
const errorCounter = new Counter('failed_requests');

export const options = {
  stages: [
    { duration: '30s', target: 100 },
    { duration: '3m', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    'http_req_duration': [`p(95)<${SLA_P95_MS}`],
    'http_req_failed': [`rate<${SLA_ERROR_RATE}`],
  },
};

const BASE_URL = __ENV.BACKEND_URL || 'http://localhost:8000'\;
const STOP_IDS = Array.from({ length: 50 }, (_, i) => i + 1);
const ENDPOINTS = [
  (id) => `/api/v1/predictions/stop/${id}`,
  (id) => `/api/v1/predictions/eta?stop_id=${id}&n=3`,
  () => '/api/v1/models/active',
];

export default function () {
  const stopId = STOP_IDS[Math.floor(Math.random() * STOP_IDS.length)];
  const endpointFn = ENDPOINTS[Math.floor(Math.random() * ENDPOINTS.length)];
  const url = `${BASE_URL}${endpointFn(stopId)}`;
  const res = http.get(url);
  dispatchLatency.add(res.timings.duration);
  const ok = check(res, { 'status is 2xx': (r) => r.status >= 200 && r.status < 300 });
  if (ok) successCounter.add(1);
  else errorCounter.add(1);
  sleep(0.5);
}
```

**spike_dispatcher.js stages:**
```javascript
stages: [
  { duration: '30s', target: 10 },
  { duration: '10s', target: 200 },
  { duration: '1m', target: 200 },
  { duration: '10s', target: 10 },
  { duration: '30s', target: 10 },
]
```

**docs/load-profiles/README.md:**

| Профиль | VU | Длительность | SLA p95 | Когда запускать |
|---------|----|--------------|---------|-----------------|
| smoke | 10 | 30s | ≤ 2s | pre-push hook |
| baseline | 50 | 5min | ≤ 2s | перед каждым PR |
| stress | 100 | 3min | ≤ 3s | перед submission |
| spike | 10→200 | 3min | ≤ 4s | еженедельно |
| soak | 30 | 30min | ≤ 2s, err ≤ 0.5% | раз в неделю |

## Verification

```bash
make loadtest-baseline  # 5 мин
make loadtest-stress    # 3 мин
make loadtest-spike     # 3 мин
ls docs/load-profiles/reports/  # HTML + JSON
```

## Beneficiary Impact

Жюри (5/5) — proof of methodology.
Команда (4/5) — разделение use-cases.

RICE: 6.00 — не блокер, но +25% к credibility.
