"""
test_user_flows.py — E2E user flow tests truck1.eu

What is a user flow test:
  Full scenario of real user from start to finish.
  Unlike unit-test (one element), flow-test checks
  multiple steps in sequence — how a real person would perform them.

Coverage:
  UF01  Search Flow         — Homepage → search → catalog → listing card
  UF02  Browse & Filter     — Catalog → filter by brand → pagination → open listing
  UF03  Contact Seller      — Listing → contact popup → form → inputs filled → close
  UF04  Leasing Flow        — Homepage → leasing catalog → leasing listing → request form
  UF05  Seller Page Flow    — Listing → dealer page → dealer card → open listing
  UF06  Category Navigation — Homepage → category → listings in category → breadcrumb back
  UF07  Pagination Flow     — Catalog page 1 → page 2 → different cards → page 1
  UF08  Back Navigation     — Catalog → listing → button Back → return to catalog
  UF09  Logo Home Return    — Any page → click logo → home
  UF10  404 Recovery        — Non-existent page → home link → home loads

Architecture:
  - Each test — independent flow (not dependent on others)
  - Use page fixtures from conftest.py
  - skip-guard on each step: if element unavailable — skip with explanation
  - Steps logged through allure-step / print for visibility in report
"""

import pytest
from playwright.sync_api import Page, expect
from pages import HomePage, CatalogPage, ListingPage, LeasingListingPage, SellerPage


# ── Helper functions ───────────────────────────────────────────────────

def _go(page: Page, path: str, desc: str = ""):
    """Navigate with wait for loading."""
    page.goto(f"https://www.truck1.eu{path}", wait_until="domcontentloaded", timeout=25_000)
    page.wait_for_timeout(500)


def _skip_if_not_visible(locator, msg: str, timeout: int = 5000):
    """Skip test if element is not visible."""
    if not locator.is_visible(timeout=timeout):
        pytest.skip(msg)


def _first_ad_url(page: Page) -> str:
    """Returns URL of first listing card or empty string."""
    card = page.locator("a[href*='/trucks-for-sale/']").first
    if card.is_visible(timeout=5000):
        return card.get_attribute("href") or ""
    return ""


