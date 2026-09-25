// Transit-AI — k6 smoke load test (T-160)
// 10 VU × 30s against /api/v1/predictions/stop/{id}
// R6 SLA: p95 ≤ 2000ms, error_rate ≤ 1%

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// === Custom metrics для графиков ===
const dispatchLatency = new Trend('dispatch_latency_ms', true);
const errorRate = new Rate('errors');
const successCounter = new Counter('successful_requests');
const failedCounter = new Counter('failed_requests');

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'http_req_duration': ['p(95)<2000'], // R6 SLA
    'http_req_failed': ['rate<0.01'],
    errors: ['rate<0.01'],
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
        const body = JSON.parse(r.body);
        return Array.isArray(body.data);
      } catch (e) {
        return false;
      }
    },
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
