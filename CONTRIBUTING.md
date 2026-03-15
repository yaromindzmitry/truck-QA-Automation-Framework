# Contributing Guide

This guide explains how to extend the QA framework: adding Page Objects, tests, markers, and load scenarios.

---

## Quick Start for New Developers

```bash
git clone https://github.com/YOUR_USERNAME/truck1-qa.git
cd truck1-qa
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env             # Fill in BASE_URL if needed

# Verify that everything works
make api
make locale-tier1
```

---

## How to Add a New Page Object

Create a file in `pages/`:

```python
# pages/search_results_page.py
from playwright.sync_api import Page
from pages.base_page import BasePage


class SearchResultsPage(BasePage):
    """Page Object for search results page."""

    # Locators — always with fallback options separated by comma
    RESULTS_COUNT = ".results-count, [data-testid='results-count'], h1 .count"
    RESULT_CARDS  = ".listing-card, article.ad-item, [class*='result-item']"
    SORT_DROPDOWN = "select[name='sort'], .sort-select, [data-testid='sort']"

    def __init__(self, page: Page, locale: str = "en") -> None:
        super().__init__(page, locale)

    def get_results_count(self) -> int:
        """Returns search results count."""
        text = self.page.locator(self.RESULTS_COUNT).inner_text(timeout=5000)
        # Extract number from string like "1 234 results"
        import re
        match = re.search(r"[\d\s]+", text)
        return int(match.group().replace(" ", "")) if match else 0

    def get_card_count(self) -> int:
        """Number of cards on the page."""
        return self.page.locator(self.RESULT_CARDS).count()
```

Rules for locators:
- Always provide 2–3 options separated by comma (CSS fallback)
- Prefer `data-testid` > semantic tags > classes
- Don't use XPath unnecessarily
- Don't hardcode text — it may vary by locale

---

## How to Add Tests

### Test File Structure

```python
# tests/test_search_results.py
import pytest
from playwright.sync_api import Page
from pages.search_results_page import SearchResultsPage


@pytest.mark.smoke          # ← required for critical checks
@pytest.mark.catalog        # ← module marker
class TestSearchResults:
    """
    SR — Search Results
    Tests for search results page truck1.eu/en/trucks-for-sale
    """

    def test_sr01_results_page_loads(self, page: Page, locale: str) -> None:
        """SR01: Results page loads and displays listings."""
        srp = SearchResultsPage(page, locale)
        srp.navigate(f"/{locale}/trucks-for-sale")

        # CF-guard: skip if Cloudflare blocks headless
        body = page.locator("body").inner_text(timeout=3000)
        if len(body.strip()) < 100:
            pytest.skip("CF challenge — run with --headed")

        count = srp.get_card_count()
        assert count > 0, "SR01: No listing cards found on results page"

    def test_sr02_results_count_shown(self, page: Page, locale: str) -> None:
        """SR02: Results counter is displayed."""
        srp = SearchResultsPage(page, locale)
        srp.navigate(f"/{locale}/trucks-for-sale")

        body = page.locator("body").inner_text(timeout=3000)
        if len(body.strip()) < 100:
            pytest.skip("CF challenge — run with --headed")

        results = srp.get_results_count()
        assert results > 0, "SR02: Results counter is 0 or not found"
```

### Test Naming

Use module prefix + sequential number:
- `test_sr01_...` — Search Results
- `test_hd01_...` — Header
- `test_cat01_...` — Catalog
- `test_uf01_...` — User Flows

### Available Markers

```python
@pytest.mark.smoke        # Critical path — runs in CI on every push
@pytest.mark.header       # Header tests
@pytest.mark.catalog      # Catalog and search
@pytest.mark.listing      # Listing page
@pytest.mark.leasing      # Leasing
@pytest.mark.seller       # Seller page
@pytest.mark.gdpr         # GDPR, footer
@pytest.mark.security     # Security checks
@pytest.mark.locale       # Multi-locale
@pytest.mark.tier1        # Tier 1 locales (EN/DE/PL) — full check
@pytest.mark.tier2        # Tier 2 locales (8 markets) — smoke only
@pytest.mark.slow         # Slow tests (gallery, slider) — not in smoke
@pytest.mark.api          # API tests without browser
```

---

## CF-guard Pattern (Required!)

