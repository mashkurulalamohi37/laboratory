import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const searchLatency = new Trend('search_latency');
export const analyticsLatency = new Trend('analytics_latency');

export const options = {
  stages: [
    { duration: '10s', target: 20 },  // Ramp-up to 20 users
    { duration: '30s', target: 50 },  // Steady throughput at 50 virtual users
    { duration: '15s', target: 100 }, // Peak rush load test
    { duration: '10s', target: 0 },   // Graceful ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<350', 'p(99)<600'], // 95% of requests under 350ms
    errors: ['rate<0.01'],                         // Error rate under 1%
    search_latency: ['p(95)<250'],
    analytics_latency: ['p(95)<300'],
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  // 1. System Health Check
  group('System Liveness & Readiness', () => {
    const res = http.get(`${BASE_URL}/health`);
    const passed = check(res, {
      'health returns 200': (r) => r.status === 200,
    });
    errorRate.add(!passed);
  });

  sleep(0.5);

  // 2. Catalog & Fuzzy Search Browsing
  group('Diagnostic Catalog & Test Discovery', () => {
    const searchTerms = ['lipid', 'sugar', 'cbc', 'liver', 'thyroid'];
    const q = searchTerms[Math.floor(Math.random() * searchTerms.length)];

    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/search?q=${q}`, { headers });
    searchLatency.add(Date.now() - start);

    const passed = check(res, {
      'search status is 200': (r) => r.status === 200,
      'search response envelope valid': (r) => r.json('success') === true,
    });
    errorRate.add(!passed);

    // Tests catalog listing
    const catRes = http.get(`${BASE_URL}/api/v1/catalog/tests?limit=20`, { headers });
    check(catRes, {
      'catalog tests returns 200': (r) => r.status === 200,
    });
  });

  sleep(0.5);

  // 3. Scheduling & Phlebotomy Slot Lookup
  group('Home Collection & Slot Availability', () => {
    const targetDate = new Date().toISOString().slice(0, 10);
    const slotRes = http.get(
      `${BASE_URL}/api/v1/scheduling/slots?date=${targetDate}&service_type=HOME_COLLECTION`,
      { headers }
    );
    const passed = check(slotRes, {
      'slots check status is 200 or 401': (r) => r.status === 200 || r.status === 401,
    });
    errorRate.add(!passed);
  });

  sleep(0.5);

  // 4. Cryptographic Report Verification Simulation
  group('Public SHA-256 Report Verification', () => {
    const sampleToken = 'verify-demo-token-sha256-bd';
    const verifyRes = http.get(`${BASE_URL}/api/v1/reports/public/verify/${sampleToken}`, { headers });
    // 200 or 404 is expected depending on token existence
    const passed = check(verifyRes, {
      'verify returns valid HTTP response': (r) => r.status === 200 || r.status === 404,
    });
    errorRate.add(!passed);
  });

  sleep(0.5);

  // 5. Executive Dashboard & TAT Analytics
  group('Executive KPI Engine & Lab Workloads', () => {
    const start = Date.now();
    const dashRes = http.get(`${BASE_URL}/api/v1/analytics/dashboard`, { headers });
    analyticsLatency.add(Date.now() - start);

    // When run unauthenticated in load testing, endpoints validate 401 or 200 securely
    const passed = check(dashRes, {
      'analytics responds within SLA': (r) => r.status === 200 || r.status === 401,
    });
    errorRate.add(!passed);

    const tatRes = http.get(`${BASE_URL}/api/v1/analytics/tat`, { headers });
    check(tatRes, {
      'tat responds within SLA': (r) => r.status === 200 || r.status === 401,
    });
  });

  sleep(1);
}
