"""
ListingPage — truck for sale listing page.

Covers:
  - Product photo block (gallery, navigation)
  - All buttons (favorites, compare, share, print, contact)
  - All links (seller, category, breadcrumbs)
  - All information blocks (price, specs, description, location)
  - "Contact the seller" popup
  - "Contact the seller" form
"""

from playwright.sync_api import Locator, Page

from .base_page import BasePage


class ListingPage(BasePage):
    # ─── Breadcrumbs ─────────────────────────────────────────────────────────
    BREADCRUMBS = ".breadcrumb, [class*='breadcrumb'], nav[aria-label*='breadcrumb']"
    BREADCRUMB_LINKS = ".breadcrumb a, [class*='breadcrumb'] a"

    # ─── Title ───────────────────────────────────────────────────────────────
    AD_TITLE = "h1, .ad-title, [class*='ad-title'], [class*='listing-title']"
    AD_PRICE = "[class*='price']:not([class*='filter']), .price-block .price, [data-price]"
    AD_ID = "[class*='ad-id'], [class*='listing-id'], .ad-number"

    # ─── Photo gallery ───────────────────────────────────────────────────────
    PHOTO_GALLERY = ".gallery, [class*='gallery'], [class*='photo'], .swiper"
    MAIN_PHOTO = ".gallery__main img, [class*='main-photo'] img, .swiper-slide-active img"
    PHOTO_THUMBNAILS = ".gallery__thumbs img, [class*='thumbnail'] img, .swiper-thumbs img"
    GALLERY_PREV = ".gallery .swiper-button-prev, [class*='gallery'] [aria-label='Previous']"
    GALLERY_NEXT = ".gallery .swiper-button-next, [class*='gallery'] [aria-label='Next']"
    FULLSCREEN_BTN = (
        "[class*='fullscreen'], [aria-label*='fullscreen'], button:has-text('Fullscreen')"
    )

    # ─── Action buttons ──────────────────────────────────────────────────────
    BTN_ADD_FAVORITES = (
        "button[class*='favourit'], [aria-label*='favourit'], button:has-text('Add to favourites')"
    )
    BTN_COMPARE_ADD = (
        "button[class*='compare'], [aria-label*='compare'], button:has-text('Compare')"
    )
    BTN_SHARE = "button:has-text('Share'), [aria-label*='share'], [class*='share']"
    BTN_PRINT = "button:has-text('Print'), [aria-label*='print'], [class*='print']"
    BTN_REPORT = "button:has-text('Report'), a:has-text('Report this ad')"

    # ─── Contact seller ──────────────────────────────────────────────────────
    BTN_CONTACT_SELLER = (
        "button:has-text('Contact'), a:has-text('Contact the seller'), [data-action='contact']"
    )
    BTN_CALL_SELLER = "a[href^='tel:'], button:has-text('Call'), [class*='phone-btn']"
    SELLER_PHONE = "a[href^='tel:'], [class*='phone'], [data-phone]"
    SELLER_NAME = "[class*='seller-name'], [class*='dealer-name'], .seller h2, .seller h3"
    SELLER_LINK = "a[href*='dealer'], a[href*='seller'], [class*='seller'] a"

    # ─── Contact popup ───────────────────────────────────────────────────────
    CONTACT_POPUP = "[class*='modal'], [class*='popup'], dialog, [role='dialog']"
    CONTACT_POPUP_CLOSE = "[class*='modal'] [aria-label*='close'], [class*='modal'] button:has-text('×'), dialog button:has-text('Close')"

    # ─── Contact the seller form ─────────────────────────────────────────────
    FORM_CONTACT = "form[class*='contact'], form[id*='contact'], [data-form='contact']"
    FORM_FIELD_NAME = "input[name*='name'], input[placeholder*='name'], #contact-name"
    FORM_FIELD_EMAIL = "input[type='email'], input[name*='email'], #contact-email"
    FORM_FIELD_PHONE = "input[type='tel'], input[name*='phone'], #contact-phone"
    FORM_FIELD_MESSAGE = (
        "textarea[name*='message'], textarea[placeholder*='message'], #contact-message"
    )
    FORM_SUBMIT = "button[type='submit']:has-text('Send'), button:has-text('Send message')"
    FORM_SUCCESS = "[class*='success'], [class*='thank'], .form-success, [data-status='sent']"
    FORM_ERROR = "[class*='error'], .form-error, [role='alert']"

    # ─── Information blocks ──────────────────────────────────────────────────
    SPECS_BLOCK = "[class*='specs'], [class*='characteristics'], .features-list, dl"
    SPEC_ROWS = "[class*='specs'] tr, [class*='specs'] li, dl dt"
    DESCRIPTION_BLOCK = "[class*='description'], [data-section='description'], .ad-description"
    LOCATION_BLOCK = "[class*='location'], [data-section='location'], .location-info"
    MAP_BLOCK = ".map, [class*='map'], [id*='map']"

    # ─── Similar ads / recommendations ───────────────────────────────────────
    SIMILAR_ADS = "[class*='similar'], [class*='related'], section:has-text('Similar'), section:has-text('You may also')"
    SIMILAR_AD_LINKS = "[class*='similar'] a, [class*='related'] a"

    def __init__(self, page: Page):
        super().__init__(page)

    # ─── Getters ──────────────────────────────────────────────────────────────

    def get_title(self) -> str:
        return self.page.locator(self.AD_TITLE).first.inner_text()

    def get_price_text(self) -> str:
        return self.page.locator(self.AD_PRICE).first.inner_text()

    def get_main_photo(self) -> Locator:
        return self.page.locator(self.MAIN_PHOTO).first

    def get_thumbnails(self) -> Locator:
        return self.page.locator(self.PHOTO_THUMBNAILS)

    def get_specs_block(self) -> Locator:
        return self.page.locator(self.SPECS_BLOCK).first

    def get_spec_rows(self) -> Locator:
        return self.page.locator(self.SPEC_ROWS)

    def get_description(self) -> Locator:
        return self.page.locator(self.DESCRIPTION_BLOCK).first

    def get_location_block(self) -> Locator:
        return self.page.locator(self.LOCATION_BLOCK).first

    def get_contact_popup(self) -> Locator:
        return self.page.locator(self.CONTACT_POPUP).first

    def get_contact_form(self) -> Locator:
        return self.page.locator(self.FORM_CONTACT).first

    def get_breadcrumbs(self) -> Locator:
        return self.page.locator(self.BREADCRUMBS).first

    def get_similar_ads(self) -> Locator:
        return self.page.locator(self.SIMILAR_ADS).first

    def get_seller_link(self) -> Locator:
        return self.page.locator(self.SELLER_LINK).first

    # ─── Gallery actions ──────────────────────────────────────────────────────

    def click_gallery_next(self):
        self.page.locator(self.GALLERY_NEXT).first.click()
        return self

    def click_gallery_prev(self):
        self.page.locator(self.GALLERY_PREV).first.click()
        return self

    def click_thumbnail(self, index: int = 0):
        thumbs = self.page.locator(self.PHOTO_THUMBNAILS)
        thumbs.nth(index).click()
        return self

    def open_fullscreen(self):
        btn = self.page.locator(self.FULLSCREEN_BTN).first
        if btn.is_visible(timeout=3000):
            btn.click()
        return self

    # ─── Listing actions ──────────────────────────────────────────────────────

    def click_add_to_favorites(self):
        self.page.locator(self.BTN_ADD_FAVORITES).first.click()
        return self

    def click_add_to_compare(self):
        self.page.locator(self.BTN_COMPARE_ADD).first.click()
        return self

    def click_share(self):
        self.page.locator(self.BTN_SHARE).first.click()
        return self

    def click_print(self):
        self.page.locator(self.BTN_PRINT).first.click()
        return self

    # ─── Contact seller ───────────────────────────────────────────────────────

    def open_contact_popup(self):
        self.page.locator(self.BTN_CONTACT_SELLER).first.click()
        self.page.wait_for_selector(self.CONTACT_POPUP, timeout=5000)
        return self

    def close_contact_popup(self):
        self.page.locator(self.CONTACT_POPUP_CLOSE).first.click()
        return self

    def fill_contact_form(
        self, name: str, email: str, phone: str = "", message: str = "Test inquiry"
    ):
        self.page.locator(self.FORM_FIELD_NAME).first.fill(name)
        self.page.locator(self.FORM_FIELD_EMAIL).first.fill(email)
        if phone:
            self.page.locator(self.FORM_FIELD_PHONE).first.fill(phone)
        self.page.locator(self.FORM_FIELD_MESSAGE).first.fill(message)
        return self

    def submit_contact_form(self):
        self.page.locator(self.FORM_SUBMIT).first.click()
        return self

    def is_form_success_visible(self) -> bool:
        return self.is_visible(self.FORM_SUCCESS, timeout=5000)

    def is_form_error_visible(self) -> bool:
        return self.is_visible(self.FORM_ERROR, timeout=3000)

    # ─── Breadcrumb navigation ────────────────────────────────────────────────

    def click_breadcrumb(self, index: int = 0):
        self.page.locator(self.BREADCRUMB_LINKS).nth(index).click()
        self.page.wait_for_load_state("domcontentloaded")
        return self

    def click_seller_link(self):
        self.page.locator(self.SELLER_LINK).first.click()
        self.page.wait_for_load_state("domcontentloaded")
        return self
