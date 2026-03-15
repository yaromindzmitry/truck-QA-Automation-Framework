"""
test_api_catalog.py — tests for listings catalog through HTTP/API

Coverage:
  TC_ACAT01  Sale catalog is accessible (200/202)
  TC_ACAT02  Leasing catalog is accessible (200/202)
  TC_ACAT03  Filter by brand works (URL parameters)
  TC_ACAT04  Filter by year works
  TC_ACAT05  Filter by price works
  TC_ACAT06  Pagination — page 2 is available
  TC_ACAT07  Very large page number is handled correctly
  TC_ACAT08  Category Curtainsider is available
  TC_ACAT09  Search by keyword returns 200/202
  TC_ACAT10  Empty search does not break server
  TC_ACAT11  XSS in parameters is not reflected in response (if 200)
  TC_ACAT12  SQL injection in parameters does not cause 500
  TC_ACAT13  Very long parameter is handled correctly
  TC_ACAT14  Non-existent brand returns 200/202 (empty result)

Note:: Cloudflare returns 202 for headless clients. REACHABLE = (200, 202).
"""

import pytest
from api.client import ListingsClient, SearchClient, REACHABLE


@pytest.mark.api
@pytest.mark.api_catalog
class TestApiCatalog:

    # ── TC_ACAT01 / TC_ACAT02: Catalogs are accessible ────────────────────────────

    def test_sale_catalog_accessible(self, api_client: ListingsClient):
        """GET trucks-for-sale → 200/202, body is not empty."""
        resp = api_client.get_sale_catalog()
        assert resp.status_code in REACHABLE, (
            f"Sale catalog returned {resp.status_code}"
        )
        assert len(resp.text) > 1000, "Response body too short"

    def test_lease_catalog_accessible(self, api_client: ListingsClient):
        """GET trucks-for-lease → 200/202, body is not empty."""
        resp = api_client.get_lease_catalog()
        assert resp.status_code in REACHABLE, (
            f"Lease catalog returned {resp.status_code}"
        )
        assert len(resp.text) > 1000, "Response body too short"

    # ── TC_ACAT03 / TC_ACAT04 / TC_ACAT05: Filters ──────────────────────────

    @pytest.mark.parametrize("make", ["Volvo", "Scania", "MAN", "Mercedes-Benz", "DAF"])
    def test_filter_by_make(self, api_client: ListingsClient, make: str):
        """GET trucks-for-sale?make=X → 200/202 (server responded)."""
        resp = api_client.get_sale_catalog(make=make)
        assert resp.status_code in REACHABLE, (
            f"Filter by make='{make}' returned {resp.status_code}"
        )

    def test_filter_by_year_range(self, api_client: ListingsClient):
        """Filter year_from/year_to does not break server."""
        resp = api_client.get_sale_catalog(year_from=2018, year_to=2022)
        assert resp.status_code in REACHABLE

    def test_filter_by_price_range(self, api_client: ListingsClient):
        """Filter price_from/price_to does not break server."""
        resp = api_client.get_sale_catalog(price_from=10000, price_to=100000)
        assert resp.status_code in REACHABLE

    def test_combined_filters(self, api_client: ListingsClient):
        """Combined filter (make + year + price) does not break server."""
        resp = api_client.get_sale_catalog(
            make="Volvo",
            year_from=2019,
            price_to=80000,
        )
        assert resp.status_code in REACHABLE

    # ── TC_ACAT06 / TC_ACAT07: Pagination ────────────────────────────────────

    def test_pagination_page_2_accessible(self, api_client: ListingsClient):
        """Page 2 catalog is available (200/202/404)."""
        resp = api_client.get_sale_catalog(page=2)
        assert resp.status_code in (*REACHABLE, 404), (
            f"Page 2 returned unexpected status {resp.status_code}"
        )

    def test_pagination_pages_differ(self, api_client: ListingsClient):
        """Page 1 and page 2 contain different content (if both 200)."""
        resp1 = api_client.get_sale_catalog(page=1)
        resp2 = api_client.get_sale_catalog(page=2)

        if resp2.status_code not in (200,):
            pytest.skip("Page 2 not available or behind CF challenge")

        assert resp1.text != resp2.text, "Page 1 and Page 2 content are identical"

    def test_very_high_page_number(self, api_client: ListingsClient):
        """Very high page number (99999) is handled without 500."""
        resp = api_client.get_sale_catalog(page=99999)
        assert resp.status_code not in (500, 502, 503), (
            f"High page number caused server error: {resp.status_code}"
        )
        assert resp.status_code in (*REACHABLE, 404, 422), (
            f"High page number returned unexpected {resp.status_code}"
        )

    # ── TC_ACAT08: Curtainsider category ────────────────────────────────────

    def test_curtainsider_category(self, search_client: SearchClient):
        """GET curtainsider-trucks → 200/202."""
        resp = search_client.get_curtainsider_category()
        assert resp.status_code in REACHABLE, (
            f"Curtainsider category returned {resp.status_code}"
        )

    @pytest.mark.parametrize("category", [
        "curtainsider-trucks",
        "tipper-trucks",
        "refrigerator-trucks",
    ])
    def test_truck_categories_accessible(
        self, search_client: SearchClient, category: str
    ):
        """Main truck categories are accessible (200/202)."""
        resp = search_client.get_category_page(category)
        assert resp.status_code in REACHABLE, (
            f"Category '{category}' returned {resp.status_code}"
        )

    # ── TC_ACAT09 / TC_ACAT10: Search ────────────────────────────────────────

    @pytest.mark.parametrize("query", ["Volvo FH", "Scania R", "DAF XF", "tipper"])
    def test_search_returns_200(self, search_client: SearchClient, query: str):
        """Search by keyword returns 200/202."""
        resp = search_client.search_listings(query)
        assert resp.status_code in REACHABLE, (
            f"Search '{query}' returned {resp.status_code}"
        )

    def test_empty_search_returns_200(self, search_client: SearchClient):
        """Empty search does not break server."""
        resp = search_client.search_listings("")
        assert resp.status_code in (*REACHABLE, 422), (
            f"Empty search returned {resp.status_code}"
        )

    def test_search_unicode_query(self, search_client: SearchClient):
        """Search with Unicode characters is handled correctly."""
        resp = search_client.search_listings("truck")
        assert resp.status_code in (*REACHABLE, 422)

    # ── TC_ACAT11 / TC_ACAT12 / TC_ACAT13: Security tests ─────────────────

    @pytest.mark.security
    def test_xss_in_search_not_reflected(self, search_client: SearchClient):
        """XSS in search parameter is not reflected without escaping (if 200)."""
        xss_payload = "<script>alert('xss')</script>"
        resp = search_client.search_listings(xss_payload)
        assert resp.status_code in (*REACHABLE, 400, 422)
        # Verify only if we get real HTML (not CF challenge)
        if resp.status_code == 200:
            assert "<script>alert('xss')</script>" not in resp.text, (
                "XSS payload reflected unescaped in response!"
            )

    @pytest.mark.security
    def test_sql_injection_in_filter(self, api_client: ListingsClient):
        """SQL injection in parameter does not cause server error (not 500)."""
        resp = api_client.get_sale_catalog(make="' OR '1'='1")
        assert resp.status_code != 500, "SQL injection caused 500 Internal Server Error!"
        assert resp.status_code in (*REACHABLE, 400, 422), (
            f"SQL injection returned unexpected {resp.status_code}"
        )

    def test_very_long_parameter(self, api_client: ListingsClient):
        """Very long parameter value is handled correctly."""
        long_value = "A" * 5000
        resp = api_client.get_sale_catalog(make=long_value)
        assert resp.status_code != 500
        assert resp.status_code in (*REACHABLE, 400, 413, 422, 414), (
            f"Long param returned unexpected {resp.status_code}"
        )

    def test_nonexistent_make_returns_200(self, api_client: ListingsClient):
        """Non-existent brand does not break catalog (empty result)."""
        resp = api_client.get_sale_catalog(make="NonExistentBrand_XYZ_999")
        assert resp.status_code in REACHABLE, (
            f"Non-existent make filter returned {resp.status_code}"
        )