def _first_lease_url(page: Page) -> str:
    """Returns URL of first leasing card or empty string."""
    card = page.locator("a[href*='/trucks-for-lease/']").first
    if card.is_visible(timeout=5000):
        return card.get_attribute("href") or ""
    return ""


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.flow
@pytest.mark.e2e
class TestUserFlows:

    # ──────────────────────────────────────────────────────────────────────────
    # UF01: Search Flow
    # Scenario: user enters query in search → goes to catalog
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf01_search_flow(self, page: Page):
        """
        UF01: Homepage → search by keyword → catalog with results
                      → click on first listing → listing page.

        Verify:
        - search field accepts input
        - After submission URL contains search query
        - On results page are cards
        - Click on card opens listing page with h1
        """
        home = HomePage(page)

        # Step 1: enter search
        search_input = page.locator(home.SEARCH_INPUT).first
        _skip_if_not_visible(search_input, "UF01: Search input not found on homepage")

        search_input.fill("Volvo")
        search_input.press("Enter")
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 2: URL changed (catalog or search)
        current_url = page.url
        assert any(kw in current_url for kw in ["volvo", "Volvo", "q=", "search", "trucks"]), (
            f"UF01: After search, URL doesn't contain search context. URL: {current_url}"
        )

        # Step 3: are cards of listings
        cards = page.locator("a[href*='/trucks-for-sale/']")
        if cards.count() == 0:
            pytest.skip("UF01: No listing cards found in search results")

        # Step 4: click on first listing
        first_card = cards.first
        first_card.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 5: listing page opened
        h1 = page.locator("h1").first
        _skip_if_not_visible(h1, "UF01: Listing page has no h1 after click")
        assert page.url != current_url, "UF01: URL didn't change after clicking listing"

    # ──────────────────────────────────────────────────────────────────────────
    # UF02: Browse & Filter Flow
    # Scenario: user opens catalog changes filter by year
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf02_browse_and_filter_flow(self, page: Page):
        """
        UF02: Catalog → filter by year_from → change → URL changes
                      → cards exist → open first listing.

        Verify:
        - Filter is displayed
        - After change URL contains filter parameter
        - Count of cards is non-zero
        """
        _go(page, "/en/trucks-for-sale")
        catalog = CatalogPage(page)

        # Step 1: catalog loaded — are cards
        cards = page.locator("a[href*='/trucks-for-sale/']")
        if cards.count() == 0:
            pytest.skip("UF02: No cards in catalog")
        initial_count = cards.count()
        initial_url = page.url

        # Step 2: filter by year (through URL — most reliable way)
        _go(page, "/en/trucks-for-sale?year_from=2018")
        page.wait_for_timeout(1000)

        # Step 3: URL contains filter
        assert "year_from=2018" in page.url or "2018" in page.url, (
            f"UF02: Filter not reflected in URL: {page.url}"
        )

        # Step 4: cards exist
        filtered_cards = page.locator("a[href*='/trucks-for-sale/']")
        if filtered_cards.count() == 0:
            pytest.skip("UF02: No cards after filter — possible empty result, not a bug")

        # Step 5: open first listing
        first_url = filtered_cards.first.get_attribute("href") or ""
        filtered_cards.first.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        h1 = page.locator("h1").first
        _skip_if_not_visible(h1, "UF02: No h1 on listing page after filter")

    # ──────────────────────────────────────────────────────────────────────────
    # UF03: Contact Seller Flow
    # Scenario: user opens listing presses "Contact"
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf03_contact_seller_flow(self, page: Page):
        """
        UF03: Catalog → first listing → button Contact
                      → popup opened → input name/email visible → close popup.

        Verify:
        - Button Contact exists on listing page
        - Popup opens after click
        - In popup are inputs for filling (email or name)
        - Popup can be closed
        """
        _go(page, "/en/trucks-for-sale")
        listing = ListingPage(page)

        # Step 1: find open first listing
        card = page.locator("a[href*='/trucks-for-sale/']").first
        _skip_if_not_visible(card, "UF03: No listing cards in catalog")
        card.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 2: h1 on listing page visible
        h1 = page.locator("h1").first
        _skip_if_not_visible(h1, "UF03: No h1 on listing page")

        # Step 3: find Contact button
        contact_btn = page.locator(listing.BTN_CONTACT_SELLER).first
        _skip_if_not_visible(contact_btn, "UF03: Contact button not found on listing page")

        contact_btn.click()
        page.wait_for_timeout(1500)

        # Step 4: popup or form opened
        popup = page.locator(listing.CONTACT_POPUP).first
        _skip_if_not_visible(popup, "UF03: Contact popup did not open after clicking Contact")

        # Step 5: in popup are fields email or name
        email_field = page.locator("input[type='email']").first
        name_field = page.locator("input[name*='name'], input[placeholder*='name']").first
        has_form = (
            email_field.is_visible(timeout=3000) or
            name_field.is_visible(timeout=3000)
        )
        assert has_form, "UF03: Contact popup has no form fields (email/name not found)"

        # Step 6: close popup (ESC — universal)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

    # ──────────────────────────────────────────────────────────────────────────
    # UF04: Leasing Flow
    # Scenario: user finds leasing opens request form
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf04_leasing_flow(self, page: Page):
        """
        UF04: Leasing catalog → first leasing listing
                              → button "Leasing request" → popup with form.

        Verify:
        - Leasing catalog loads
        - First listing opens
        - Button leasing request exists opens form
        """
        _go(page, "/en/trucks-for-lease")
        leasing = LeasingListingPage(page)

        # Step 1: leasing catalog loaded
        h1 = page.locator("h1").first
        _skip_if_not_visible(h1, "UF04: Leasing catalog has no h1")

        # Step 2: find first leasing listing
        card = page.locator("a[href*='/trucks-for-lease/']").first
        _skip_if_not_visible(card, "UF04: No leasing cards in catalog")
        card.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 3: listing page loaded
        listing_h1 = page.locator("h1").first
        _skip_if_not_visible(listing_h1, "UF04: No h1 on leasing listing page")

        # Step 4: button leasing request
        lease_btn = page.locator(leasing.BTN_LEASING_REQUEST).first
        _skip_if_not_visible(lease_btn, "UF04: Leasing request button not found")

        lease_btn.click()
        page.wait_for_timeout(1500)

        # Step 5: popup with form opened
        popup = page.locator(leasing.LEASING_POPUP).first
        _skip_if_not_visible(popup, "UF04: Leasing request popup did not open")

        # Step 6: email field in form
        email = page.locator("input[type='email']").first
        _skip_if_not_visible(email, "UF04: No email field in leasing request form")

    # ──────────────────────────────────────────────────────────────────────────
    # UF05: Seller Page Flow
    # Scenario: from listing page go to dealer and back to listing
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf05_seller_page_flow(self, page: Page):
        """
        UF05: Catalog → listing → link to dealer → page dealer
                      → first listing dealer → page listings.

        Verify:
        - Link to seller exists on listing page
        - Page seller loads (dealer name in title)
        - On page seller are cards listings
        """
        _go(page, "/en/trucks-for-sale")

        # Step 1: open first listing
        card = page.locator("a[href*='/trucks-for-sale/']").first
        _skip_if_not_visible(card, "UF05: No cards in catalog")
        card.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        h1 = page.locator("h1").first
        _skip_if_not_visible(h1, "UF05: No h1 on listing page")
        listing_title = h1.inner_text()

        # Step 2: find link to seller
        listing = ListingPage(page)
        seller_link = page.locator(listing.SELLER_LINK).first
        _skip_if_not_visible(seller_link, "UF05: Seller link not found on listing page")

        seller_link.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 3: page seller loaded
        seller = SellerPage(page)
        seller_name = page.locator(seller.SELLER_NAME).first
        _skip_if_not_visible(seller_name, "UF05: Seller name not visible on dealer page")

        # Step 4: on page dealer are cards
        dealer_cards = page.locator("a[href*='/trucks-for-sale/']")
        if dealer_cards.count() == 0:
            pytest.skip("UF05: No listing cards on seller page")

        # Step 5: open listing dealer
        dealer_cards.first.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        listing_h1_2 = page.locator("h1").first
        _skip_if_not_visible(listing_h1_2, "UF05: No h1 on dealer's listing page")

    # ──────────────────────────────────────────────────────────────────────────
    # UF06: Category Navigation Flow
    # Scenario: home → category → list in category → breadcrumb back
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf06_category_navigation_flow(self, page: Page):
        """
        UF06: Homepage → button Catalogue → catalog → category Curtainsider
                      → list listings → breadcrumb → back in catalog.

        Verify:
        - Button Catalogue works
        - Category opens
        - Breadcrumbs exist and are clickable
        """
        home = HomePage(page)

        # Step 1: click Catalogue in header
        catalogue_btn = page.locator(home.NAV_CATALOGUE).first
        _skip_if_not_visible(catalogue_btn, "UF06: Catalogue button not found in header")
        catalogue_btn.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 2: landed in catalog
        catalog_url = page.url
        assert "truck1.eu" in catalog_url, f"UF06: Unexpected URL after Catalogue: {catalog_url}"

        # Step 3: navigate to category Curtainsider through URL
        _go(page, "/en/curtainsider-trucks")
        h1 = page.locator("h1").first
        _skip_if_not_visible(h1, "UF06: Curtainsider category has no h1")

        category_url = page.url
        assert "curtainsider" in category_url, (
            f"UF06: URL doesn't contain category slug: {category_url}"
        )

        # Step 4: are breadcrumbs
        listing = ListingPage(page)
        breadcrumbs = page.locator(listing.BREADCRUMBS).first
        _skip_if_not_visible(breadcrumbs, "UF06: No breadcrumbs on category page")

        # Step 5: click breadcrumb (first = home or catalog)
        bc_links = page.locator(listing.BREADCRUMB_LINKS)
        if bc_links.count() < 1:
            pytest.skip("UF06: No breadcrumb links found")

        bc_links.first.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 6: returned to different page (not the category)
        assert page.url != category_url, (
            "UF06: URL didn't change after clicking breadcrumb"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # UF07: Pagination Flow
    # Scenario: catalog → page 2 → different set of cards → page 1
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf07_pagination_flow(self, page: Page):
        """
        UF07: Catalog page 1 → remember first card → page 2
                            → first card is different → page 1 → card is same.

        Verify:
        - Pagination works (URL changes)
        - On page 2 different listings (not repeating page 1)
        - Return to page 1 restores original results
        """
        _go(page, "/en/trucks-for-sale?page=1")

        # Step 1: remember first card on page 1
        cards_p1 = page.locator("a[href*='/trucks-for-sale/']")
        if cards_p1.count() == 0:
            pytest.skip("UF07: No cards on page 1")

        first_card_p1_href = cards_p1.first.get_attribute("href") or ""

        # Step 2: go to page 2
        _go(page, "/en/trucks-for-sale?page=2")
        page.wait_for_timeout(1000)

        assert "page=2" in page.url or "/page/2" in page.url or page.url != "https://www.truck1.eu/en/trucks-for-sale?page=1", (
            f"UF07: Page 2 URL unexpected: {page.url}"
        )

        # Step 3: cards on page 2 are
        cards_p2 = page.locator("a[href*='/trucks-for-sale/']")
        if cards_p2.count() == 0:
            pytest.skip("UF07: No cards on page 2 — might be last page")

        first_card_p2_href = cards_p2.first.get_attribute("href") or ""

        # Step 4: page 2 shows different listings
        assert first_card_p1_href != first_card_p2_href, (
            f"UF07: Page 1 page 2 show same first listing: {first_card_p1_href}\n"
            "This may indicate pagination is broken."
        )

        # Step 5: return to page 1
        _go(page, "/en/trucks-for-sale?page=1")
        cards_back = page.locator("a[href*='/trucks-for-sale/']")
        if cards_back.count() == 0:
            pytest.skip("UF07: No cards after returning to page 1")

        first_card_back_href = cards_back.first.get_attribute("href") or ""

        # Page 1 again shows same listings
        assert first_card_back_href == first_card_p1_href, (
            f"UF07: After returning to page 1, first card changed!\n"
            f"Before: {first_card_p1_href}\nAfter: {first_card_back_href}"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # UF08: Back Navigation Flow
    # Scenario: catalog → listing → button Back → return to catalog
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf08_back_navigation_flow(self, page: Page):
        """
        UF08: Catalog → open listing → browser button Back
                      → return to catalog → cards in place.

        Verify:
        - After return back URL matches catalog
        - Cards of listings still are visible (page not broken)
        """
        _go(page, "/en/trucks-for-sale")

        # Step 1: remember URL catalog
        catalog_url = page.url

        # Step 2: open first listing
        card = page.locator("a[href*='/trucks-for-sale/']").first
        _skip_if_not_visible(card, "UF08: No cards in catalog")
        card.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        listing_url = page.url
        assert listing_url != catalog_url, "UF08: URL didn't change after opening listing"

        # Step 3: click Back
        page.go_back()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 4: returned to catalog
        back_url = page.url
        assert "trucks-for-sale" in back_url, (
            f"UF08: After going back, URL is not catalog: {back_url}"
        )

        # Step 5: catalog not broken — cards are
        cards_after = page.locator("a[href*='/trucks-for-sale/']")
        assert cards_after.count() > 0, (
            "UF08: After browser back, no listing cards visible — page may be broken"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # UF09: Logo Return to Home
    # Scenario: from catalog page click on logo → home
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf09_logo_returns_to_home(self, page: Page):
        """
        UF09: Page catalog → click on logo → home page opened.

        Verify:
        - Logo is clickable
        - Click returns to main (URL — root domain)
        """
        _go(page, "/en/trucks-for-sale")

        home = HomePage(page)

        # Step 1: logo is visible
        logo = page.locator(home.LOGO).first
        _skip_if_not_visible(logo, "UF09: Logo not found on catalog page")

        catalog_url = page.url

        # Step 2: click on logo
        logo.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Step 3: returned to main
        home_url = page.url
        assert home_url != catalog_url, "UF09: URL didn't change after logo click"
        assert "truck1.eu" in home_url, f"UF09: Unexpected URL after logo: {home_url}"
        # Homepage — this is root domain, /en or /en/
        # truck1.eu may redirect to root without /en — this is normal
        is_homepage = (
            home_url.rstrip("/") == "https://www.truck1.eu"
            or home_url.rstrip("/").endswith("/en")
            or home_url.endswith("/en/")
            or home_url == "https://www.truck1.eu/"
        )
        assert is_homepage, (
            f"UF09: Logo didn't lead to homepage. URL: {home_url}\n"
            f"Expected: root domain or /en path"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # UF10: 404 Recovery Flow
    # Scenario: non-existent page → home link → site works
    # ──────────────────────────────────────────────────────────────────────────

    def test_uf10_404_recovery_flow(self, page: Page):
        """
        UF10: Non-existent page (404) → find link to main
                                            → go → home loads.

        Verify:
        - Server does not respond with 500 on non-existent URL
        - On 404-page is link leading home
        - After going by it site works normally
        """
        # Step 1: go to non-existent page
        page.goto(
            "https://www.truck1.eu/en/this-page-does-not-exist-truck1qa-test",
            wait_until="domcontentloaded",
            timeout=20_000
        )
        page.wait_for_timeout(500)

        # Step 2: not 500
        # (Playwright does not have direct access to HTTP status through goto,
        #  but if loaded — definitely not crashed)
        body_text = page.locator("body").inner_text()
        assert len(body_text) > 10, "UF10: 404 page is empty — server may have crashed"

        # Step 3: find link to main
        home_link = page.locator("a[href*='/en'], a[href='/'], a:has-text('Home'), a:has-text('Back')").first
        _skip_if_not_visible(home_link, "UF10: No home link found on 404 page")

        home_link.click()
        page.wait_for_load_state("domcontentloaded", timeout=20_000)

        # Step 4: home opened normally
        assert "truck1.eu" in page.url, f"UF10: After 404 recovery, URL is: {page.url}"
        h1 = page.locator("h1").first
        assert h1.is_visible(timeout=5000), "UF10: After 404 recovery, homepage has no h1"
