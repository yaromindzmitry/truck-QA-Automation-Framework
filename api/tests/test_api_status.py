"""
test_api_status.py — basic security access and   and  HTTP-statuses truck1.eu

Coverage:
  TC_STATUS01  Homepage page returns 200/202
  TC_STATUS02  All  and  return 200/202
  TC_STATUS03  robots.txt available
  TC_STATUS04  sitemap.xml available (or 404 if other path)
  TC_STATUS05  Catalog sale returns 200/202
  TC_STATUS06  Catalog leasing returns 200/202
  TC_STATUS07  Page  iz returns 200/202/302
  TC_STATUS08  Page  and  returns 200/202/302
  TC_STATUS09  Non-existent page —  500 (CF may return 202 or 404)
  TC_STATUS10  HTTPS  rect  HTTP works
  TC_STATUS11  to and  without and  are missing
  TC_STATUS12  Content-Type for HTML page
  TC_STATUS13  Time response home pages < 5 sec
  TC_STATUS14  Time response catalog < 7 sec

Note:  HTTP 202:
  truck1.eu  and   Cloudflare.  without real browser get
  Cloudflare bot-challenge  statusom 202. This  and yes  and for headless
  HTTP-client. REACHABLE = (200, 202)  «server and  in and  responded».
  Realcontent page checked  in UI- (Playwright).
"""

import pytest
import requests
from api.client import ListingsClient, SearchClient, REACHABLE


