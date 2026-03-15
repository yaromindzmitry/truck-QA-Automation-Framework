"""
LeasingListingPage — truck leasing listing page.

Inherits from ListingPage, overrides:
  - "Request a leasing offer" form (instead of Contact the seller)
  - Leasing-specific blocks (conditions, rates)
"""

from playwright.sync_api import Locator, Page

from .listing_page import ListingPage


class LeasingListingPage(ListingPage):
    # ─── Leasing blocks ───────────────────────────────────────────────────────
    LEASING_CONDITIONS = "[class*='leasing'], [data-section='leasing-conditions'], .lease-terms"
    LEASING_RATE = "[class*='rate'], [class*='monthly'], .lease-rate, [data-leasing-rate]"
    LEASING_DURATION = "[class*='duration'], [class*='term'], .lease-duration"
    LEASING_DEPOSIT = "[class*='deposit'], [class*='down-payment'], .deposit-info"

    # ─── Leasing request button ───────────────────────────────────────────────
    BTN_REQUEST_LEASING = (
        "button:has-text('Request a leasing offer'), "
        "button:has-text('Request leasing'), "
        "a:has-text('Request a leasing offer'), "
        "[data-action='request-leasing']"
    )

    # ─── "Request a leasing offer" popup ──────────────────────────────────────
    LEASING_POPUP = "[class*='modal'], [class*='popup'], dialog, [role='dialog']"
    LEASING_POPUP_TITLE = "[class*='modal'] h2, [class*='modal'] h3, dialog h2"

    # ─── "Request a leasing offer" form ───────────────────────────────────────
    FORM_LEASING = (
        "form[class*='leasing'], form[id*='leasing'], [data-form='leasing'], form[class*='contact']"
    )
    FORM_COMPANY_NAME = "input[name*='company'], input[placeholder*='company'], #leasing-company"
    FORM_CONTACT_PERSON = "input[name*='contact'], input[placeholder*='contact person']"
    FORM_FIELD_NAME = "input[name*='name'], input[placeholder*='name'], #leasing-name"
    FORM_FIELD_EMAIL = "input[type='email'], input[name*='email'], #leasing-email"
    FORM_FIELD_PHONE = "input[type='tel'], input[name*='phone'], #leasing-phone"
    FORM_DOWN_PAYMENT = "input[name*='down_payment'], input[name*='deposit'], select[name*='down']"
    FORM_TERM = "select[name*='term'], select[name*='duration'], input[name*='term']"
    FORM_MESSAGE = "textarea[name*='message'], textarea[placeholder*='message']"
    FORM_SUBMIT = "button[type='submit']:has-text('Send'), button:has-text('Request'), button:has-text('Submit')"
    FORM_SUCCESS = "[class*='success'], [class*='thank'], .form-success"
    FORM_ERROR = "[class*='error'], .form-error, [role='alert']"

    # ─── Documents / conditions (if PDF exists) ───────────────────────────────
    DOCS_LINKS = "a[href*='.pdf'], a[href*='document'], [class*='document'] a"

    def __init__(self, page: Page):
        super().__init__(page)

    # ─── Leasing getters ──────────────────────────────────────────────────────

    def get_leasing_conditions(self) -> Locator:
        return self.page.locator(self.LEASING_CONDITIONS).first

    def get_leasing_rate(self) -> Locator:
        return self.page.locator(self.LEASING_RATE).first

    def get_leasing_duration(self) -> Locator:
        return self.page.locator(self.LEASING_DURATION).first

    def get_leasing_form(self) -> Locator:
        return self.page.locator(self.FORM_LEASING).first

    # ─── Leasing form actions ──────────────────────────────────────────────────

    def open_leasing_request_popup(self):
        self.page.locator(self.BTN_REQUEST_LEASING).first.click()
        self.page.wait_for_selector(self.LEASING_POPUP, timeout=5000)
        return self

    def fill_leasing_form(
        self,
        name: str,
        email: str,
        phone: str = "",
        company: str = "",
        message: str = "Test leasing inquiry",
    ):
        if company:
            company_field = self.page.locator(self.FORM_COMPANY_NAME).first
            if company_field.is_visible(timeout=2000):
                company_field.fill(company)

        self.page.locator(self.FORM_FIELD_NAME).first.fill(name)
        self.page.locator(self.FORM_FIELD_EMAIL).first.fill(email)

        if phone:
            phone_field = self.page.locator(self.FORM_FIELD_PHONE).first
            if phone_field.is_visible(timeout=2000):
                phone_field.fill(phone)

        msg_field = self.page.locator(self.FORM_MESSAGE).first
        if msg_field.is_visible(timeout=2000):
            msg_field.fill(message)

        return self

    def submit_leasing_form(self):
        self.page.locator(self.FORM_SUBMIT).first.click()
        return self

    def is_leasing_form_sent(self) -> bool:
        return self.is_visible(self.FORM_SUCCESS, timeout=5000)

    def is_leasing_form_error(self) -> bool:
        return self.is_visible(self.FORM_ERROR, timeout=3000)
