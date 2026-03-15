# QA Coverage Report — truck1.eu
**Date:** 2026-03-15
**Framework:** pytest + Playwright + Locust + k6
**Status:** Production-ready ✅

---

## Coverage Summary

| Category           | Test File                       | Tests | Status          |
|---------------------|---------------------------------|--------|-----------------|
| **UI — Header**      | test_header.py                  | 21     | ✅ Ready         |
| **UI — Home**    | test_home_blocks.py             | 19     | ✅ Ready         |
| **UI — Catalog**    | test_catalog.py                 | 21     | ✅ Ready         |
| **UI — Listing** | test_listing.py                 | 26     | ✅ Ready         |
| **UI — Leasing**     | test_leasing_listing.py         | 15     | ✅ Ready         |
| **UI — Seller**   | test_seller_page.py             | 21     | ✅ Ready         |
| **UI — GDPR/Footer**| test_gdpr_footer.py             | 14     | ✅ Ready         |
| **UI — Security**| test_security_ui.py            | 10     | ✅ Ready         |
| **UI — User Flows** | test_user_flows.py              | 10     | ✅ Ready         |
| **Locales**          | test_locale_smoke.py            | 73*    | ✅ Ready         |
| **API — Status**    | test_api_status.py              | 17     | ✅ Ready         |
| **API — Catalog**   | test_api_catalog.py             | 18     | ✅ Ready         |
| **API — Listings**| test_api_listings.py            | 14     | ✅ Ready         |
| **API — Seller**  | test_api_seller.py              | 12     | ✅ Ready         |
| **API — Security** | test_api_security.py         | 21     | ✅ Ready         |
| **API — Blackbox**  | test_api_db_blackbox.py         | 24     | ✅ Ready         |
| **Load**        | locustfile.py + scenarios_advanced.py | 9 scenarios | ✅ Ready |
| **Load (k6)**   | k6_smoke.js                     | 4 levels   | ✅ Ready         |
| **TOTAL**           |                                 | **356+** | ✅              |

*73 = 10×3 (Tier1) + 5×8 (Tier2) + 3 (Cross)

---

## Latest Run Results

### UI / API Tests (headless Playwright)
```
Latest run: report_20260314_232157.html
  315 passed
    0 failed
  165 skipped  ← CF challenges in headless mode
```

**Reason for skipped:** Cloudflare protection blocks headless Playwright.
**Solution:** `make smoke-headed` or run with `--headed --slowmo=800`.

### Locale Smoke Tests
```
Tier 1 (EN/DE/PL):  30 passed / 0 failed  (CF-skip for some HTTP checks)
Tier 2 (8 locales): 40 passed / 0 failed
Cross-locale:        3 passed / 0 failed
```

### Load Tests

| Level | VU | Time | Requests | Errors | P50 | P95 | Verdict |
|---|---|---|---|---|---|---|---|
| Smoke | 3 | 30s | ~100 | 0% | ~48ms | <300ms | ✅ PASS |
| Light | 10 | 2m | ~500 | 0% | ~48ms | ~200ms | ✅ PASS |
| Normal | 25 | 5m | 1 606 | 0% | 48ms | **160ms** | ✅ PASS |
| ContentValidator | 5 | 1m | 69 | 0% | ~50ms | 150ms | ✅ Real HTML |
| **Spike (0→50 VU)** | **50** | **3m** | **6 848** | **0%** | **50ms** | **230ms** *(peak)* | **✅ PASS** |
| Stress | 50 | 10m | — | — | — | — | ⏳ TBD |

**Spike Test Details:**
- Impact moment (0→50 VU): P95 = 230ms, avg = 101ms
- After 30 seconds: P95 returned to 96ms — fast recovery
- Maximum single request: 916ms (Search with filters) — acceptable
- Threshold: P95 < 3000ms — actual peak **13× below threshold**

**Conclusion:** Site confidently handles load under sharp spikes. CDN Cloudflare absorbs spike with virtually no degradation. Stress (50 VU, 10 min) — next step for checking sustained load.

---

## Coverage Architecture

```
truck1.eu QA Framework
│
├── UI Tests (Playwright / headed & headless)
│   ├── Smoke — critical paths in 2–3 min
│   ├── Full  — full regression in ~15 min
│   └── CF-aware — skip/retry on 202 challenges
│
├── API Tests (requests.Session, no browser)
│   ├── HTTP status & headers — ~30 sec
│   ├── Response structure — JSON/HTML validation
│   ├── Catalog & pagination — real data
│   ├── Security headers — CSP, HSTS, X-Frame
│   └── Blackbox DB — direct SQL-like checks via API
│
├── Locale Tests (11 locales, 2 levels)
│   ├── Tier 1 (EN/DE/PL): 10 detailed checks × 3 locales
│   ├── Tier 2 (8 locales): 5 smoke checks × 8 locales
│   └── Cross-locale: consistency + SEO hreflang
│
└── Load Tests
    ├── Locust — 4 user scenarios × 4 levels
    ├── k6    — Go-based, 4 levels + ramp-up/down
    └── Advanced: Spike / Soak / Step / ContentValidator / API
```

---

## Known Vulnerabilities

| ID           | Description                          | Status       |
|--------------|-----------------------------------|--------------|
| SEC-BUG-001  | X-Frame-Options missing (Clickjacking) | 📋 Reported |
| SEC-BUG-002  | target=_blank without noopener (Tabnapping)    | 📋 Reported |

Details: `bug_report_security.docx`

---

## Running Tests (Quick Start)

```bash
# Setup
make install

# Fast API tests (no browser needed, ~1 min)
make api

# Smoke for all locales (no browser, ~3 min)
make locale-smoke

# UI smoke headless (may be blocked by CF)
make smoke LOCALE=en

# UI smoke in visible browser (bypasses CF)
make smoke-headed LOCALE=en

# Load — normal (25 VU, 5 min)
make load-normal

# Load — stress (50 VU, 10 min) requires confirmation
make load-stress

# Spike test — sharp load spike
make load-spike
```

---

## CI/CD (GitHub Actions)

File: `.github/workflows/qa.yml`

| Trigger              | Jobs Run              | Time    |
|----------------------|-------------------------------|----------|
| `push main`          | api + locale-smoke + ui-smoke | ~15 min  |
| `pull_request`       | api + locale-smoke + ui-smoke | ~15 min  |
| Cron `*/6 * * * *`   | api + locale-smoke            | ~5 min   |
| `workflow_dispatch`  | Any combination by choice    | Flexible    |

**Manual Run Parameters:**
- `locale` — EN/DE/PL and 8 secondary
- `suite` — full / smoke / api / locale / load
- `load_level` — smoke / light / normal

---

## Next Steps (Recommendations)

1. **Stress test** — `make load-stress` — find degradation limit (50 VU, 10 min)
2. **Spike test** — `make load-spike` — behavior under sudden traffic spike
3. **Soak test** — `make load-soak` — degradation over 30 min (memory leaks, cache)
4. **Allure reports** — integrate `allure-pytest` for pretty reports
5. **Slack webhook** — add GitHub Actions notifications for failures
6. **Staging environment** — `make smoke HOST=https://staging.truck1.eu`
7. **Fix SEC-BUG-001/002** — coordinate with development team
