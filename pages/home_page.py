"""
HomePage — home page of truck1.eu

Covers sections:
  - Header (logo, catalogue, search, place-ad, sell, favorites, compare, sign-in)
  - Slider/Banner
  - Currency / Language blocks
  - Product categories
  - Advertising block
  - Leasing section
  - Sell block
  - Featured offers slider
  - Blog block
  - Recently viewed slider
  - Popular categories
  - GDPR popup
  - Footer
"""

from playwright.sync_api import Page, Locator, expect
from .base_page import BasePage


class HomePage(BasePage):

    # ─── Product categories ───────────────────────────────────────────────────
    CATEGORIES_BLOCK = "[class*='categor'], [data-section*='categor'], .categories"
    CATEGORY_ITEMS = "[class*='categor'] a, [class*='categor'] li"

    # ─── Advertising ────────────────────────────────────────────────────────────
    ADVERTISING_BLOCK = "[class*='advertis'], [class*='banner-block'], .ad-block"

    # ─── Leasing section ──────────────────────────────────────────────────────
    LEASING_SECTION = "[class*='leasing'], section:has-text('Leasing'), [data-section='leasing']"
    LEASING_LINK = "a[href*='lease'], a:has-text('Leasing')"

    # ─── Sell block ───────────────────────────────────────────────────────────
    SELL_BLOCK = "[class*='sell-block'], section:has-text('Sell your truck'), .sell-section"
    SELL_CTA = ".sell-block a, [class*='sell'] a, a:has-text('Sell')"

    # ─── Featured offers slider ───────────────────────────────────────────────
    FEATURED_SLIDER = "[class*='featured'], [data-section='featured'], section:has-text('Featured')"
    FEATURED_ITEMS = "[class*='featured'] .card, [class*='featured'] article, [class*='featured'] [class*='item']"
    FEATURED_PREV = "[class*='featured'] .swiper-button-prev, [class*='featured'] [aria-label='Previous']"
    FEATURED_NEXT = "[class*='featured'] .swiper-button-next, [class*='featured'] [aria-label='Next']"

    # ─── Blog ────────────────────────────────────────────────────────────────
    BLOG_BLOCK = "[class*='blog'], section:has-text('Blog'), [data-section='blog']"
    BLOG_ITEMS = "[class*='blog'] article, [class*='blog'] .card, [class*='blog'] [class*='post']"
    BLOG_LINK = "[class*='blog'] a[href*='blog'], a:has-text('Blog')"

    # ─── Recently viewed slider ───────────────────────────────────────────────
    RECENTLY_VIEWED = "[class*='recently'], [class*='viewed'], section:has-text('Recently viewed')"
    RECENTLY_ITEMS = "[class*='recently'] .card, [class*='recently'] article"

    # ─── Popular categories ───────────────────────────────────────────────────
    POPULAR_CATEGORIES = "[class*='popular'], section:has-text('Popular'), [data-section='popular']"
    POPULAR_CATEGORY_LINKS = "[class*='popular'] a"

    # ─── Catalog preview (on homepage) ────────────────────────────────────────
    BTN_SEE_ALL_SALE = "a:has-text('See all trucks for sale'), a[href*='trucks-for-sale']"
    BTN_SEE_ALL_LEASE = "a:has-text('See all trucks for lease'), a[href*='trucks-for-lease']"

    def __init__(self, page: Page):
        super().__init__(page)

    # ─── Header actions ───────────────────────────────────────────────────────

    def click_catalogue(self):
        self.page.locator(self.NAV_CATALOGUE).first.click()
        return self

    def type_in_search(self, query: str):
        inp = self.page.locator(self.SEARCH_INPUT).first
        inp.fill(query)
        inp.press("Enter")
        return self

    def click_place_ad(self):
        self.page.locator(self.BTN_PLACE_AD).first.click()
        return self

    def click_sell(self):
        self.page.locator(self.BTN_SELL).first.click()
        return self

    def click_favorites(self):
        self.page.locator(self.BTN_FAVORITES).first.click()
        return self

    def click_compare(self):
        self.page.locator(self.BTN_COMPARE).first.click()
        return self

    def click_sign_in(self):
        self.page.locator(self.BTN_SIGN_IN).first.click()
        return self

    # ─── Slider ───────────────────────────────────────────────────────────────

    def click_slider_next(self):
        self.page.locator(self.SLIDER_NEXT).first.click()
        return self

    def click_slider_prev(self):
        self.page.locator(self.SLIDER_PREV).first.click()
        return self

    def get_slider_dots(self) -> Locator:
        return self.page.locator(self.SLIDER_DOTS)

    # ─── Currency / Language ──────────────────────────────────────────────────

    def get_currency_block(self) -> Locator:
        return self.page.locator(self.CURRENCY_BLOCK).first

    def get_language_block(self) -> Locator:
        return self.page.locator(self.LANGUAGE_BLOCK).first

    # ─── Sections getters ────────────────────────────────────────────────────

    def get_categories_block(self) -> Locator:
        return self.page.locator(self.CATEGORIES_BLOCK).first

    def get_category_items(self) -> Locator:
        return self.page.locator(self.CATEGORY_ITEMS)

    def get_advertising_block(self) -> Locator:
        return self.page.locator(self.ADVERTISING_BLOCK).first

    def get_leasing_section(self) -> Locator:
        return self.page.locator(self.LEASING_SECTION).first

    def get_sell_block(self) -> Locator:
        return self.page.locator(self.SELL_BLOCK).first

    def get_featured_slider(self) -> Locator:
        return self.page.locator(self.FEATURED_SLIDER).first

    def get_featured_items(self) -> Locator:
        return self.page.locator(self.FEATURED_ITEMS)

    def get_blog_block(self) -> Locator:
        return self.page.locator(self.BLOG_BLOCK).first

    def get_blog_items(self) -> Locator:
        return self.page.locator(self.BLOG_ITEMS)

    def get_recently_viewed(self) -> Locator:
        return self.page.locator(self.RECENTLY_VIEWED).first

    def get_popular_categories(self) -> Locator:
        return self.page.locator(self.POPULAR_CATEGORIES).first

    def get_popular_category_links(self) -> Locator:
        return self.page.locator(self.POPULAR_CATEGORY_LINKS)

    # ─── Navigation ───────────────────────────────────────────────────────────

    def click_see_all_sale(self):
        self.page.locator(self.BTN_SEE_ALL_SALE).first.click()
        return self

    def click_see_all_lease(self):
        self.page.locator(self.BTN_SEE_ALL_LEASE).first.click()
        return self

    def click_leasing_link(self):
        self.page.locator(self.LEASING_LINK).first.click()
        return self

    def click_blog_link(self):
        self.page.locator(self.BLOG_LINK).first.click()
        return self
