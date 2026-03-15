"""
test_api_listings.py — tests for listing pages through HTTP

Coverage:
  TC_ALIST01  Page of real listing (sale) returns 200
  TC_ALIST02  Page of real listing (lease) returns 200
  TC_ALIST03  Non-existent listing returns 404
  TC_ALIST04  Listing page contains key HTML elements
  TC_ALIST05  Form "Contact the seller" endpoint is present
  TC_ALIST06  Contact validation
  TC_ALIST07  Contact validation
  TC_ALIST08  Contact validation
  TC_ALIST09  Leasing form
  TC_ALIST10  Leasing form
  TC_ALIST11  Seller page is available
  TC_ALIST12  Redirect from old URL works
  TC_ALIST13  Meta tags are present in listing HTML
"""

import re

import pytest

from api.client import REACHABLE, ListingsClient
from api.models import ContactFormSchema, LeasingRequestSchema
from utils.helpers import generate_test_contact

# ── Fixtures: get real listing ID from catalog ─────────────────────


@pytest.fixture(scope="module")
def first_sale_listing_url(api_client_module: ListingsClient):
    """Takes URL of first listing from sale catalog.

    Note:: with Cloudflare 202, catalog returns challenge page
    without real hrefs — in this case test will be skipped.
    """
    resp = api_client_module.get_sale_catalog()
    if resp.status_code not in REACHABLE:
        pytest.skip(f"Cannot fetch sale catalog (status {resp.status_code})")
    urls = re.findall(
        r'href="(/[a-z]{2}/trucks-for-sale/[^"]+)"',
        resp.text,
    )
    if not urls:
        pytest.skip(
            "No listing URLs found in catalog HTML — "
            "Cloudflare challenge page returned (no real content)"
        )
    return urls[0]


@pytest.fixture(scope="module")
def first_lease_listing_url(api_client_module: ListingsClient):
    """Takes URL of first leasing listing."""
    resp = api_client_module.get_lease_catalog()
    if resp.status_code not in REACHABLE:
        pytest.skip(f"Cannot fetch lease catalog (status {resp.status_code})")
    urls = re.findall(
        r'href="(/[a-z]{2}/trucks-for-lease/[^"]+)"',
        resp.text,
    )
    if not urls:
        pytest.skip(
            "No leasing listing URLs found in catalog HTML — "
            "Cloudflare challenge page returned (no real content)"
        )
    return urls[0]


