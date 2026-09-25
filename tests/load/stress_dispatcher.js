// Transit-AI — k6 stress load test (T-162)
// 100 VU × 3 min, stages (ramp-up → hold → ramp-down), p95 ≤ 3s, error_rate ≤ 2%.
// Используется для проверки поведения backend при пиковой нагрузке.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// SLA пороги для stress (R6 допуск расширен)
const SLA_P95_MS = 3000;
const SLA_ERROR_RATE = 0.02;

const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');
const successCounter = new Counter('successful_requests');
const failedCounter = new Counter('failed_requests');

export const options = {
  stages: [
    { duration: '30s', target: 100 }, // ramp-up 0 → 100 VU
    { duration: '3m', target: 100 },  // hold at 100 VU
    { duration: '30s', target: 0 },   // ramp-down 100 → 0 VU
  ],
  thresholds: {
    // Effective thresholds (for grep / code review):
    //   p(95)<3000
    //   rate<0.02
    'http_req_duration': [`p(95)<${SLA_P95_MS}`],
    'http_req_failed': [`rate<${SLA_ERROR_RATE}`],
    'errors': [`rate<${SLA_ERROR_RATE}`],
  },
};

const BASE_URL = __ENV.BACKEND_URL || 'http://localhost:8000';
const STOP_IDS = Array.from({ length: 50 }, (_, i) => i + 1);

// 3 эндпоинта: predictions/stop, predictions/eta, models/active
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

  sleep(0.5);
}
