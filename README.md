# truck1.eu — QA Automation Framework

[![QA Suite](https://github.com/yaromindzmitry/truck-QA-Automation-Framework/actions/workflows/qa.yml/badge.svg)](https://github.com/yaromindzmitry/truck-QA-Automation-Framework/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://python.org)
[![Playwright](https://img.shields.io/badge/playwright-1.50-green)](https://playwright.dev)
[![pytest](https://img.shields.io/badge/pytest-8.3-orange)](https://pytest.org)
[![Locust](https://img.shields.io/badge/locust-2.32-red)](https://locust.io)
[![Ruff](https://img.shields.io/badge/linter-ruff-black)](https://github.com/astral-sh/ruff)

Black-box QA framework for [truck1.eu](https://www.truck1.eu) — one of Europe's largest commercial truck sales platforms. Covers UI, API, locale, security, and load testing.

---

## Why This Project

This is not a tutorial CRUD. truck1.eu is a real public website with:
- **11 language locales** (EN, DE, PL, and 8 other markets)
- **Cloudflare protection** against bots, affecting headless testing
- **Real findings**: 2 security issues identified and documented
- **Load tests** verified with data: 50 VU spike, 0 errors

The goal is to demonstrate an approach to black-box testing of a production website where there's no access to source code, staging, or test environment.

---

## Actual Coverage Status

> Honest assessment is more important than round numbers.

### What Works Stably in CI (headless)

| Group | Tests | CI Status |
|---|---|---|
| API tests (requests, no browser) | 106 | ✅ Stable |
| Locale smoke Tier 1 — EN/DE/PL | 30 | ✅ Stable |
| Locale smoke Tier 2 — 8 locales | 40 | ✅ Stable |
| Cross-locale consistency | 3 | ✅ Stable |
| **Total headless-stable** | **179** | **✅** |

### UI tests (Playwright, headless — partially blocked by CF)

| Module | Tests | Headless | Headed |
|---|---|---|---|
| Header | 21 | ⚠️ CF-skip | ✅ |
| Home blocks | 19 | ⚠️ CF-skip | ✅ |
| Catalog | 21 | ⚠️ CF-skip | ✅ |
| Listing page | 26 | ⚠️ CF-skip | ✅ |
| Leasing listing | 15 | ⚠️ CF-skip | ✅ |
| Seller page | 21 | ⚠️ CF-skip | ✅ |
| GDPR / Footer | 14 | ✅ Stable | ✅ |
| Security UI | 10 | ✅ Stable | ✅ |
| User Flows | 10 | ⚠️ CF-skip | ✅ |
| **UI Total** | **157** | **~30 stable** | **~157** |

**⚠️ CF-skip** = Cloudflare returns a challenge page for headless. The test doesn't break — it's correctly marked `SKIP`. Solution: `make smoke-headed`.

### Load Test Scenarios

| File | Scenarios | Levels |
|---|---|---|
| locustfile.py | 4 user classes | Smoke / Light / Normal / Stress |
| scenarios_advanced.py | 5 scenarios | Spike / Soak / Step / Validate / API |
| k6_smoke.js | 4 flows | Smoke / Light / Normal / Stress |

---

## Bugs Found

> Tests don't just pass — they find problems.

| ID | Level | Description | File |
|---|---|---|---|
| SEC-BUG-001 | 🔴 Medium | `X-Frame-Options` missing — site can be embedded in a frame (Clickjacking) | [bug_report_security.docx](bug_report_security.docx) |
| SEC-BUG-002 | 🟡 Low | `target=_blank` without `rel="noopener noreferrer"` — risk of Tabnapping attack | [bug_report_security.docx](bug_report_security.docx) |
| UF-BUG-001 | ℹ️ Info | Logo links to `https://www.truck1.eu/` (root), not `/en/` — depends on cookie locale | Documented in test UF09 |
| FOOT-BUG-001 | ℹ️ Info | Footer: 6 `<a>` links without `href` (onclick navigation) — accessibility issue | [test_gdpr_footer.py](tests/test_gdpr_footer.py) |

---

## Known Limitations

An honest list of what to consider:

**Cloudflare (main limitation)**
Headless Playwright triggers CF bot-challenge (HTTP 202 + JS page). Most UI tests only work in `--headed` mode or require a real browser. In CI, tests are correctly marked `SKIP`, not `FAIL`.

**No Access to Staging**
All tests run against production `www.truck1.eu`. This means: dependency on real data, instability during planned site updates, inability to test forms with real submission.

**A/B Tests and Regional Differences**
truck1.eu actively uses A/B tests. Some UI elements may be absent on a specific locale. The test uses `pytest.skip()` instead of `pytest.fail()` — this is a deliberate choice.

**Dynamic Locators**
Selectors are built with fallback chains, but after layout updates, some tests may need locator updates. This is normal for black-box testing of a public website.

**Load Tests**
Stress (50 VU, 10m) and Soak (30m) tests run only manually with explicit confirmation — to avoid creating real production load without coordination.

---

## Load Test Results

| Level | VU | Time | Requests | Errors | P50 | P95 | Verdict |
|---|---|---|---|---|---|---|---|
| Smoke | 3 | 30s | ~100 | 0% | ~48ms | <300ms | ✅ PASS |
| Light | 10 | 2m | ~500 | 0% | ~48ms | ~200ms | ✅ PASS |
| Normal | 25 | 5m | 1 606 | 0% | 48ms | **160ms** | ✅ PASS |
| **Spike** | **0→50** | **3m** | **6 848** | **0%** | **50ms** | **230ms** *(peak)* | **✅ PASS** |
| Stress | 50 | 10m | — | — | — | — | ⏳ TBD |

Threshold: P95 < 3000ms, Fail rate < 1%. CDN Cloudflare explains the low P50 (~48ms) — most pages are served from edge nodes.

---

## Project Structure

```
truck1_qa/
├── pages/                       # Page Object Model
│   ├── base_page.py             # Base locators and utilities
│   ├── home_page.py
│   ├── catalog_page.py
│   ├── listing_page.py
│   ├── leasing_listing_page.py
│   └── seller_page.py
│
├── api/                         # API tests (requests, no browser)
│   ├── client/
│   │   ├── base_client.py       # requests.Session + Retry + logging
│   │   ├── listings_client.py
│   │   └── search_client.py
│   ├── models/
│   │   └── response_schemas.py  # Dataclass response schemas
│   └── tests/
│       ├── test_api_status.py   # HTTP status, headers, response time
│       ├── test_api_catalog.py  # Catalog, filters, XSS/SQLi
│       ├── test_api_listings.py # Listings, forms, meta
│       ├── test_api_seller.py   # Seller pages
│       ├── test_api_security.py # Security headers
│       └── test_api_db_blackbox.py
│
├── tests/                       # UI tests (Playwright)
│   ├── test_header.py
│   ├── test_home_blocks.py
│   ├── test_catalog.py
│   ├── test_listing.py
│   ├── test_leasing_listing.py
│   ├── test_seller_page.py
│   ├── test_gdpr_footer.py
│   ├── test_security_ui.py
│   ├── test_user_flows.py
│   └── test_locale_smoke.py     # 11 locales, 2 tiers
│
├── load_tests/
│   ├── locustfile.py            # 4 scenarios: Browser/Search/Filter/Leasing
│   ├── scenarios_advanced.py    # Spike / Soak / Step / ContentValidator / API
│   └── k6_smoke.js             # k6 alternative: 4 levels + custom metrics
│
├── utils/
│   └── helpers.py
│
├── .github/workflows/
│   └── qa.yml                   # CI: api + locale + ui-smoke + security + load
│
├── Makefile                     # All commands in one place
├── CONTRIBUTING.md              # How to extend the framework
├── QA_COVERAGE_REPORT.md        # Detailed report with results
├── pyproject.toml               # ruff configuration
├── .pre-commit-config.yaml      # pre-commit hooks
├── .env.example                 # Environment variables template
├── .gitignore
├── conftest.py
├── pytest.ini
└── requirements.txt
```

---

## Quick Start

```bash
git clone https://github.com/yaromindzmitry/truck-QA-Automation-Framework.git
cd truck-QA-Automation-Framework
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env

# Check that everything works (~1 min, no browser)
make api
```

### Main Commands

```bash
make help              # All available commands

# No browser — stable in CI
make api               # API tests (~1 min)
make locale-smoke      # All 11 locales (~3 min)
make locale-tier1      # Only EN/DE/PL

# UI — --headed recommended to bypass CF
make smoke-headed      # UI smoke with browser
make smoke LOCALE=de   # UI smoke headless (some will SKIP)
make full LOCALE=en    # Full regression

# Load testing
make load-normal       # 25 VU, 5 min (safe)
make load-spike        # 0→50 VU sharp (safe, 3 min)
make load-stress       # 50 VU, 10 min (requires confirmation)
```

---

## CI/CD

File: `.github/workflows/qa.yml`

| Trigger | Jobs | Time |
|---|---|---|
| `push main` / `pull_request` | api + locale-smoke + ui-smoke (EN/DE/PL) | ~15 min |
| Cron every 6 hours | api + locale-smoke | ~5 min |
| `workflow_dispatch` | Choice: suite / locale / load_level | Flexible |

---

## Technology Stack

- **Python 3.11** + pytest 8.3 + playwright 1.50
- **pytest-xdist** — parallel test execution
- **pytest-rerunfailures** — auto-retry unstable tests
- **Locust 2.32** + k6 — load testing
- **Ruff** — linting and formatting
- **pre-commit** — hooks for secret and code quality protection
- **GitHub Actions** — CI/CD
- **allure-pytest** — extended reports (optional)

---

## Extending the Framework

See [CONTRIBUTING.md](CONTRIBUTING.md):
- How to add a Page Object
- How to add a test (with examples)
- CF-guard pattern
- How to add a locale
- Debugging a failed test
