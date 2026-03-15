"""
search_client.py — client for checking search and navigation endpoints.

Covers:
  - Keyword search
  - Autocomplete / suggest
  - Category navigation
  - Sitemap / robots.txt
  - SEO pages (canonical, meta)
"""

import requests

from .base_client import Truck1ApiClient


class SearchClient(Truck1ApiClient):
    # ── Search ────────────────────────────────────────────────────────────────

    def search_listings(
        self,
        query: str,
        category: str = "trucks-for-sale",
        **filters,
    ) -> requests.Response:
        """
        GET /{locale}/{category}?q=query&...

        Main search query with filtering capability.
        """
        params = {"q": query, **filters}
        return self.get(self.locale_path(category), params=params)

    def suggest(self, query: str) -> requests.Response:
        """
        GET /api/suggest?q=query  or  /api/autocomplete?q=query

        Autocomplete endpoint in search bar.
        """
        for path in ["/api/suggest", "/api/autocomplete", "/api/search/suggest"]:
            resp = self.get(path, params={"q": query})
            if resp.status_code != 404:
                return resp
        return resp

    # ── Categories ─────────────────────────────────────────────────────────────

    def get_category_page(self, category_slug: str) -> requests.Response:
        """GET /{locale}/{category_slug}"""
        return self.get(self.locale_path(category_slug))

    def get_curtainsider_category(self) -> requests.Response:
        """GET /{locale}/curtainsider-trucks"""
        return self.get(self.locale_path("curtainsider-trucks"))

    def get_tipper_trucks(self) -> requests.Response:
        return self.get(self.locale_path("tipper-trucks"))

    def get_refrigerator_trucks(self) -> requests.Response:
        return self.get(self.locale_path("refrigerator-trucks"))

    # ── Technical pages ─────────────────────────────────────────────────

    def get_robots_txt(self) -> requests.Response:
        """GET /robots.txt"""
        return self.get("/robots.txt")

    def get_sitemap(self) -> requests.Response:
        """GET /sitemap.xml"""
        return self.get("/sitemap.xml")

    def get_homepage(self, locale: str = None) -> requests.Response:
        """GET /{locale}/"""
        loc = locale or self.locale
        return self.get(f"/{loc}")

    # ── Locales ────────────────────────────────────────────────────────────────

    def get_all_locale_homepages(self, locales: list = None) -> dict:
        """
        Checks availability of home pages for all locales.
        Returns dictionary {locale: status_code}.
        """
        locales = locales or ["en", "de", "pl", "lt", "lv", "ee", "ru", "cs", "sk", "ro", "bg"]
        results = {}
        for loc in locales:
            try:
                resp = self.get(f"/{loc}")
                results[loc] = resp.status_code
            except Exception as e:
                results[loc] = str(e)
        return results

    # ── Static pages ──────────────────────────────────────────────────

    def get_about_page(self) -> requests.Response:
        return self.get(self.locale_path("about"))

    def get_blog_page(self) -> requests.Response:
        return self.get(self.locale_path("blog"))

    def get_leasing_info_page(self) -> requests.Response:
        return self.get(self.locale_path("leasing"))

    def get_place_ad_page(self) -> requests.Response:
        return self.get(self.locale_path("place-ad"))
