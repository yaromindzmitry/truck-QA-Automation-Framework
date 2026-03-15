"""
SellerPage — seller/dealer page on truck1.eu.

Covers:
  - All buttons (contact, favorites, share)
  - All links (listings, social networks, seller website)
  - All information blocks (company description, rating, contacts, address)
  - All tooltips
  - List of seller's listings
  - Filters for seller's listings
"""

from playwright.sync_api import Page, Locator
from .base_page import BasePage


class SellerPage(BasePage):

    # ─── Seller profile header ────────────────────────────────────────────────
    SELLER_LOGO = "[class*='dealer-logo'] img, [class*='seller-logo'] img, .company-logo img"
    SELLER_NAME = "h1, [class*='dealer-name'], [class*='seller-name'], .company-name"
    SELLER_VERIFIED_BADGE = "[class*='verified'], [class*='badge'], [title*='verified']"
    SELLER_RATING = "[class*='rating'], [class*='stars'], [data-rating]"
    SELLER_SINCE = "[class*='since'], [class*='member-since'], .member-year"

    # ─── Contact information ──────────────────────────────────────────────────
    SELLER_PHONE = "a[href^='tel:'], [class*='phone'], [data-phone]"
    SELLER_EMAIL = "a[href^='mailto:'], [class*='email'], [data-email]"
    SELLER_WEBSITE = "a[href^='http']:not([href*='truck1']):not([href^='tel']):not([href^='mailto'])"
    SELLER_ADDRESS = "[class*='address'], [class*='location'], [itemprop='address']"
    SELLER_MAP = ".map, [class*='map'], [id*='map']"

    # ─── Action buttons ──────────────────────────────────────────────────────
    BTN_CONTACT = "button:has-text('Contact'), a:has-text('Contact dealer'), [data-action='contact-dealer']"
    BTN_FOLLOW = "button:has-text('Follow'), button[class*='follow'], [data-action='follow']"
    BTN_SHARE_SELLER = "button:has-text('Share'), [aria-label*='share'], [class*='share']"

    # ─── Social networks ─────────────────────────────────────────────────────
    SOCIAL_LINKS = "a[href*='facebook'], a[href*='linkedin'], a[href*='instagram'], a[href*='twitter'], a[href*='youtube']"

    # ─── Information blocks ──────────────────────────────────────────────────
    ABOUT_BLOCK = "[class*='about'], [class*='description'], .dealer-about, [data-section='about']"
    STATS_BLOCK = "[class*='stats'], [class*='statistics'], .dealer-stats"
    TOTAL_ADS_COUNT = "[class*='stats'] [class*='count'], [class*='ads-count'], .total-ads"

    # ─── Tooltips ────────────────────────────────────────────────────────────
    TOOLTIPS = "[title], [data-tooltip], [data-tippy-content], [aria-label]"
    TOOLTIP_TRIGGERS = "[class*='tooltip-trigger'], [data-toggle='tooltip'], [class*='info-icon']"

    # ─── Listings ────────────────────────────────────────────────────────────
    ADS_LIST = "[class*='ads-list'], [class*='listings'], .dealer-listings"
    AD_CARDS = "[class*='listing-card'], [class*='ad-card'], article[class*='listing']"
    AD_CARD_TITLE = "[class*='ad-card'] h2, [class*='ad-card'] h3, .card-title"
    AD_CARD_PRICE = "[class*='ad-card'] [class*='price'], .card [class*='price']"

    # ─── Seller listings filters ──────────────────────────────────────────────
    ADS_FILTER_TYPE = "select[name*='type'], [data-filter='ad-type'], button:has-text('For sale'), button:has-text('For lease')"
    ADS_SORT = "select[name*='sort'], [data-sort='seller-ads']"
    ADS_SEARCH = "input[class*='search']:not([id*='header']), [placeholder*='Search in dealer']"

    # ─── Pagination ───────────────────────────────────────────────────────────
    PAGINATION = ".pagination, [class*='pagination']"
    PAGINATION_NEXT = ".pagination-next, a:has-text('Next'), [aria-label='Next page']"

    # ─── Reviews ──────────────────────────────────────────────────────────────
    REVIEWS_BLOCK = "[class*='review'], [class*='feedback'], [data-section='reviews']"
    REVIEW_ITEMS = "[class*='review-item'], [class*='feedback-item']"

    def __init__(self, page: Page):
        super().__init__(page)

    # ─── Getters ─────────────────────────────────────────────────────────────

    def get_seller_name(self) -> str:
        return self.page.locator(self.SELLER_NAME).first.inner_text()

    def get_seller_phone(self) -> Locator:
        return self.page.locator(self.SELLER_PHONE).first

    def get_seller_email(self) -> Locator:
        return self.page.locator(self.SELLER_EMAIL).first

    def get_seller_address(self) -> Locator:
        return self.page.locator(self.SELLER_ADDRESS).first

    def get_about_block(self) -> Locator:
        return self.page.locator(self.ABOUT_BLOCK).first

    def get_stats_block(self) -> Locator:
        return self.page.locator(self.STATS_BLOCK).first

    def get_ad_cards(self) -> Locator:
        return self.page.locator(self.AD_CARDS)

    def get_total_ads_count(self) -> str:
        try:
            return self.page.locator(self.TOTAL_ADS_COUNT).first.inner_text()
        except Exception:
            return ""

    def get_social_links(self) -> Locator:
        return self.page.locator(self.SOCIAL_LINKS)

    def get_tooltip_triggers(self) -> Locator:
        return self.page.locator(self.TOOLTIP_TRIGGERS)

    def get_reviews_block(self) -> Locator:
        return self.page.locator(self.REVIEWS_BLOCK).first

    def get_verified_badge(self) -> Locator:
        return self.page.locator(self.SELLER_VERIFIED_BADGE).first

    # ─── Actions ────────────────────────────────────────────────────────────

    def click_contact(self):
        self.page.locator(self.BTN_CONTACT).first.click()
        return self

    def click_follow(self):
        self.page.locator(self.BTN_FOLLOW).first.click()
        return self

    def hover_tooltip(self, index: int = 0):
        triggers = self.page.locator(self.TOOLTIP_TRIGGERS)
        if triggers.count() > index:
            triggers.nth(index).hover()
        return self

    def click_first_ad(self):
        self.page.locator(self.AD_CARDS).first.locator("a").first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def filter_ads_by_type(self, ad_type: str):
        btn = self.page.locator(f"button:has-text('{ad_type}')").first
        if btn.is_visible(timeout=3000):
            btn.click()
            self.page.wait_for_load_state("domcontentloaded")
        return self

    def go_to_next_page(self):
        self.page.locator(self.PAGINATION_NEXT).first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def click_seller_website(self):
        link = self.page.locator(self.SELLER_WEBSITE).first
        if link.is_visible(timeout=3000):
            link.click()
        return self
