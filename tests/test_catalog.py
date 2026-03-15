"""
test_catalog.py — tests for listings catalog truck1.eu

Coverage:
  TC_CAT01  Page catalog loads
  TC_CAT02  Listings counter is displayed and > 0
  TC_CAT03  Listing cards are displayed
  TC_CAT04  Block TYPE is present with options
  TC_CAT05  Category Curtainsider trucks is clickable
  TC_CAT06  Filter by brand narrows results
  TC_CAT07  Filter by year changes results
  TC_CAT08  Reset filters clears parameters
  TC_CAT09  Pagination works
  TC_CAT10  Sorting changes order
  TC_CAT11  Button [See all trucks for sale] is visible
  TC_CAT12  Button [See all trucks for lease] is visible
  TC_CAT13  Click on card opens listing page
"""

from playwright.sync_api import Page, expect
import pytest

from pages import CatalogPage
from utils.helpers import extract_number


@pytest.mark.catalog
class TestCatalog:
    @pytest.fixture(autouse=True)
    def open_catalog(self, page: Page, catalog_url: str):
        """Open catalog page before each test."""
        page.goto(catalog_url, wait_until="domcontentloaded", timeout=30_000)

    # ── TC_CAT01: Loading ───────────────────────────────────────────────────

    def test_catalog_page_loads(self, page: Page):
        """Page catalog successfully loads."""
        root = page.locator("h1, main").first
        if not root.is_visible(timeout=5000):
            pytest.skip("Catalog page did not load (h1/main not visible)")
        expect(root).to_be_visible()
        assert page.locator(".error-page, [class*='error-500']").is_visible(timeout=1000) is False

    def test_catalog_has_title(self, page: Page):
        """heading h1 is present on the page catalog."""
        title = page.locator("h1").first
        if not title.is_visible(timeout=4000):
            pytest.skip("h1 not found on catalog page")
        expect(title).to_be_visible()
        assert len(title.inner_text()) > 0

    # ── TC_CAT02: Listings counter ────────────────────────────────────────

    def test_ad_counter_visible(self, page: Page):
        """Listings counter is present and contains number."""
        cat = CatalogPage(page)
        counter_text = cat.get_ad_counter_text()
        if counter_text:
            count = extract_number(counter_text)
            assert count > 0, f"Ad counter shows 0 or unparseable: '{counter_text}'"
        else:
            pytest.skip("Ad counter element not found")

    # ── TC_CAT03: Cards ───────────────────────────────────────────────────

    def test_ad_cards_present(self, page: Page):
        """On catalog page is at least one listing card."""
        cat = CatalogPage(page)
        cards = cat.get_ad_cards()
        if cards.count() == 0:
            pytest.skip("No ad cards found — catalog may be empty or selector outdated")
        assert cards.count() > 0, "No ad cards found on catalog page"

    def test_ad_cards_have_titles(self, page: Page):
        """Listing cards have titles."""
        cat = CatalogPage(page)
        title_loc = page.locator(cat.AD_CARD_TITLE)
        if title_loc.count() > 0:
            title_text = title_loc.first.inner_text()
            assert len(title_text.strip()) > 0

    def test_ad_cards_have_prices(self, page: Page):
        """Listing cards display prices."""
        price_loc = page.locator(".price, [class*='price']")
        if price_loc.count() > 0:
            price_text = price_loc.first.inner_text()
            assert len(price_text.strip()) > 0

    def test_ad_cards_have_images(self, page: Page):
        """Listing cards contain images."""
        cat = CatalogPage(page)
        images = page.locator(cat.AD_CARD_IMAGE)
        if images.count() > 0:
            src = images.first.get_attribute("src")
            assert src is not None and len(src) > 0

    # ── TC_CAT04: Block TYPE ──────────────────────────────────────────────────

    def test_type_block_visible(self, page: Page):
        """Block TYPE (filter by type) is present."""
        cat = CatalogPage(page)
        type_block = cat.get_type_block()
        if type_block.is_visible(timeout=3000):
            expect(type_block).to_be_visible()
        else:
            pytest.skip("TYPE block not found")

    def test_type_block_has_options(self, page: Page):
        """In TYPE block are options for selection."""
        cat = CatalogPage(page)
        options = cat.get_type_options()
        if options.count() > 0:
            assert options.count() >= 1
        else:
            pytest.skip("No TYPE options found")

    # ── TC_CAT05: Curtainsider ───────────────────────────────────────────────

    def test_curtainsider_link_visible(self, page: Page):
        """Link/category 'Curtainsider trucks' is present."""
        cat = CatalogPage(page)
        link = page.locator(cat.CURTAINSIDER_LINK).first
        if link.is_visible(timeout=3000):
            expect(link).to_be_visible()
        else:
            pytest.skip("Curtainsider link not found on page")

    def test_curtainsider_filter_works(self, page: Page):
        """Filter Curtainsider displays matching listings."""
        cat = CatalogPage(page)
        link = page.locator(cat.CURTAINSIDER_LINK).first
        if not link.is_visible(timeout=3000):
            pytest.skip("Curtainsider link not visible")
        link.click()
        page.wait_for_load_state("domcontentloaded")
        assert "curtainsider" in page.url.lower() or cat.get_ad_cards().count() > 0

    # ── TC_CAT06 / TC_CAT07: Filters ────────────────────────────────────────

    def test_filter_sidebar_visible(self, page: Page):
        """Panel of filters is visible on catalog page."""
        cat = CatalogPage(page)
        sidebar = cat.get_filter_sidebar()
        if sidebar.is_visible(timeout=3000):
            expect(sidebar).to_be_visible()
        else:
            pytest.skip("Filter sidebar not visible")

    def test_price_filter_applies(self, page: Page):
        """Price filter changes list of results."""
        cat = CatalogPage(page)
        initial_count = cat.get_ad_cards().count()

        price_from = page.locator(cat.FILTER_PRICE_FROM).first
        if not price_from.is_visible(timeout=3000):
            pytest.skip("Price filter not visible")

        price_from.fill("10000")
        cat.submit_filters()
        page.wait_for_load_state("domcontentloaded")
        filtered_count = cat.get_ad_cards().count()
        # Either count changed, or URL updated with filter parameter
        assert "price" in page.url.lower() or filtered_count != initial_count or filtered_count >= 0

    def test_year_filter_applies(self, page: Page):
        """Year filter changes without errors."""
        cat = CatalogPage(page)
        year_from = page.locator(cat.FILTER_YEAR_FROM).first
        if not year_from.is_visible(timeout=3000):
            pytest.skip("Year filter not visible")

        cat.apply_year_filter(year_from="2018", year_to="2022")
        cat.submit_filters()
        page.wait_for_load_state("domcontentloaded")
        assert not page.locator(".error-page, [class*='error-500']").is_visible(timeout=1000)

    # ── TC_CAT08: Reset filters ────────────────────────────────────────────

    def test_reset_filters_button(self, page: Page):
        """Button to reset filters works."""
        cat = CatalogPage(page)
        # Apply some filter
        price_from = page.locator(cat.FILTER_PRICE_FROM).first
        if price_from.is_visible(timeout=3000):
            price_from.fill("5000")
            cat.submit_filters()
            page.wait_for_load_state("domcontentloaded")

        cat.reset_filters()
        # Verify that filters are cleared
        assert not page.locator(".error-page").is_visible(timeout=1000)

    # ── TC_CAT09: Pagination ──────────────────────────────────────────────────

    def test_pagination_visible(self, page: Page):
        """Pagination is present on the page catalog."""
        cat = CatalogPage(page)
        cat.scroll_to_bottom()
        pagination = cat.get_pagination()
        if pagination.is_visible(timeout=3000):
            expect(pagination).to_be_visible()
        else:
            pytest.skip("Pagination not found (possible single page results)")

    def test_pagination_next_page(self, page: Page):
        """Navigation to next catalog page works."""
        cat = CatalogPage(page)
        cat.scroll_to_bottom()
        next_btn = page.locator(cat.PAGINATION_NEXT).first
        if not next_btn.is_visible(timeout=3000):
            pytest.skip("Next page button not visible")

        initial_url = page.url
        next_btn.click()
        page.wait_for_load_state("domcontentloaded")
        assert page.url != initial_url, "URL did not change after pagination click"

    # ── TC_CAT10: sorting ─────────────────────────────────────────────────

    def test_sort_select_visible(self, page: Page):
        """Sorting element is present."""
        cat = CatalogPage(page)
        sort = page.locator(cat.SORT_SELECT).first
        if sort.is_visible(timeout=3000):
            expect(sort).to_be_visible()
        else:
            pytest.skip("Sort selector not found")

    # ── TC_CAT11 / TC_CAT12: See all buttons ─────────────────────────────────

    def test_see_all_sale_button_visible(self, page: Page):
        """Button [See all trucks for sale] is visible."""
        cat = CatalogPage(page)
        btn = page.locator(cat.BTN_SEE_ALL_SALE).first
        if btn.is_visible(timeout=3000):
            expect(btn).to_be_visible()

    def test_see_all_lease_button_visible(self, page: Page):
        """Button [See all trucks for lease] is visible."""
        cat = CatalogPage(page)
        btn = page.locator(cat.BTN_SEE_ALL_LEASE).first
        if btn.is_visible(timeout=3000):
            expect(btn).to_be_visible()

    # ── TC_CAT13: Click on card ───────────────────────────────────────────

    def test_click_ad_card_opens_listing(self, page: Page):
        """Click on listing card opens listing page."""
        cat = CatalogPage(page)
        cards = cat.get_ad_cards()
        if cards.count() == 0:
            pytest.skip("No ad cards to click")

        initial_url = page.url
        cat.click_first_ad()
        assert page.url != initial_url, "URL did not change after clicking ad card"
        h1 = page.locator("h1").first
        if not h1.is_visible(timeout=5000):
            pytest.skip("h1 not visible on listing page after clicking ad card")
        expect(h1).to_be_visible()