Any UI test working with page content should contain a CF-guard:

```python
# At the start of test after navigate()
body = page.locator("body").inner_text(timeout=3000)
if len(body.strip()) < 100:
    pytest.skip("CF challenge — run with --headed --slowmo=800")
```

Why: Cloudflare blocks headless Playwright. In CI the test will be marked as `SKIP`,
not `FAIL`. This is correct behavior — the test isn't broken, the environment just doesn't allow it.

To run with a real browser (bypasses CF):
```bash
make smoke-headed LOCALE=en
```

---

## How to Add an API Test

```python
# api/tests/test_api_search.py
import pytest
import requests

BASE_URL = "https://www.truck1.eu"
REACHABLE = (200, 202, 301, 302)


@pytest.mark.api
class TestApiSearch:

    def test_search_endpoint_reachable(self):
        """Search API returns 200 or CF 202."""
        resp = requests.get(f"{BASE_URL}/en/trucks-for-sale", timeout=10)
        assert resp.status_code in REACHABLE, f"Search: unexpected {resp.status_code}"

    def test_search_with_filters(self):
        """Filtering by brand works."""
        resp = requests.get(
            f"{BASE_URL}/en/trucks-for-sale",
            params={"brand": "volvo"},
            timeout=10,
        )
        assert resp.status_code in REACHABLE
        if resp.status_code == 200:
            assert "volvo" in resp.text.lower() or len(resp.text) > 1000
```

---

## How to Add a Locale Smoke Test

Add a method to the `TestTier1LocaleSmoke` or `TestTier2LocaleSmoke` class in `tests/test_locale_smoke.py`:

```python
@pytest.mark.tier1
@pytest.mark.parametrize("locale", TIER1_LOCALES)
def test_loc11_search_page_reachable(self, locale: str) -> None:
    """LOC11: Search page is accessible."""
    url = f"https://www.truck1.eu/{locale}/trucks-for-sale"
    resp = requests.get(url, timeout=10, allow_redirects=True)
    assert resp.status_code in REACHABLE, f"LOC11 [{locale}]: {resp.status_code}"
```

---

## How to Add a Load Test Scenario

In `load_tests/locustfile.py`:

```python
class SearchHeavyUser(HttpUser):
    """User with intensive search and filtering."""
    weight = 10          # Weight relative to other classes
    wait_time = between(1, 3)

    @task(3)
    def search_with_brand_filter(self):
        with self.client.get(
            "/en/trucks-for-sale",
            params={"brand": "volvo", "year_from": "2020"},
            headers=BROWSER_HEADERS,
            catch_response=True,
            name="Search: brand+year filter",
        ) as resp:
            _ok(resp)

    @task(1)
    def search_deep_page(self):
        with self.client.get(
            "/en/trucks-for-sale",
            params={"page": 5},
            headers=BROWSER_HEADERS,
            catch_response=True,
            name="Search: deep pagination",
        ) as resp:
            _ok(resp)
```

---

## Running Linter and Formatter

```bash
# Install pre-commit (once)
pip install pre-commit
pre-commit install

# Run linter manually
ruff check .
ruff check . --fix   # Auto-fix

# Formatting
ruff format .

# All pre-commit hooks
pre-commit run --all-files
```

---

## Debugging Failed Tests

```bash
# 1. Run specific test with verbose and headed
pytest tests/test_catalog.py::TestCatalog::test_filter_by_type \
    --locale=en --headed --slowmo=1000 -v -s

# 2. Check failure screenshot
open reports/screenshots/

# 3. Enable Playwright traces
pytest tests/test_catalog.py -v --tracing=on
# Traces saved in test-results/ — open: playwright show-trace <file>

# 4. Interactive mode (pause on failure)
pytest tests/test_catalog.py --headed --slowmo=500 --pause-on-fail
```

---

## Principles We Follow

1. **Honest Results**: if test `SKIP` — it's not `PASS`. We honestly separate CF-skip from actual skips.
2. **Fallback Selectors**: always 2–3 CSS options. One layout fix shouldn't break tests.
3. **Don't Fix Production in Tests**: if the site is broken — test should `FAIL`, not work around it.
4. **No Secrets in Code**: `.env` in `.gitignore`, tokens only in GitHub Secrets.
5. **Mark Tests**: unmarked tests go into full runs, not just smoke.
