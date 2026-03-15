"""
listings_client.py — client for working with truck1.eu listings

Covers:
  - Listings catalog (sale / leasing)
  - Individual listing pages
  - Seller/dealer pages
  - Seller contact form
  - Leasing request form
"""

import requests
from .base_client import Truck1ApiClient


class ListingsClient(Truck1ApiClient):

    # ── Catalog ───────────────────────────────────────────────────────────────

    def get_catalog_page(
        self,
        category: str = "trucks-for-sale",
        page: int = 1,
        **filters,
    ) -> requests.Response:
        """
        GET /{locale}/{category}?page=N&...filters

        Args:
            category: 'trucks-for-sale' | 'trucks-for-lease'
            page: page number
            **filters: make, year_from, year_to, price_from, price_to,
                       mileage_to, country, type etc.
        """
        params = {"page": page, **filters}
        return self.get(self.locale_path(category), params=params)

    def get_sale_catalog(self, page: int = 1, **filters) -> requests.Response:
        """GET /{locale}/trucks-for-sale"""
        return self.get_catalog_page("trucks-for-sale", page=page, **filters)

    def get_lease_catalog(self, page: int = 1, **filters) -> requests.Response:
        """GET /{locale}/trucks-for-lease"""
        return self.get_catalog_page("trucks-for-lease", page=page, **filters)

    # ── Listing page ───────────────────────────────────────────────────

    def get_listing(self, listing_id: str) -> requests.Response:
        """
        GET /{locale}/trucks-for-sale/{listing_id}

        listing_id: slug or numeric listing ID
        """
        return self.get(self.locale_path(f"trucks-for-sale/{listing_id}"))

    def get_leasing_listing(self, listing_id: str) -> requests.Response:
        """GET /{locale}/trucks-for-lease/{listing_id}"""
        return self.get(self.locale_path(f"trucks-for-lease/{listing_id}"))

    # ── Seller page ─────────────────────────────────────────────────────

    def get_dealer_page(self, dealer_slug: str) -> requests.Response:
        """GET /{locale}/dealers/{dealer_slug}"""
        return self.get(self.locale_path(f"dealers/{dealer_slug}"))

    def get_dealers_list(self, page: int = 1, country: str = None) -> requests.Response:
        """GET /{locale}/dealers"""
        params = {"page": page}
        if country:
            params["country"] = country
        return self.get(self.locale_path("dealers"), params=params)

    # ── Contact form (Contact the seller) ────────────────────────────────

    def post_contact_seller(
        self,
        listing_id: str,
        name: str,
        email: str,
        phone: str = "",
        message: str = "Test inquiry",
    ) -> requests.Response:
        """
        POST /api/contact or similar contact form endpoint.

        Real endpoint determined via Network Inspector.
        Current variant — standard truck1.eu API pattern.
        """
        payload = {
            "listing_id": listing_id,
            "name": name,
            "email": email,
            "phone": phone,
            "message": message,
        }
        # Try both possible endpoints
        for path in ["/api/contact", f"/api/listings/{listing_id}/contact"]:
            resp = self.post(path, json=payload)
            if resp.status_code != 404:
                return resp
        return resp

    # ── Leasing request form ─────────────────────────────────────────────────

    def post_leasing_request(
        self,
        listing_id: str,
        name: str,
        email: str,
        phone: str = "",
        company: str = "",
        message: str = "Test leasing inquiry",
    ) -> requests.Response:
        """POST /api/leasing-request or similar."""
        payload = {
            "listing_id": listing_id,
            "name": name,
            "email": email,
            "phone": phone,
            "company": company,
            "message": message,
        }
        for path in ["/api/leasing-request", f"/api/listings/{listing_id}/leasing"]:
            resp = self.post(path, json=payload)
            if resp.status_code != 404:
                return resp
        return resp

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, locale: str = None) -> requests.Response:
        """GET /{locale}?q=query"""
        loc = locale or self.locale
        return self.get(f"/{loc}", params={"q": query})

    # ── Homepage page ──────────────────────────────────────────────────────

    def get_homepage(self) -> requests.Response:
        """GET /{locale}/"""
        return self.get(self.locale_path(""))

    # ── Favorites / Comparison ─────────────────────────────────────────────────

    def get_favourites_page(self) -> requests.Response:
        """GET /{locale}/favourites"""
        return self.get(self.locale_path("favourites"))

    def get_compare_page(self) -> requests.Response:
        """GET /{locale}/compare"""
        return self.get(self.locale_path("compare"))