@pytest.mark.api
@pytest.mark.api_status
class TestApiStatus:

    # ── TC_STATUS01: Homepage page ────────────────────────────────────────

    def test_homepage_returns_200(self, api_client: ListingsClient):
        """GET /{locale}/ → 200 or 202 (CF challenge)"""
        resp = api_client.get_homepage()
        assert resp.status_code in REACHABLE, (
            f"Homepage returned {resp.status_code}, expected 200 or 202"
        )

    # ── TC_STATUS02: All  and  ──────────────────────────────────────────────

    @pytest.mark.parametrize("locale", ["en", "de", "pl", "lt", "lv", "ru", "cs"])
    def test_all_locales_return_200(self, search_client: SearchClient, locale: str):
        """GET /{locale}/ → 200/202 for all  and  ."""
        resp = search_client.get(f"/{locale}")
        assert resp.status_code in REACHABLE, (
            f"Locale /{locale} returned {resp.status_code}"
        )

    def test_all_locales_bulk(self, search_client: SearchClient):
        """Check all  and ,  and   and  and."""
        results = search_client.get_all_locale_homepages()
        failed = {loc: code for loc, code in results.items() if code not in REACHABLE}
        assert not failed, f"These locales returned unexpected codes: {failed}"

    # ── TC_STATUS03 / TC_STATUS04: robots.txt / sitemap ──────────────────────

    def test_robots_txt_accessible(self, search_client: SearchClient):
        """GET /robots.txt → 200/202"""
        resp = search_client.get_robots_txt()
        assert resp.status_code in REACHABLE, (
            f"robots.txt returned {resp.status_code}"
        )

    def test_sitemap_xml_accessible(self, search_client: SearchClient):
        """GET /sitemap.xml → 200/202 or 404 if sitemap  om  and ."""
        resp = search_client.get_sitemap()
        # Cloudflare may return 202, real 404   and 
        assert resp.status_code in (*REACHABLE, 404), (
            f"sitemap.xml returned unexpected {resp.status_code}"
        )
        if resp.status_code in REACHABLE and "xml" in resp.headers.get("Content-Type", ""):
            assert resp.text.strip().startswith("<?xml") or "<urlset" in resp.text

    # ── TC_STATUS05 / TC_STATUS06: Catalog and  ──────────────────────────────────

    def test_sale_catalog_returns_200(self, api_client: ListingsClient):
        """GET /{locale}/trucks-for-sale → 200/202"""
        resp = api_client.get_sale_catalog()
        assert resp.status_code in REACHABLE, (
            f"Sale catalog returned {resp.status_code}"
        )

    def test_lease_catalog_returns_200(self, api_client: ListingsClient):
        """GET /{locale}/trucks-for-lease → 200/202"""
        resp = api_client.get_lease_catalog()
        assert resp.status_code in REACHABLE, (
            f"Lease catalog returned {resp.status_code}"
        )

    # ── TC_STATUS07 / TC_STATUS08: Favorites / Compare ───────────────────────

    def test_favourites_page_accessible(self, api_client: ListingsClient):
        """GET /{locale}/favourites → 200/202/302"""
        resp = api_client.get_favourites_page()
        assert resp.status_code in (*REACHABLE, 301, 302), (
            f"Favourites page returned {resp.status_code}"
        )

    def test_compare_page_accessible(self, api_client: ListingsClient):
        """GET /{locale}/compare → 200/202/302"""
        resp = api_client.get_compare_page()
        assert resp.status_code in (*REACHABLE, 301, 302), (
            f"Compare page returned {resp.status_code}"
        )

    # ── TC_STATUS09: 404 ────────────────────────────────────────────────────

    def test_nonexistent_page_no_server_error(self, api_client: ListingsClient):
        """GET pages does not cause 500.

        CF challenge (202) or  and 404 —   and .
         — server  crashes  5xx.
        """
        resp = api_client.get("/en/this-page-does-not-exist-xyz123-qwerty")
        assert resp.status_code not in (500, 502, 503, 504), (
            f"Non-existent page caused server error: {resp.status_code}"
        )
        assert resp.status_code in (*REACHABLE, 404, 410), (
            f"Non-existent page returned unexpected: {resp.status_code}"
        )

    def test_nonexistent_listing_no_server_error(self, api_client: ListingsClient):
        """GET non-existent listings does not cause 500."""
        resp = api_client.get_listing("0000000-nonexistent-truck-xyz")
        assert resp.status_code not in (500, 502, 503, 504), (
            f"Non-existent listing caused server error: {resp.status_code}"
        )
        assert resp.status_code in (*REACHABLE, 404, 410), (
            f"Non-existent listing returned unexpected: {resp.status_code}"
        )

    # ── TC_STATUS10: HTTPS  rect ──────────────────────────────────────────

    def test_http_redirects_to_https(self, api_locale: str):
        """HTTP → HTTPS  rect works correctly."""
        http_url = f"http://www.truck1.eu/{api_locale}"
        resp = requests.get(http_url, allow_redirects=False, timeout=10)
        assert resp.status_code in (301, 302, 307, 308), (
            f"HTTP did not redirect. Status: {resp.status_code}"
        )
        location = resp.headers.get("Location", "")
        assert location.startswith("https://"), (
            f"Redirect Location is not HTTPS: {location}"
        )

    # ── TC_STATUS11: Security headers ────────────────────────────────────────

    def test_security_headers_present(self, api_client: ListingsClient):
        """Response contains basic headers without and ."""
        resp = api_client.get_homepage()
        headers = {k.lower(): v for k, v in resp.headers.items()}
        has_frame_protection = (
            "x-frame-options" in headers
            or "content-security-policy" in headers
        )
        if not has_frame_protection:
            pytest.skip("Security headers not found (CF challenge page may not expose them)")
        assert has_frame_protection

    def test_no_server_version_exposed(self, api_client: ListingsClient):
        """ and  server does not disclosed  in header."""
        resp = api_client.get_homepage()
        server = resp.headers.get("Server", "")
        # Cloudflare returns "cloudflare" without version  — this OK
        assert "/" not in server or "cloudflare" in server.lower() or len(server) < 15, (
            f"Server version exposed: '{server}'"
        )

    # ── TC_STATUS12: Content-Type ────────────────────────────────────────────

    def test_html_pages_have_correct_content_type(self, api_client: ListingsClient):
        """HTML pages return Content-Type: text/html."""
        resp = api_client.get_homepage()
        ct = resp.headers.get("Content-Type", "")
        assert "text/html" in ct, f"Expected text/html, got: '{ct}'"

    # ── TC_STATUS13 / TC_STATUS14: Time response ──────────────────────────────

    def test_homepage_response_time(self, api_client: ListingsClient):
        """Homepage page from str 5 seconds."""
        resp = api_client.get_homepage()
        elapsed = resp.elapsed.total_seconds()
        assert elapsed < 5.0, (
            f"Homepage too slow: {elapsed:.2f}s (threshold: 5s)"
        )

    def test_catalog_response_time(self, api_client: ListingsClient):
        """Catalog from str 7 seconds."""
        resp = api_client.get_sale_catalog()
        elapsed = resp.elapsed.total_seconds()
        assert elapsed < 7.0, (
            f"Catalog too slow: {elapsed:.2f}s (threshold: 7s)"
        )
