"""
CatalogPage — catalog listings page (trucks-for-sale / trucks-for-lease).

Covers:
  - Buttons [See all trucks for sale/lease]
  - TYPE block
  - Curtainsider trucks category
  - Ad counter
  - Listings catalog section
  - Filters (make, year, price, mileage, country, etc.)
"""

from playwright.sync_api import Page, Locator, expect
from .base_page import BasePage


class CatalogPage(BasePage):

    # ─── Title / counter ──────────────────────────────────────────────────────
    PAGE_TITLE = "h1, .page-title, [class*='page-title']"
    AD_COUNTER = "[class*='count'], [class*='total'], .results-count, h1 span"

    # ─── Toggle buttons ───────────────────────────────────────────────────────
    BTN_SEE_ALL_SALE = "a:has-text('See all trucks for sale'), [href*='trucks-for-sale']:has-text('See all')"
    BTN_SEE_ALL_LEASE = "a:has-text('See all trucks for lease'), [href*='trucks-for-lease']:has-text('See all')"

    # ─── TYPE block ───────────────────────────────────────────────────────────
    TYPE_BLOCK = "[class*='type-filter'], [data-filter='type'], fieldset:has-text('Type')"
    TYPE_OPTIONS = "[class*='type-filter'] label, [data-filter='type'] label, fieldset:has-text('Type') label"

    # ─── Categories ───────────────────────────────────────────────────────────
    CURTAINSIDER_LINK = "a:has-text('Curtainsider'), [href*='curtainsider']"
    CATEGORY_LINKS = "[class*='categor'] a, .category-list a"

    # ─── Listing cards ────────────────────────────────────────────────────────
    AD_CARDS = ".listing-card, [class*='listing-item'], article[class*='ad'], [class*='truck-card']"
    FIRST_AD_CARD = ".listing-card:first-child, [class*='listing-item']:first-child"
    AD_CARD_TITLE = "[class*='listing-item'] h2, [class*='listing-item'] h3, .card-title"
    AD_CARD_PRICE = "[class*='price'], .price"
    AD_CARD_IMAGE = "[class*='listing-item'] img, .card img"
    AD_CARD_LINK = "[class*='listing-item'] a, .listing-card a"

    # ─── Filters ──────────────────────────────────────────────────────────────
    FILTER_SIDEBAR = "[class*='filter'], aside, .filters, [data-component='filters']"
    FILTER_MAKE = "select[name*='make'], [data-filter='make'], [class*='make-filter']"
    FILTER_YEAR_FROM = "input[name*='year_from'], [data-filter='year-from']"
    FILTER_YEAR_TO = "input[name*='year_to'], [data-filter='year-to']"
    FILTER_PRICE_FROM = "input[name*='price_from'], [data-filter='price-from']"
    FILTER_PRICE_TO = "input[name*='price_to'], [data-filter='price-to']"
    FILTER_MILEAGE = "input[name*='mileage'], [data-filter='mileage']"
    FILTER_COUNTRY = "select[name*='country'], [data-filter='country']"
    BTN_APPLY_FILTERS = "button:has-text('Search'), button:has-text('Apply'), button[type='submit']"
    BTN_RESET_FILTERS = "button:has-text('Reset'), a:has-text('Clear'), button:has-text('Clear all')"

    # ─── Sorting ───────────────────────────────────────────────────────────────
    SORT_SELECT = "select[name*='sort'], [data-sort], [class*='sort-select']"

    # ─── Pagination ────────────────────────────────────────────────────────────
    PAGINATION = ".pagination, [class*='pagination'], nav[aria-label*='pagination']"
    PAGINATION_NEXT = ".pagination-next, [aria-label='Next page'], a:has-text('Next')"
    PAGINATION_PREV = ".pagination-prev, [aria-label='Previous page'], a:has-text('Prev')"

    def __init__(self, page: Page):
        super().__init__(page)

    # ─── Getters ──────────────────────────────────────────────────────────────

    def get_ad_cards(self) -> Locator:
        return self.page.locator(self.AD_CARDS)

    def get_ad_counter_text(self) -> str:
        try:
            return self.page.locator(self.AD_COUNTER).first.inner_text()
        except Exception:
            return ""

    def get_filter_sidebar(self) -> Locator:
        return self.page.locator(self.FILTER_SIDEBAR).first

    def get_type_block(self) -> Locator:
        return self.page.locator(self.TYPE_BLOCK).first

    def get_type_options(self) -> Locator:
        return self.page.locator(self.TYPE_OPTIONS)

    def get_pagination(self) -> Locator:
        return self.page.locator(self.PAGINATION).first

    # ─── Actions ───────────────────────────────────────────────────────────────

    def click_first_ad(self):
        self.page.locator(self.AD_CARD_LINK).first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def click_curtainsider(self):
        self.page.locator(self.CURTAINSIDER_LINK).first.click()
        return self

    def apply_make_filter(self, make: str):
        sel = self.page.locator(self.FILTER_MAKE).first
        sel.select_option(label=make)
        return self

    def apply_year_filter(self, year_from: str = None, year_to: str = None):
        if year_from:
            self.page.locator(self.FILTER_YEAR_FROM).first.fill(year_from)
        if year_to:
            self.page.locator(self.FILTER_YEAR_TO).first.fill(year_to)
        return self

    def apply_price_filter(self, price_from: str = None, price_to: str = None):
        if price_from:
            self.page.locator(self.FILTER_PRICE_FROM).first.fill(price_from)
        if price_to:
            self.page.locator(self.FILTER_PRICE_TO).first.fill(price_to)
        return self

    def submit_filters(self):
        self.page.locator(self.BTN_APPLY_FILTERS).first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def reset_filters(self):
        btn = self.page.locator(self.BTN_RESET_FILTERS).first
        if btn.is_visible(timeout=3000):
            btn.click()
            self.page.wait_for_load_state("domcontentloaded")
        return self

    def go_to_next_page(self):
        self.page.locator(self.PAGINATION_NEXT).first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def select_sort(self, value: str):
        self.page.locator(self.SORT_SELECT).first.select_option(value=value)
        return self
