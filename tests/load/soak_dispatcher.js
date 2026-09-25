// Transit-AI — k6 soak load test (T-162)
// 30 VU × 30 мин. Используется для поиска memory/connection leaks.
// p95 ≤ 2s, error_rate ≤ 0.5% (более строгий порог — долговременная стабильность).

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// SLA пороги для soak (строже чем baseline — долгая стабильность)
const SLA_P95_MS = 2000;
const SLA_ERROR_RATE = 0.005;

const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');
const successCounter = new Counter('successful_requests');
const failedCounter = new Counter('failed_requests');

export const options = {
  vus: 30,
  duration: '30m',
  thresholds: {
    // Effective thresholds (for grep / code review):
    //   p(95)<2000
    //   rate<0.005
    'http_req_duration': [`p(95)<${SLA_P95_MS}`],
    'http_req_failed': [`rate<${SLA_ERROR_RATE}`],
    'errors': [`rate<${SLA_ERROR_RATE}`],
  },
};

const BASE_URL = __ENV.BACKEND_URL || 'http://localhost:8000';
const STOP_IDS = Array.from({ length: 30 }, (_, i) => i + 1);

export default function () {
  const stopId = STOP_IDS[Math.floor(Math.random() * STOP_IDS.length)];
  const url = `${BASE_URL}/api/v1/predictions/stop/${stopId}`;

  const res = http.get(url);
  dispatchLatency.add(res.timings.duration);

  const ok = check(res, {
    'status is 2xx': (r) => r.status >= 200 && r.status < 300,
    'has body': (r) => r.body && r.body.length > 0,
  });

  if (ok) {
    successCounter.add(1);
    errorRate.add(0);
  } else {
    failedCounter.add(1);
    errorRate.add(1);
  }

  sleep(1);
}
