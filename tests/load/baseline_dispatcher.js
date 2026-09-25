// Transit-AI — k6 baseline load test (T-162)
// 50 VU × 5 min, 3 endpoints round-robin, p95 ≤ 2s, error_rate ≤ 1%.
// Используется для подтверждения что backend держит нормальную нагрузку ЕДЦ.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// SLA пороги (R6 hackathon-rules: p95 ≤ 2000ms, error_rate ≤ 1%)
const SLA_P95_MS = 2000;
const SLA_ERROR_RATE = 0.01;

const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');
const successCounter = new Counter('successful_requests');
const failedCounter = new Counter('failed_requests');

export const options = {
  vus: 50,
  duration: '5m',
  thresholds: {
    // Effective thresholds (for grep / code review):
    //   p(95)<2000
    //   rate<0.01
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

  sleep(1); // 1 req/sec per VU
}
