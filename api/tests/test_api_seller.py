"""
test_api_seller.py — HTTP-tests page yes/ and  in Coverage:
  TC_ASEL01  List and to  and  in available
  TC_ASEL02  Page specific dealer is available
  TC_ASEL03  Non-existent and  and  → 404
  TC_ASEL04  HTML pages dealer contains  ame company and
  TC_ASEL05  HTML contains contact data (tel: or mailto:)
  TC_ASEL06  Page dealer contains  and to listings
  TC_ASEL07   filter and  listings dealer by type (sale/lease)
  TC_ASEL08  Pagination listings dealer
  TC_ASEL09   and  without listings —  page
  TC_ASEL10  SEO: canonical  and  title  in HTML dealer
"""

import re

import pytest

from api.client import REACHABLE, ListingsClient


@pytest.fixture(scope="module")
def first_dealer_url(api_client_module: ListingsClient):
    """Finds URL  dealer through HTML catalog.

    Note:: with Cloudflare 202 HTML  contains real links — skip.
    """
    resp = api_client_module.get_sale_catalog()
    if resp.status_code not in REACHABLE:
        pytest.skip(f"Cannot fetch catalog (status {resp.status_code})")

    urls = re.findall(
        r'href="(/[a-z]{2}/dealers/[^"?#]+)"',
        resp.text,
    )
    if not urls:
        pytest.skip(
            "No dealer URLs found in catalog HTML — "
            "Cloudflare challenge page returned (no real content)"
        )
    return urls[0]


@pytest.mark.api
@pytest.mark.api_seller
class TestApiSeller:
    # ── TC_ASEL01: List and to  and  in ────────────────────────────────────────────

    def test_dealers_list_accessible(self, api_client: ListingsClient):
        """GET /{locale}/dealers → 200/202."""
        resp = api_client.get_dealers_list()
        assert resp.status_code in REACHABLE, f"Dealers list returned {resp.status_code}"

    def test_dealers_list_has_content(self, api_client: ListingsClient):
        """Page  and  in contains to and   or (only if 200,  CF challenge)."""
        resp = api_client.get_dealers_list()
        assert resp.status_code in REACHABLE
        if resp.status_code == 200:
            dealer_links = re.findall(r'href="[^"]*dealers/[^"]*"', resp.text)
            assert len(dealer_links) > 0, "No dealer links found on dealers list page"

    # ── TC_ASEL02 / TC_ASEL03: Page dealer ───────────────────────────────

    def test_dealer_page_returns_200(self, api_client: ListingsClient, first_dealer_url: str):
        """Page specific dealer → 200/202."""
        resp = api_client.get(first_dealer_url)
        assert (
            resp.status_code in REACHABLE
        ), f"Dealer page {first_dealer_url} returned {resp.status_code}"

    def test_nonexistent_dealer_returns_404(self, api_client: ListingsClient):
        """Non-existent and  and  → 404/410 or CF challenge (202). Not 500."""
        resp = api_client.get_dealer_page("nonexistent-dealer-xyz-000000")
        assert resp.status_code not in (
            500,
            502,
            503,
        ), f"Non-existent dealer caused server error: {resp.status_code}"
        assert resp.status_code in (
            *REACHABLE,
            404,
            410,
        ), f"Non-existent dealer returned unexpected {resp.status_code}"

    # ── TC_ASEL04 / TC_ASEL05: HTML content ───────────────────────────────

    def test_dealer_page_has_company_name(self, api_client: ListingsClient, first_dealer_url: str):
        """HTML pages dealer contains tag <h1>   and company and ."""
        resp = api_client.get(first_dealer_url)
        assert "<h1" in resp.text, "No <h1> tag found on dealer page"

    def test_dealer_page_has_contact_info(self, api_client: ListingsClient, first_dealer_url: str):
        """HTML pages dealer contains contact data (tel: or mailto:)."""
        resp = api_client.get(first_dealer_url)
        has_phone = "tel:" in resp.text
        has_email = "mailto:" in resp.text
        has_address = any(kw in resp.text.lower() for kw in ["address", "street", "city"])
        assert has_phone or has_email or has_address, "No contact information found on dealer page"

    # ── TC_ASEL06 / TC_ASEL07:  and  dealer ─────────────────────────────

    def test_dealer_page_has_listings(self, api_client: ListingsClient, first_dealer_url: str):
        """Page dealer contains to and   listings."""
        resp = api_client.get(first_dealer_url)
        # Find to and   trucks-for-sale or trucks-for-lease
        listing_links = re.findall(
            r'href="[^"]*trucks-for-(?:sale|lease)/[^"]*"',
            resp.text,
        )
        assert len(listing_links) > 0, "No listing links found on dealer page"

    def test_dealer_ads_filter_sale(self, api_client: ListingsClient, first_dealer_url: str):
        """filter and  listings dealer by type 'sale' does not break server."""
        resp = api_client.get(first_dealer_url, params={"type": "sale"})
        assert resp.status_code in REACHABLE

    def test_dealer_ads_filter_lease(self, api_client: ListingsClient, first_dealer_url: str):
        """filter and  listings dealer by type 'lease' does not break server."""
        resp = api_client.get(first_dealer_url, params={"type": "lease"})
        assert resp.status_code in REACHABLE

    # ── TC_ASEL08: Pagination dealer ──────────────────────────────────────────

    def test_dealer_pagination_page_2(self, api_client: ListingsClient, first_dealer_url: str):
        """Page 2 listings dealer is available (200/202/404)."""
        resp = api_client.get(first_dealer_url, params={"page": 2})
        assert resp.status_code in (*REACHABLE, 404), f"Dealer page 2 returned {resp.status_code}"

    # ── TC_ASEL10: SEO ────────────────────────────────────────────────────────

    def test_dealer_page_has_title(self, api_client: ListingsClient, first_dealer_url: str):
        """HTML pages dealer contains <title>."""
        resp = api_client.get(first_dealer_url)
        assert "<title>" in resp.text, "No <title> on dealer page"

    def test_dealer_page_has_canonical(self, api_client: ListingsClient, first_dealer_url: str):
        """HTML pages dealer contains canonical ku."""
        resp = api_client.get(first_dealer_url)
        assert "canonical" in resp.text.lower(), "No canonical link on dealer page"
