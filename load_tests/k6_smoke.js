/**
 * k6_smoke.js — Load testing truck1.eu through k6
 *
 * Tool: k6 (https://k6.io) — Go-based, highly efficient
 * Installation:  brew install k6
 *
 * Load levels (set via --env LEVEL=xxx):
 *
 *  LEVEL=smoke   →  3 VU,  30s  — basic availability check
 *  LEVEL=light   → 10 VU,  2m  — light traffic
 *  LEVEL=normal  → 25 VU,  5m  — realistic load
 *  LEVEL=stress  → 50 VU, 10m  — stress (coordinate with team first!)
 *
 * Execution:
 *   k6 run load_tests/k6_smoke.js
 *   k6 run --env LEVEL=light load_tests/k6_smoke.js
 *   k6 run --env LEVEL=normal --out json=reports/k6_results.json load_tests/k6_smoke.js
 *   k6 run --env LEVEL=stress load_tests/k6_smoke.js
 *
 * Pass thresholds:
 *   http_req_duration p(95) < 3000ms
 *   http_req_failed   rate  < 1%
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// ── Custom metrics ─────────────────────────────────────────────────────────────

const cfChallenges = new Counter('cf_challenges_total');
const serverErrors = new Counter('server_errors_total');
const slowRequests = new Counter('slow_requests_over_3s');
const catalogDuration = new Trend('catalog_response_ms');
const homepageDuration = new Trend('homepage_response_ms');

// ── Load level configuration ───────────────────────────────────────────────────

const LEVELS = {
  smoke:  { vus: 3,  duration: '30s' },
  light:  { vus: 10, duration: '2m'  },
  normal: { vus: 25, duration: '5m'  },
  stress: { vus: 50, duration: '10m' },
};

const level = __ENV.LEVEL || 'smoke';
const cfg = LEVELS[level] || LEVELS.smoke;

console.log(`▶ Load level: ${level.toUpperCase()} — ${cfg.vus} VUs for ${cfg.duration}`);

// ── Test configuration ────────────────────────────────────────────────────────

export const options = {
  vus: cfg.vus,
  duration: cfg.duration,

  // Smooth start and stop (ramp-up / ramp-down)
  stages: [
    { duration: '10s', target: Math.floor(cfg.vus * 0.5) },  // warm-up
    { duration: cfg.duration, target: cfg.vus },              // main load
    { duration: '10s', target: 0 },                           // shutdown
  ],

  // Thresholds — test marked "red" if violated
  thresholds: {
    'http_req_duration':              ['p(95)<3000', 'p(99)<5000'],
    'http_req_failed':                ['rate<0.01'],   // < 1% errors
    'catalog_response_ms':            ['p(95)<3000'],
    'homepage_response_ms':           ['p(95)<2000'],  // homepage should be faster
  },

  // Not clutter output with large number of requests
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// ── Constants ──────────────────────────────────────────────────────────────

const BASE_URL = 'https://www.truck1.eu';

const LOCALES = ['en', 'de', 'pl'];
const BRANDS  = ['volvo', 'man', 'mercedes', 'daf', 'scania'];
const YEARS   = ['2015', '2017', '2018', '2019', '2020'];

const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9',
  'Accept-Encoding': 'gzip, deflate, br',
};

// ── Helper functions ───────────────────────────────────────────────

function randomFrom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function locale() {
  // EN most often (60%), DE 25%, PL 15%
  const r = Math.random();
  if (r < 0.60) return 'en';
  if (r < 0.85) return 'de';
  return 'pl';
}

function checkResponse(res, name) {
  const ok = check(res, {
    [`${name}: status 200/202`]: (r) => r.status === 200 || r.status === 202,
    [`${name}: response time < 5s`]: (r) => r.timings.duration < 5000,
    [`${name}: no server error`]: (r) => r.status < 500,
  });

  if (res.status === 202) {
    cfChallenges.add(1);
  }
  if (res.status >= 500) {
    serverErrors.add(1);
  }
  if (res.timings.duration > 3000) {
    slowRequests.add(1);
  }
  return ok;
}

// ── Main scenario ─────────────────────────────────────────────────────────────

export default function () {
  const loc = locale();

  // Scenario depends on virtual user "type"
  const scenario = Math.random();

  if (scenario < 0.40) {
    // 40%: Browser user — home → catalog → listing
    runBrowserFlow(loc);
  } else if (scenario < 0.65) {
    // 25%: User searchа
    runSearchFlow(loc);
  } else if (scenario < 0.85) {
    // 20%: User filterов
    runFilterFlow(loc);
  } else {
    // 15%: User leasingа
    runLeasingFlow(loc);
  }
}

// ── Scenario: Browser User ───────────────────────────────────────────────────

function runBrowserFlow(loc) {
  group('Browser Flow', function () {

    // Step 1: Homepage
    const home = http.get(`${BASE_URL}/${loc}`, { headers: HEADERS });
    homepageDuration.add(home.timings.duration);
    checkResponse(home, 'Homepage');
    sleep(randomFrom([1, 2, 2, 3]));

    // Step 2: Catalog
    const catalog = http.get(`${BASE_URL}/${loc}/trucks-for-sale`, { headers: HEADERS });
    catalogDuration.add(catalog.timings.duration);
    checkResponse(catalog, 'Catalog');
    sleep(randomFrom([2, 2, 3, 4]));

    // Step 3: Page 2 (pagination) — 50% probability
    if (Math.random() < 0.5) {
      const page2 = http.get(`${BASE_URL}/${loc}/trucks-for-sale?page=2`, { headers: HEADERS });
      checkResponse(page2, 'Catalog page 2');
      sleep(randomFrom([1, 2, 3]));
    }
  });
}

// ── Scenario: Search ─────────────────────────────────────────────────────────

function runSearchFlow(loc) {
  group('Search Flow', function () {

    const brand = randomFrom(BRANDS);

    // Search by brand
    const search = http.get(
      `${BASE_URL}/${loc}/trucks-for-sale?q=${brand}`,
      { headers: HEADERS }
    );
    catalogDuration.add(search.timings.duration);
    checkResponse(search, `Search brand=${brand}`);
    sleep(randomFrom([2, 3, 4]));

    // Optionally refine with year filter
    if (Math.random() < 0.6) {
      const year = randomFrom(YEARS);
      const filtered = http.get(
        `${BASE_URL}/${loc}/trucks-for-sale?q=${brand}&year_from=${year}`,
        { headers: HEADERS }
      );
      catalogDuration.add(filtered.timings.duration);
      checkResponse(filtered, `Search brand+year`);
      sleep(randomFrom([2, 3]));
    }
  });
}

// ── Scenario: Filters ────────────────────────────────────────────────────────

function runFilterFlow(loc) {
  group('Filter Flow', function () {

    // Catalog filtered by year
    const year = randomFrom(YEARS);
    const byYear = http.get(
      `${BASE_URL}/${loc}/trucks-for-sale?year_from=${year}`,
      { headers: HEADERS }
    );
    catalogDuration.add(byYear.timings.duration);
    checkResponse(byYear, 'Filter by year');
    sleep(randomFrom([2, 3, 4, 5]));

    // Body type category
    const categories = ['curtainsider-trucks', 'refrigerated-trucks', 'tipper-trucks', 'box-trucks'];
    const cat = randomFrom(categories);
    const byCat = http.get(
      `${BASE_URL}/${loc}/${cat}`,
      { headers: HEADERS }
    );
    catalogDuration.add(byCat.timings.duration);
    checkResponse(byCat, `Category: ${cat}`);
    sleep(randomFrom([2, 3]));
  });
}

// ── Scenario: Leasing ────────────────────────────────────────────────────────

function runLeasingFlow(loc) {
  group('Leasing Flow', function () {

    const leasing = http.get(
      `${BASE_URL}/${loc}/trucks-for-lease`,
      { headers: HEADERS }
    );
    checkResponse(leasing, 'Leasing catalog');
    sleep(randomFrom([3, 4, 5, 6]));

    // Page 2 leasingа
    const page2 = http.get(
      `${BASE_URL}/${loc}/trucks-for-lease?page=2`,
      { headers: HEADERS }
    );
    checkResponse(page2, 'Leasing page 2');
    sleep(randomFrom([2, 3, 4]));
  });
}

// ── Final summary report ──────────────────────────────────────────────────────

export function handleSummary(data) {
  const req     = data.metrics.http_reqs.values;
  const dur     = data.metrics.http_req_duration.values;
  const failed  = data.metrics.http_req_failed.values;
  const cf      = data.metrics.cf_challenges_total
                    ? data.metrics.cf_challenges_total.values.count : 0;
  const slow    = data.metrics.slow_requests_over_3s
                    ? data.metrics.slow_requests_over_3s.values.count : 0;

  const p95 = dur['p(95)'];
  const p99 = dur['p(99)'];
  const failRate = (failed.rate * 100).toFixed(2);

  const passThreshold = p95 < 3000 && failed.rate < 0.01;

  const lines = [
    '='.repeat(62),
    `  LOAD TEST RESULTS — truck1.eu  [${level.toUpperCase()}]`,
    '='.repeat(62),
    `  Total requests  : ${req.count}`,
    `  Failures        : ${(failed.rate * req.count).toFixed(0)} (${failRate}%)`,
    `  CF challenges   : ${cf}`,
    `  Slow (>3s)      : ${slow}`,
    '',
    `  Avg resp time   : ${dur.avg.toFixed(0)} ms`,
    `  Median (p50)    : ${dur.med.toFixed(0)} ms`,
    `  95th percentile : ${p95.toFixed(0)} ms  ${p95 < 3000 ? '✅' : '❌ (>3000ms)'}`,
    `  99th percentile : ${p99.toFixed(0)} ms  ${p99 < 5000 ? '✅' : '❌ (>5000ms)'}`,
    `  Max resp time   : ${dur.max.toFixed(0)} ms`,
    '',
    `  RESULT: ${passThreshold ? '✅ PASS — site holds under load' : '❌ FAIL — thresholds violated'}`,
    '='.repeat(62),
  ].join('\n');

  console.log('\n' + lines);

  return {
    stdout: lines + '\n',
    'reports/k6_summary.txt': lines + '\n',
  };
}