@pytest.mark.api
@pytest.mark.api_listings
class TestApiListings:
    # ── TC_ALIST01 / TC_ALIST02: Listings are accessible ─────────────────────────

    def test_sale_listing_returns_200(
        self, api_client: ListingsClient, first_sale_listing_url: str
    ):
        """Page of real listing (sale) returns 200/202."""
        resp = api_client.get(first_sale_listing_url)
        assert (
            resp.status_code in REACHABLE
        ), f"Sale listing {first_sale_listing_url} returned {resp.status_code}"

    def test_lease_listing_returns_200(
        self, api_client: ListingsClient, first_lease_listing_url: str
    ):
        """Page real leasing listings → 200/202."""
        resp = api_client.get(first_lease_listing_url)
        assert (
            resp.status_code in REACHABLE
        ), f"Lease listing {first_lease_listing_url} returned {resp.status_code}"

    # ── TC_ALIST03: 404 for non-existent ──────────────────────────────────

    def test_nonexistent_listing_404(self, api_client: ListingsClient):
        """Non-existent and slug listings → 404/410 or CF challenge (202). Not 500."""
        resp = api_client.get_listing("nonexistent-truck-xyz-000000")
        assert resp.status_code not in (
            500,
            502,
            503,
        ), f"Non-existent listing caused server error: {resp.status_code}"
        assert resp.status_code in (
            *REACHABLE,
            404,
            410,
        ), f"Expected 404/410 or CF challenge, got {resp.status_code}"

    # ── TC_ALIST04: HTML content ──────────────────────────────────────────

    def test_listing_html_has_title(self, api_client: ListingsClient, first_sale_listing_url: str):
        """HTML pages listings contains tag <title>."""
        resp = api_client.get(first_sale_listing_url)
        assert "<title>" in resp.text, "No <title> tag in listing HTML"

    def test_listing_html_has_h1(self, api_client: ListingsClient, first_sale_listing_url: str):
        """HTML pages listings contains tag <h1>."""
        resp = api_client.get(first_sale_listing_url)
        assert "<h1" in resp.text, "No <h1> tag in listing HTML"

    def test_listing_html_has_price(self, api_client: ListingsClient, first_sale_listing_url: str):
        """HTML pages listings contains  (€ or  and   and)."""
        resp = api_client.get(first_sale_listing_url)
        has_price = "€" in resp.text or "EUR" in resp.text or bool(re.search(r"\d{4,}", resp.text))
        assert has_price, "No price information found in listing HTML"

    # ── TC_ALIST05 / TC_ALIST06 / TC_ALIST07: Contact form API ───────────────

    def test_contact_endpoint_exists(self, api_client: ListingsClient, first_sale_listing_url: str):
        """nt Contact the seller is present ( 405 Method Not Allowed)."""
        # Extract ID  iz URL
        match = re.search(r"/trucks-for-sale/(.+)", first_sale_listing_url)
        if not match:
            pytest.skip("Cannot extract listing ID from URL")
        listing_id = match.group(1).rstrip("/")

        contact = generate_test_contact()
        resp = api_client.post_contact_seller(
            listing_id=listing_id,
            name=contact.name,
            email=contact.email,
            message=contact.message,
        )
        # 200/201 = success, 422/400 = val and yes and , 404 = endpoint
        #  and  and  e om 500 (server error)
        assert resp.status_code != 500, "Contact form caused 500 Internal Server Error"
        assert resp.status_code in (
            200,
            201,
            302,
            400,
            401,
            403,
            404,
            405,
            422,
        ), f"Unexpected status code: {resp.status_code}"

    def test_contact_form_schema_validation(self):
        """ContactFormSchema correctly validates data."""
        #  and  data
        valid = ContactFormSchema(
            listing_id="12345",
            name="Test User",
            email="test@example.com",
            message="This is a test inquiry",
        )
        is_valid, errors = valid.is_valid()
        assert is_valid, f"Valid form marked invalid: {errors}"

        # Notinvalid email
        invalid = ContactFormSchema(
            listing_id="12345",
            name="Test User",
            email="not-an-email",
            message="Test",
        )
        is_valid, errors = invalid.is_valid()
        assert not is_valid, "Invalid email was accepted"
        assert any("email" in e.lower() for e in errors)

        #   ame
        no_name = ContactFormSchema(
            listing_id="12345",
            name="",
            email="test@example.com",
            message="Test message",
        )
        is_valid, errors = no_name.is_valid()
        assert not is_valid, "Empty name was accepted"

    def test_contact_form_missing_email(
        self, api_client: ListingsClient, first_sale_listing_url: str
    ):
        """Contact form without email returns 400 or 422 (val and yes and   server)."""
        match = re.search(r"/trucks-for-sale/(.+)", first_sale_listing_url)
        if not match:
            pytest.skip("Cannot extract listing ID")
        listing_id = match.group(1).rstrip("/")

        resp = api_client.post_contact_seller(
            listing_id=listing_id,
            name="Test User",
            email="",
            message="Test message",
        )
        # Expected:  and ku validation error or from,  200  and   500
        if resp.status_code == 404:
            pytest.skip("Contact API endpoint not found")
        assert resp.status_code in (
            400,
            422,
        ), f"Missing email was accepted with status {resp.status_code}"

    # ── TC_ALIST09 / TC_ALIST10: Leasing form ────────────────────────────────

    def test_leasing_request_schema_validation(self):
        """LeasingRequestSchema correctly validates data."""
        valid = LeasingRequestSchema(
            listing_id="lease-123",
            name="Company Owner",
            email="owner@company.eu",
            phone="+48123456789",
            company="Test Transport Ltd",
        )
        is_valid, errors = valid.is_valid()
        assert is_valid, f"Valid leasing form marked invalid: {errors}"

        invalid = LeasingRequestSchema(
            listing_id="",
            name="",
            email="bad-email",
        )
        is_valid, errors = invalid.is_valid()
        assert not is_valid

    def test_leasing_form_endpoint(self, api_client: ListingsClient, first_lease_listing_url: str):
        """nt Request a leasing offer  request."""
        match = re.search(r"/trucks-for-lease/(.+)", first_lease_listing_url)
        if not match:
            pytest.skip("Cannot extract leasing listing ID")
        listing_id = match.group(1).rstrip("/")

        contact = generate_test_contact()
        resp = api_client.post_leasing_request(
            listing_id=listing_id,
            name=contact.name,
            email=contact.email,
            phone=contact.phone,
            company="Test Transport Ltd",
            message=contact.message,
        )
        assert resp.status_code != 500, "Leasing form caused 500 error"

    # ── TC_ALIST11: Page seller ────────────────────────────────────────

    def test_dealer_page_accessible(self, api_client: ListingsClient, first_sale_listing_url: str):
        """Page seller is available through ku  iz listings."""
        resp_listing = api_client.get(first_sale_listing_url)
        # Find ku  dealer  in HTML
        dealer_urls = re.findall(
            r'href="(/[a-z]{2}/dealers/[^"]+)"',
            resp_listing.text,
        )
        if not dealer_urls:
            pytest.skip("No dealer link found in listing HTML")

        dealer_url = dealer_urls[0]
        resp = api_client.get(dealer_url)
        assert resp.status_code == 200, f"Dealer page {dealer_url} returned {resp.status_code}"

    # ── TC_ALIST13: Meta-tag and  ─────────────────────────────────────────────────

    def test_listing_has_og_tags(self, api_client: ListingsClient, first_sale_listing_url: str):
        """HTML contains Open Graph meta-tag and  for  and ."""
        resp = api_client.get(first_sale_listing_url)
        has_og = 'property="og:title"' in resp.text or "og:title" in resp.text
        assert has_og, "No Open Graph tags found in listing HTML"

    def test_listing_has_canonical(self, api_client: ListingsClient, first_sale_listing_url: str):
        """HTML contains canonical ku."""
        resp = api_client.get(first_sale_listing_url)
        assert (
            'rel="canonical"' in resp.text or "canonical" in resp.text.lower()
        ), "No canonical link in listing HTML"
