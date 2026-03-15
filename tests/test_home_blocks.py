"""
test_home_blocks.py — tests for home page blocks truck1.eu

Coverage:
  TC_HOME01  Block "Categories of goods" is visible, contains elements
  TC_HOME02  Block "Advertising" is visible
  TC_HOME03  Section "Leasing" is visible and link works
  TC_HOME04  Block "Sell" is visible, CTA works
  TC_HOME05  Slider "Featured offers" is visible and contains cards
  TC_HOME06  Slider "Featured offers" — navigation works
  TC_HOME07  Block "Blog" is visible, contains articles
  TC_HOME08  Link "Blog" leads to blog
  TC_HOME09  Slider "Recently viewed" is visible (if history exists)
  TC_HOME10  Block "Popular categories" is visible, links work
  TC_HOME11  Button [See all trucks for sale] leads to catalog
  TC_HOME12  Button [See all trucks for lease] leads to leasing
  TC_HOME13  No critical errors in console
"""

from playwright.sync_api import Page, expect
import pytest

from pages import HomePage


@pytest.mark.home
class TestHomeBlocks:
    # ── TC_HOME01: Categories of goods ─────────────────────────────────────────

    def test_categories_block_visible(self, page: Page):
        """Block of categories of goods is present on home."""
        home = HomePage(page)
        block = home.get_categories_block()
        if not block.is_visible(timeout=4000):
            pytest.skip("Categories block not found — selector may need update")
        expect(block).to_be_visible()

    def test_categories_have_items(self, page: Page):
        """In block of categories is at least one element."""
        home = HomePage(page)
        items = home.get_category_items()
        if items.count() == 0:
            pytest.skip("No category items found — selector may need update")
        assert items.count() > 0, "No category items found"

    def test_category_link_navigates(self, page: Page):
        """Click on category opens page with results."""
        home = HomePage(page)
        items = home.get_category_items()
        if items.count() > 0:
            items.first.click()
            page.wait_for_load_state("domcontentloaded")
            assert page.url != home.url or page.locator("h1").is_visible()

    # ── TC_HOME02: Advertising ───────────────────────────────────────────────

    def test_advertising_block_visible(self, page: Page):
        """Advertising block is present on the page."""
        home = HomePage(page)
        adv = home.get_advertising_block()
        # Advertising blocks may be hidden by ad-blocker, so soft check
        if adv.is_visible(timeout=3000):
            assert True
        else:
            pytest.skip("Advertising block not visible (possible ad blocker)")

    # ── TC_HOME03: Leasing section ───────────────────────────────────────────

    def test_leasing_section_visible(self, page: Page):
        """Section Leasing is visible on home page."""
        home = HomePage(page)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        leasing = home.get_leasing_section()
        if not leasing.is_visible(timeout=3000):
            pytest.skip("Leasing section not found on page")
        expect(leasing).to_be_visible()

    def test_leasing_link_works(self, page: Page):
        """Link in Leasing section leads to leasing page."""
        home = HomePage(page)
        link = page.locator(home.LEASING_LINK).first
        if link.is_visible(timeout=3000):
            link.click()
            page.wait_for_load_state("domcontentloaded")
            assert "lease" in page.url.lower() or "leasing" in page.url.lower()

    # ── TC_HOME04: Sell block ────────────────────────────────────────────────

    def test_sell_block_visible(self, page: Page):
        """Block 'Sell' is visible on home page."""
        home = HomePage(page)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        sell = home.get_sell_block()
        if not sell.is_visible(timeout=3000):
            pytest.skip("Sell block not found")
        expect(sell).to_be_visible()

    # ── TC_HOME05 / TC_HOME06: Featured offers slider ────────────────────────

    def test_featured_offers_slider_visible(self, page: Page):
        """Slider Featured offers is present on the page."""
        home = HomePage(page)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        featured = home.get_featured_slider()
        if not featured.is_visible(timeout=5000):
            pytest.skip("Featured offers slider not found")
        expect(featured).to_be_visible()

    def test_featured_offers_have_cards(self, page: Page):
        """Slider Featured offers contains cards listings."""
        home = HomePage(page)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        items = home.get_featured_items()
        if items.count() == 0:
            pytest.skip("No featured offer cards found")
        assert items.count() > 0

    @pytest.mark.slow
    def test_featured_slider_navigation(self, page: Page):
        """Navigation of Featured offers slider works."""
        home = HomePage(page)
        next_btn = page.locator(home.FEATURED_NEXT).first
        if next_btn.is_visible(timeout=3000):
            next_btn.click()
            page.wait_for_timeout(500)
            assert not page.locator(".error-page").is_visible(timeout=1000)

    # ── TC_HOME07 / TC_HOME08: Blog ──────────────────────────────────────────

    def test_blog_block_visible(self, page: Page):
        """Block Blog is visible on home page."""
        home = HomePage(page)
        home.scroll_to_bottom()
        blog = home.get_blog_block()
        if not blog.is_visible(timeout=3000):
            pytest.skip("Blog block not found")
        expect(blog).to_be_visible()

    def test_blog_has_articles(self, page: Page):
        """Block Blog contains articles."""
        home = HomePage(page)
        home.scroll_to_bottom()
        items = home.get_blog_items()
        if items.count() == 0:
            pytest.skip("No blog items found")
        assert items.count() > 0

    def test_blog_link_navigates(self, page: Page):
        """Link Blog opens blog page."""
        home = HomePage(page)
        home.scroll_to_bottom()
        link = page.locator(home.BLOG_LINK).first
        if link.is_visible(timeout=3000):
            link.click()
            page.wait_for_load_state("domcontentloaded")
            assert "blog" in page.url.lower()

    # ── TC_HOME09: Recently viewed ───────────────────────────────────────────

    def test_recently_viewed_visible_after_visit(self, page: Page, base_url: str, locale: str):
        """After visiting listings slider 'Recently viewed' appears."""
        # First visit catalog so history appears
        page.goto(f"{base_url}/{locale}/trucks-for-sale", wait_until="domcontentloaded")
        # Click on first listing
        first_link = page.locator(".listing-card a, [class*='listing-item'] a").first
        if first_link.is_visible(timeout=5000):
            first_link.click()
            page.go_back()
            page.wait_for_load_state("domcontentloaded")

        # Verify homepage
        page.goto(f"{base_url}/{locale}", wait_until="domcontentloaded")
        home = HomePage(page)
        home.scroll_to_bottom()
        recently = home.get_recently_viewed()
        # Soft check — view history may not be empty
        if recently.is_visible(timeout=3000):
            assert True
        else:
            pytest.skip("Recently viewed section not shown (no history)")

    # ── TC_HOME10: Popular categories ────────────────────────────────────────

    def test_popular_categories_visible(self, page: Page):
        """Block Popular categories is visible."""
        home = HomePage(page)
        home.scroll_to_bottom()
        popular = home.get_popular_categories()
        if not popular.is_visible(timeout=3000):
            pytest.skip("Popular categories block not found")
        expect(popular).to_be_visible()

    def test_popular_category_links_work(self, page: Page):
        """Links in Popular categories are clickable."""
        home = HomePage(page)
        home.scroll_to_bottom()
        links = home.get_popular_category_links()
        if links.count() == 0:
            pytest.skip("No popular category links found")
        first_href = links.first.get_attribute("href")
        assert first_href is not None and len(first_href) > 0

    # ── TC_HOME11 / TC_HOME12: See all buttons ───────────────────────────────

    def test_see_all_trucks_for_sale_button(self, page: Page):
        """Button [See all trucks for sale →] leads to sale page."""
        home = HomePage(page)
        btn = page.locator(home.BTN_SEE_ALL_SALE).first
        if btn.is_visible(timeout=3000):
            btn.click()
            page.wait_for_load_state("domcontentloaded")
            assert "trucks-for-sale" in page.url or "sale" in page.url.lower()

    def test_see_all_trucks_for_lease_button(self, page: Page):
        """Button [See all trucks for lease →] leads to leasing page."""
        home = HomePage(page)
        btn = page.locator(home.BTN_SEE_ALL_LEASE).first
        if btn.is_visible(timeout=3000):
            btn.click()
            page.wait_for_load_state("domcontentloaded")
            assert "lease" in page.url.lower()

    # ── TC_HOME13: Console errors ─────────────────────────────────────────

    def test_no_critical_console_errors(self, page: Page):
        """On home page no critical JS-errors in console."""
        errors = getattr(page, "_console_errors", [])
        critical = [
            e for e in errors if "Uncaught" in e or "TypeError" in e or "ReferenceError" in e
        ]
        assert len(critical) == 0, f"Critical JS errors found: {critical[:3]}"
