# Claude Code Agent — Prompts for Generating truck1.eu Tests

This file contains ready-to-use prompts for the Claude Code agent
when developing and extending the test suite.

---

## Prompt 1: Page Exploration and Page Object Generation

```
Go to https://www.truck1.eu/en/trucks-for-sale
and explore the listings catalog page.

Your task:
1. Identify all interactive elements: buttons, links, filters, input fields
2. Record CSS selectors and data-attributes for each element
3. Generate a Python CatalogPage class following Page Object Model
   using playwright.sync_api
4. Add methods: get_*, click_*, fill_*, apply_filter_*
5. Save the result to pages/catalog_page.py

Code requirements:
- Use multiple fallback selectors separated by comma
- All public methods should return self or Locator
- Docstring on every method
```

---

## Prompt 2: Test Case Generation from Checklist

```
I have a Page Object class for a truck listing page:
[paste contents of pages/listing_page.py]

Generate a complete test file tests/test_listing.py for pytest + playwright.

Test cases should cover:
- Display of all information blocks (photos, price, specs)
- All buttons working (favorites, compare, share)
- Contact form: empty submission, invalid email, valid data
- Breadcrumbs and back navigation
- Link to seller page

Requirements:
- TestListingPage class with @pytest.mark.listing and @pytest.mark.smoke markers
- Fixture autouse=True to open first listing from catalog
- pytest.skip() if element not found (this is a black-box test)
- Comment TC_LIST01...TC_LIST_N on each test
- Use fixtures from conftest.py: page, catalog_url, locale
```

---

## Prompt 3: Failed Test Analysis and Fix Proposal

```
Here is a failed test from our pytest-playwright framework for truck1.eu:

[paste traceback]

Current locator: [paste locator]

Go to https://www.truck1.eu/en and find the current selector
for this element. Propose:
1. Fixed locator (primary + fallback)
2. Explanation of why the old one broke
3. Updated test code
```

---

## Prompt 4: Coverage Extension for a New Feature

```
A new section has appeared on https://www.truck1.eu: [section name].

Explore this section and:
1. Add new Page Object class pages/[name]_page.py
2. Create test file tests/test_[name].py with coverage:
   - All visible elements are displayed
   - All buttons are clickable without errors
   - Forms pass basic validation
3. Add new pytest marker to pytest.ini
4. Update conftest.py if new fixtures are needed
5. Add new job to .github/workflows/ci.yml
```

---

## Prompt 5: Local Report Generation

```
After running tests I have file reports/report.html
and folder reports/screenshots/ with screenshots of failed tests.

Analyze the results and produce:
1. Brief summary: passed/failed/skipped per module
2. Top 5 most frequently failing tests
3. Error grouping by type (element not found / timeout / assertion)
4. Recommendations for stabilizing flaky tests
5. Save to reports/analysis.md
```

---

## Example Session: Agent Generates Test, Framework Runs It

### Step 1 — Agent explores and writes code:
```bash
claude "Explore https://www.truck1.eu/en/trucks-for-sale
        and generate pytest tests to verify filters.
        Save to tests/test_filters_generated.py"
```

### Step 2 — Deterministic framework run:
```bash
pytest tests/test_filters_generated.py -v --locale=en
```

### Step 3 — Agent analyzes failed tests:
```bash
claude "Analyze reports/report.html and propose fixes
        for failed tests in test_filters_generated.py"
```

### Step 4 — CI/CD runs the final version:
```bash
# Automatically via GitHub Actions on push to main
```

---

## Principle: Agent = Test Developer, pytest = Runner

| Task                        | Agent  | pytest |
|-----------------------------|--------|--------|
| Explore UI                  | ✅     | ❌     |
| Write / update code         | ✅     | ❌     |
| Deterministic test run      | ❌     | ✅     |
| CI/CD integration           | ❌     | ✅     |
| Results analysis            | ✅     | ❌     |
| History / trends            | ❌     | ✅     |
