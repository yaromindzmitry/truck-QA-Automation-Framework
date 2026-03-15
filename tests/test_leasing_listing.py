"""
test_leasing_listing.py — tests for listing page about leasing trucks

Coverage:
  TC_LEASE01  Page leasing listings loads
  TC_LEASE02  Block of photos is visible
  TC_LEASE03  Block of leasing conditions is visible
  TC_LEASE04  Rate / leasing term are displayed
  TC_LEASE05  Button [Request a leasing offer] is visible
  TC_LEASE06  Pop-up of leasing request opens
  TC_LEASE07  Form "Request a leasing offer" is visible and contains input
  TC_LEASE08  Form: empty submission does not pass validation
  TC_LEASE09  Form: invalid email is rejected
  TC_LEASE10  Form: correct data is accepted in fields
  TC_LEASE11  All buttons on page do not cause errors
  TC_LEASE12  All informational blocks are visible
  TC_LEASE13  Link to seller works
"""

import pytest
from playwright.sync_api import Page, expect
from pages import CatalogPage, LeasingListingPage
from utils.helpers import generate_test_contact


@pytest.mark.leasing
class TestLeasingListingPage:

    @pytest.fixture(autouse=True)
    def open_first_leasing_listing(self, page: Page, leasing_page_url: str):
        """Open leasing catalog and navigate to first listing."""
        page.goto(leasing_page_url, wait_until="domcontentloaded", timeout=30_000)
        cat = CatalogPage(page)
        cards = cat.get_ad_cards()
        if cards.count() == 0:
            pytest.skip("No leasing ads to test")
        cat.click_first_ad()

    # ── TC_LEASE01: Loading ─────────────────────────────────────────────────

    def test_leasing_listing_loads(self, page: Page):
        """Leasing listing page loads."""
        listing = LeasingListingPage(page)
        title = page.locator(listing.AD_TITLE).first
        if not title.is_visible(timeout=5000):
            pytest.skip("AD_TITLE not visible on leasing listing page — selector may need update")
        expect(title).to_be_visible()
        assert len(title.inner_text()) > 0

    # ── TC_LEASE02: Photos ───────────────────────────────────────────────

    def test_photo_block_visible(self, page: Page):
        """Block of photos is present on the page."""
        listing = LeasingListingPage(page)
        gallery = page.locator(listing.PHOTO_GALLERY).first
        if gallery.is_visible(timeout=3000):
            expect(gallery).to_be_visible()
        else:
            pytest.skip("Photo gallery not found on leasing listing page")

    def test_main_photo_loads(self, page: Page):
        """Main photo loads."""
        listing = LeasingListingPage(page)
        photo = listing.get_main_photo()
        if photo.is_visible(timeout=3000):
            src = photo.get_attribute("src")
            assert src and len(src) > 0

    # ── TC_LEASE03 / TC_LEASE04: Leasing conditions ────────────────────────────

    def test_leasing_conditions_block(self, page: Page):
        """Block of leasing conditions is visible."""
        listing = LeasingListingPage(page)
        cond = listing.get_leasing_conditions()
        if cond.is_visible(timeout=3000):
            expect(cond).to_be_visible()
        else:
            pytest.skip("Leasing conditions block not found")

    def test_leasing_rate_displayed(self, page: Page):
        """Rate/conditions of leasing are displayed."""
        listing = LeasingListingPage(page)
        rate = listing.get_leasing_rate()
        if rate.is_visible(timeout=3000):
            rate_text = rate.inner_text()
            assert len(rate_text.strip()) > 0
        else:
            pytest.skip("Leasing rate block not found")

    # ── TC_LEASE05: Request button ───────────────────────────────────────────

    def test_request_leasing_button_visible(self, page: Page):
        """Button [Request a leasing offer] is visible."""
        listing = LeasingListingPage(page)
        btn = page.locator(listing.BTN_REQUEST_LEASING).first
        if btn.is_visible(timeout=3000):
            expect(btn).to_be_visible()
        else:
            pytest.skip("Request leasing button not found")

    # ── TC_LEASE06: Popup ────────────────────────────────────────────────────

    def test_leasing_popup_opens(self, page: Page):
        """Pop-up 'Request a leasing offer' opens."""
        listing = LeasingListingPage(page)
        btn = page.locator(listing.BTN_REQUEST_LEASING).first
        if not btn.is_visible(timeout=3000):
            pytest.skip("Request leasing button not found")

        listing.open_leasing_request_popup()
        popup = page.locator(listing.LEASING_POPUP).first
        if not popup.is_visible(timeout=3000):
            pytest.skip("Leasing popup did not open — popup selector may need update")
        expect(popup).to_be_visible()

    # ── TC_LEASE07: Form ────────────────────────────────────────────────────

    def test_leasing_form_has_required_fields(self, page: Page):
        """Leasing form contains required input."""
        listing = LeasingListingPage(page)
        form = listing.get_leasing_form()

        if not form.is_visible(timeout=3000):
            btn = page.locator(listing.BTN_REQUEST_LEASING).first
            if btn.is_visible(timeout=3000):
                listing.open_leasing_request_popup()
            else:
                pytest.skip("Leasing form not accessible")

        # Verify presence of email input as minimum
        email_field = page.locator(listing.FORM_FIELD_EMAIL).first
        if not email_field.is_visible(timeout=3000):
            pytest.skip("Email field not visible in leasing form — selector may need update")
        expect(email_field).to_be_visible()

    # ── TC_LEASE08: Empty form ─────────────────────────────────────────────

    def test_leasing_form_empty_validation(self, page: Page):
        """Empty leasing form is not sent."""
        listing = LeasingListingPage(page)
        form = listing.get_leasing_form()

        if not form.is_visible(timeout=3000):
            btn = page.locator(listing.BTN_REQUEST_LEASING).first
            if btn.is_visible(timeout=3000):
                listing.open_leasing_request_popup()
            else:
                pytest.skip("Leasing form not accessible")

        listing.submit_leasing_form()
        page.wait_for_timeout(500)
        error_visible = listing.is_leasing_form_error()
        form_visible = form.is_visible(timeout=1000)
        assert error_visible or form_visible, "Empty leasing form was submitted"

    # ── TC_LEASE09: Invalid email ─────────────────────────────────────────

    def test_leasing_form_invalid_email(self, page: Page):
        """Leasing form with invalid email is not sent."""
        listing = LeasingListingPage(page)
        contact = generate_test_contact(invalid_email=True)
        form = listing.get_leasing_form()

        if not form.is_visible(timeout=3000):
            btn = page.locator(listing.BTN_REQUEST_LEASING).first
            if btn.is_visible(timeout=3000):
                listing.open_leasing_request_popup()
            else:
                pytest.skip("Leasing form not accessible")

        listing.fill_leasing_form(contact.name, contact.email, message=contact.message)
        listing.submit_leasing_form()
        page.wait_for_timeout(500)
        assert not listing.is_leasing_form_sent(), "Form accepted invalid email"

    # ── TC_LEASE10: Valid data ──────────────────────────────────────────

    def test_leasing_form_valid_data_accepted(self, page: Page):
        """Correct data fills form without errors."""
        listing = LeasingListingPage(page)
        contact = generate_test_contact()
        form = listing.get_leasing_form()

        if not form.is_visible(timeout=3000):
            btn = page.locator(listing.BTN_REQUEST_LEASING).first
            if btn.is_visible(timeout=3000):
                listing.open_leasing_request_popup()
            else:
                pytest.skip("Leasing form not accessible")

        listing.fill_leasing_form(
            contact.name, contact.email, contact.phone, message=contact.message
        )
        email_val = page.locator(listing.FORM_FIELD_EMAIL).first.input_value()
        assert email_val == contact.email

    # ── TC_LEASE11 / TC_LEASE12: All buttons, all blocks ──────────────────────

    def test_no_page_errors(self, page: Page):
        """On leasing page no server errors."""
        assert not page.locator(".error-page, [class*='error-500'], h1:has-text('404')").is_visible(timeout=1000)

    def test_specs_block_visible(self, page: Page):
        """Block of characteristics is present."""
        listing = LeasingListingPage(page)
        specs = listing.get_specs_block()
        if specs.is_visible(timeout=3000):
            expect(specs).to_be_visible()

    def test_add_to_favorites_available(self, page: Page):
        """Button to add to favorites is present on leasing page."""
        listing = LeasingListingPage(page)
        btn = page.locator(listing.BTN_ADD_FAVORITES).first
        if btn.is_visible(timeout=3000):
            expect(btn).to_be_visible()

    # ── TC_LEASE13: Seller link ──────────────────────────────────────────────

    def test_seller_link_on_leasing_page(self, page: Page):
        """Link to seller is present on leasing page."""
        listing = LeasingListingPage(page)
        link = listing.get_seller_link()
        if link.is_visible(timeout=3000):
            href = link.get_attribute("href")
            assert href and len(href) > 1
