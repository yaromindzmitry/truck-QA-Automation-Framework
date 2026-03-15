"""
conftest.py — global pytest fixtures for truck1.eu QA framework.

Architecture:
  - browser / page fixtures via pytest-playwright  (UI tests)
  - API clients via requests.Session               (API tests)
  - locale parametrization via --locale CLI option
  - interception of console errors and network requests
"""

from datetime import datetime
import os

from dotenv import load_dotenv
import pytest

from api.client import ListingsClient, SearchClient

try:
    from playwright.sync_api import BrowserContext, Page
except ImportError:
    Page = None  # type: ignore[assignment,misc]
    BrowserContext = None  # type: ignore[assignment,misc]

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://www.truck1.eu")

# ── Locales truck1.eu ──────────────────────────────────────────────────────────
# Tier 1: main markets — full test suite
TIER1_LOCALES = ["en", "de", "pl"]

# Tier 2: secondary markets — smoke tests only (test_locale_smoke.py)
TIER2_LOCALES = ["lt", "lv", "ee", "ru", "cs", "sk", "ro", "bg"]

# All supported locales
LOCALES = TIER1_LOCALES + TIER2_LOCALES


def pytest_configure(config):
    """Generate unique report name with timestamp on each run."""
    if not config.option.htmlpath:
        os.makedirs("reports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        config.option.htmlpath = f"reports/report_{ts}.html"


def pytest_addoption(parser):
    parser.addoption(
        "--locale",
        action="store",
        default="en",
        choices=LOCALES,
        help=(
            "Site locale for UI/API tests (default: en). "
            "Tier 1 (full suite): en, de, pl. "
            "Tier 2 (smoke only): lt, lv, ee, ru, cs, sk, ro, bg. "
            "For multi-locale smoke use: pytest tests/test_locale_smoke.py"
        ),
    )
    parser.addoption(
        "--base-url-override",
        action="store",
        default=None,
        help="Override base URL (e.g. for staging: https://staging.truck1.eu)",
    )


@pytest.fixture(scope="session")
def base_url(request):
    override = request.config.getoption("--base-url-override")
    return override if override else BASE_URL


@pytest.fixture(scope="session")
def locale(request):
    return request.config.getoption("--locale")


@pytest.fixture(scope="session")
def locale_url(base_url, locale):
    """Returns locale-prefixed base URL, e.g. https://www.truck1.eu/en"""
    return f"{base_url}/{locale}"


# ─── Playwright browser config ────────────────────────────────────────────────


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezone_id": "Europe/Warsaw",
        "ignore_https_errors": True,
    }


CF_TITLES = ("just a moment", "attention required", "checking your browser")


def _is_cloudflare_blocked(page) -> bool:
    """Return True if Cloudflare challenge page is shown."""
    title = page.title().lower()
    return any(t in title for t in CF_TITLES)


@pytest.fixture
def page(context: BrowserContext, locale_url: str) -> Page:
    """
    Override standard page fixture:
    - open page immediately on correct locale
    - collect console errors
    - accept GDPR cookies (if banner appears)
    - skip test if Cloudflare blocks headless browser
    """
    page = context.new_page()
    console_errors = []

    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    page.goto(locale_url, wait_until="domcontentloaded", timeout=30_000)

    if _is_cloudflare_blocked(page):
        page.close()
        pytest.skip("Cloudflare challenge page — skipped in headless CI")

    # Close GDPR popup if present
    _accept_gdpr(page)

    page._console_errors = console_errors  # available in tests
    yield page
    page.close()


def _accept_gdpr(page: Page):
    """Click 'Accept' on GDPR banner if displayed."""
    try:
        accept_btn = page.locator(
            "button:has-text('Accept'), button:has-text('Accept all'), "
            "[data-testid='gdpr-accept'], .gdpr-accept, #gdpr-consent-accept"
        ).first
        if accept_btn.is_visible(timeout=3_000):
            accept_btn.click()
            page.wait_for_load_state("networkidle", timeout=5_000)
    except Exception:
        pass  # GDPR banner did not appear — continue


# ─── Helper fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def listing_page_url(base_url, locale):
    """URL of first truck for sale listing."""
    return f"{base_url}/{locale}/trucks-for-sale"


@pytest.fixture
def leasing_page_url(base_url, locale):
    """URL of leasing page."""
    return f"{base_url}/{locale}/trucks-for-lease"


@pytest.fixture
def catalog_url(base_url, locale):
    return f"{base_url}/{locale}/trucks-for-sale"


@pytest.fixture
def seller_page_url(base_url, locale):
    return f"{base_url}/{locale}/dealers"


# ─── API fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def api_client(base_url, locale):
    """
    HTTP client for API tests (function scope).
    Created fresh for each test — isolated session.
    """
    return ListingsClient(base_url=base_url, locale=locale)


@pytest.fixture(scope="module")
def api_client_module(base_url, locale):
    """
    HTTP client with module scope — reused within module.
    Used for expensive fixtures (fetching real listing ID).
    """
    return ListingsClient(base_url=base_url, locale=locale)


@pytest.fixture(scope="function")
def search_client(base_url, locale):
    """HTTP client for search and navigation requests."""
    return SearchClient(base_url=base_url, locale=locale)


@pytest.fixture(scope="session")
def api_locale(locale):
    """Proxy fixture: passes locale to API tests."""
    return locale


# ─── Hooks ───────────────────────────────────────────────────────────────────


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Take screenshot on test failure."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page:
            os.makedirs("reports/screenshots", exist_ok=True)
            screenshot_path = (
                f"reports/screenshots/{item.nodeid.replace('/', '_').replace('::', '__')}.png"
            )
            try:
                page.screenshot(path=screenshot_path, full_page=True)
                report.extra = getattr(report, "extra", [])
            except Exception:
                pass
