// Transit-AI — k6 spike load test (T-162)
// Резкий скачок 10 VU → 200 VU за 10 сек, удержание 1 мин, возврат к 10 VU.
// p95 ≤ 4s, error_rate ≤ 2%. Используется для проверки resilience и recovery.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// SLA пороги для spike (максимальный допуск)
const SLA_P95_MS = 4000;
const SLA_ERROR_RATE = 0.02;

const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');
const successCounter = new Counter('successful_requests');
const failedCounter = new Counter('failed_requests');

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // baseline (warm-up)
    { duration: '10s', target: 200 }, // резкий spike 10 → 200 VU
    { duration: '1m', target: 200 },  // удержание пика
    { duration: '10s', target: 10 },  // быстрый спад
    { duration: '30s', target: 10 },  // recovery (recovery check)
  ],
  thresholds: {
    // Effective thresholds (for grep / code review):
    //   p(95)<4000
    //   rate<0.02
    'http_req_duration': [`p(95)<${SLA_P95_MS}`],
    'http_req_failed': [`rate<${SLA_ERROR_RATE}`],
    'errors': [`rate<${SLA_ERROR_RATE}`],
  },
};

const BASE_URL = __ENV.BACKEND_URL || 'http://localhost:8000';
const STOP_IDS = Array.from({ length: 50 }, (_, i) => i + 1);

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

  sleep(0.3);
}
