"""
BasePage — base class for all Page Objects.

Contains:
  - common locators (header, footer, GDPR)
  - navigation utilities
  - element waiting methods
"""

import re

from playwright.sync_api import Locator, Page, expect


class BasePage:
    # ─── Constants ────────────────────────────────────────────────────────────────
    DEFAULT_TIMEOUT = 10_000  # ms

    # ─── Header locators ──────────────────────────────────────────────────────────
    # FIXED per report.html data: site uses v3-c-* classes and data-event-click
    HEADER = "header, [class*='v3-c-header'], [class*='header'], [id*='header']"
    LOGO = (
        "a[href='/'], a[href*='truck1'] img, "
        "[class*='v3-c-logo'] img, [class*='v3-c-logo'] a, "
        ".logo img, [class*='logo'] img"
    )
    # Catalogue — not found by text in report; trying data-event-click and href
    NAV_CATALOGUE = (
        "[data-event-click*='catalogue'], [data-event-click*='catalog'], "
        "a:has-text('Catalogue'), a:has-text('Catalog'), "
        "[href*='trucks-for-sale'], [href*='catalog']"
    )
    SEARCH_INPUT = (
        "input[type='search'], input[name='kw'], input[name='q'], "
        "input[placeholder*='Search'], input[placeholder*='search'], "
        "[class*='v3-c-search'] input, [class*='search'] input"
    )
    BTN_PLACE_AD = (
        "a:has-text('Place an ad'), a:has-text('Add advert'), "
        "[data-event-click*='place_ad'], [data-event-click*='add_advert'], "
        "[href*='place-ad'], [href*='add-advert'], [href*='place_ad']"
    )
    # FIXED: button is called "Sellers", not "Sell" (from log: >Sellers</a>)
    BTN_SELL = (
        "a:has-text('Sellers'), button:has-text('Sellers'), "
        "[data-event-click*='seller'], [data-event-click*='sell'], "
        "a:has-text('Sell your'), [href*='sell']"
    )
    # FIXED: site does not use href/aria-label with 'favourite', only v3 classes
    BTN_FAVORITES = (
        "[data-event-click*='favourit'], [data-event-click*='saved'], "
        "[class*='v3-c-favourit'], [class*='v3-c-saved'], "
        "[href*='favourites'], [href*='saved'], "
        "a[title*='avourit'], button[title*='avourit']"
    )
    # FIXED: compare also not found by href/aria-label
    BTN_COMPARE = (
        "[data-event-click*='compare'], "
        "[class*='v3-c-compare'], "
        "[href*='compare'], "
        "a[title*='ompare'], button[title*='ompare']"
    )
    # FIXED: Sign in / Log in / Register not found with standard selectors
    BTN_SIGN_IN = (
        "a:has-text('Log in'), button:has-text('Log in'), "
        "a:has-text('Sign in'), a:has-text('Login'), "
        "[data-event-click*='login'], [data-event-click*='sign_in'], "
        "[href*='login'], [href*='sign-in'], [href*='auth']"
    )
    BTN_REGISTRATION = (
        "a:has-text('Registration'), a:has-text('Register'), a:has-text('Sign up'), "
        "[data-event-click*='register'], [href*='register'], [href*='signup']"
    )

    # ─── Slider / banner ────────────────────────────────────────────────────────
    # FIXED: .swiper not found — using v3-c-* and data attributes
    MAIN_SLIDER = (
        "[class*='v3-c-slider'], [class*='v3-c-banner'], "
        "[class*='v3-c-carousel'], [class*='swiper'], "
        "[data-component*='slider'], [data-component*='banner']"
    )
    SLIDER_PREV = (
        "[class*='v3-c-slider'] [class*='prev'], "
        ".swiper-button-prev, [aria-label='Previous'], "
        "[class*='slider'] button:first-child"
    )
    SLIDER_NEXT = (
        "[class*='v3-c-slider'] [class*='next'], "
        ".swiper-button-next, [aria-label='Next'], "
        "[class*='slider'] button:last-child"
    )
    SLIDER_DOTS = (
        ".swiper-pagination-bullet, "
        "[class*='v3-c-slider'] [class*='dot'], "
        "[class*='v3-c-slider'] [class*='bullet'], "
        "[class*='pagination'] span"
    )

    # ─── Currency / language ────────────────────────────────────────────────────
    # FIXED: v3-c-* classes for currency/language
    CURRENCY_BLOCK = (
        "[class*='v3-c-currency'], [data-event-click*='currency'], "
        "[class*='currency'], select[name*='currency'], "
        "button[class*='currency']"
    )
    LANGUAGE_BLOCK = (
        "[class*='v3-c-language'], [class*='v3-c-lang'], "
        "[data-event-click*='language'], [data-event-click*='lang'], "
        "[class*='language'], select[name*='lang']"
    )

    # ─── GDPR ────────────────────────────────────────────────────────────────
    GDPR_POPUP = "[class*='gdpr'], [class*='cookie'], #cookie-consent, [data-testid*='gdpr']"
    GDPR_ACCEPT = "button:has-text('Accept'), button:has-text('Accept all'), #gdpr-consent-accept"
    GDPR_DECLINE = "button:has-text('Decline'), button:has-text('Reject')"

    # ─── Footer ──────────────────────────────────────────────────────────────
    FOOTER = "footer, [class*='footer'], [id*='footer']"
    FOOTER_LINKS = "footer a, [class*='footer'] a"

    def __init__(self, page: Page):
        self.page = page

    # ─── Navigation ──────────────────────────────────────────────────────────

    def navigate(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return self

    def reload(self):
        self.page.reload(wait_until="domcontentloaded")
        return self

    def go_back(self):
        self.page.go_back(wait_until="domcontentloaded")
        return self

    # ─── Element getters ─────────────────────────────────────────────────────

    def get(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def get_by_text(self, text: str) -> Locator:
        return self.page.get_by_text(text)

    def get_by_role(self, role: str, **kwargs) -> Locator:
        return self.page.get_by_role(role, **kwargs)

    # ─── Waits ───────────────────────────────────────────────────────────────

    def wait_for(self, selector: str, timeout: int = DEFAULT_TIMEOUT):
        self.page.wait_for_selector(selector, timeout=timeout)

    def is_visible(self, selector: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
        try:
            return self.page.locator(selector).first.is_visible(timeout=timeout)
        except Exception:
            return False

    def expect_visible(self, selector: str, timeout: int = DEFAULT_TIMEOUT):
        expect(self.page.locator(selector).first).to_be_visible(timeout=timeout)

    def expect_url_contains(self, pattern: str):
        expect(self.page).to_have_url(re.compile(pattern))

    # ─── Actions ─────────────────────────────────────────────────────────────

    def click(self, selector: str):
        self.page.locator(selector).first.click()
        return self

    def fill_input(self, selector: str, value: str):
        self.page.locator(selector).first.fill(value)
        return self

    def press_key(self, selector: str, key: str):
        self.page.locator(selector).first.press(key)
        return self

    def scroll_to_bottom(self):
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def scroll_to_element(self, selector: str):
        self.page.locator(selector).first.scroll_into_view_if_needed()

    # ─── Header: common checks ───────────────────────────────────────────────

    def get_logo(self) -> Locator:
        return self.page.locator(self.LOGO).first

    def get_search_input(self) -> Locator:
        return self.page.locator(self.SEARCH_INPUT).first

    def get_header(self) -> Locator:
        return self.page.locator(self.HEADER).first

    def get_footer(self) -> Locator:
        return self.page.locator(self.FOOTER).first

    def get_footer_links(self) -> Locator:
        return self.page.locator(self.FOOTER_LINKS)

    def get_gdpr_popup(self) -> Locator:
        return self.page.locator(self.GDPR_POPUP).first

    def accept_gdpr(self):
        try:
            btn = self.page.locator(self.GDPR_ACCEPT).first
            if btn.is_visible(timeout=3000):
                btn.click()
        except Exception:
            pass

    def decline_gdpr(self):
        try:
            btn = self.page.locator(self.GDPR_DECLINE).first
            if btn.is_visible(timeout=3000):
                btn.click()
        except Exception:
            pass

    # ─── Title / URL ──────────────────────────────────────────────────────────

    @property
    def title(self) -> str:
        return self.page.title()

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def console_errors(self) -> list:
        return getattr(self.page, "_console_errors", [])
