"""
base_client.py — base HTTP client for truck1.eu API.

Architecture:
  - Wrapper over requests.Session with retry strategy
  - Single point for managing headers, timeouts, base URL
  - Request/response logging for debugging
  - Locale support via Accept-Language header

Example usage:
    client = Truck1ApiClient(locale="en")
    resp = client.get("/api/v1/listings", params={"make": "Volvo"})
    assert resp.status_code == 200
"""

import logging
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL", "https://www.truck1.eu")

# Cloudflare may return 202 (bot-challenge) instead of 200 for requests without browser.
# Both codes mean "server is alive and responded" — equivalent for status checks.
REACHABLE = (200, 202)

# Locales → Accept-Language header
LOCALE_HEADERS = {
    "en": "en-US,en;q=0.9",
    "de": "de-DE,de;q=0.9",
    "pl": "pl-PL,pl;q=0.9",
    "lt": "lt-LT,lt;q=0.9",
    "lv": "lv-LV,lv;q=0.9",
    "ru": "ru-RU,ru;q=0.9",
    "cs": "cs-CZ,cs;q=0.9",
    "ro": "ro-RO,ro;q=0.9",
}


class Truck1ApiClient:
    """Base HTTP client for truck1.eu."""

    DEFAULT_TIMEOUT = 15  # seconds
    MAX_RETRIES = 3

    def __init__(
        self,
        base_url: str = BASE_URL,
        locale: str = "en",
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.locale = locale
        self.timeout = timeout
        self.session = self._build_session()

    # ── Session ───────────────────────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        session = requests.Session()

        retry = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update(self._default_headers())
        return session

    def _default_headers(self) -> dict:
        return {
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": LOCALE_HEADERS.get(self.locale, "en-US,en;q=0.9"),
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "Cache-Control": "no-cache",
        }

    # ── HTTP methods ──────────────────────────────────────────────────────────

    def get(self, path: str, params: dict = None, **kwargs) -> requests.Response:
        url = self._url(path)
        logger.debug("GET %s params=%s", url, params)
        resp = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
        self._log_response(resp)
        return resp

    def post(self, path: str, json: dict = None, data: dict = None, **kwargs) -> requests.Response:
        url = self._url(path)
        logger.debug("POST %s json=%s", url, json)
        resp = self.session.post(url, json=json, data=data, timeout=self.timeout, **kwargs)
        self._log_response(resp)
        return resp

    def put(self, path: str, json: dict = None, **kwargs) -> requests.Response:
        url = self._url(path)
        resp = self.session.put(url, json=json, timeout=self.timeout, **kwargs)
        self._log_response(resp)
        return resp

    def delete(self, path: str, **kwargs) -> requests.Response:
        url = self._url(path)
        resp = self.session.delete(url, timeout=self.timeout, **kwargs)
        self._log_response(resp)
        return resp

    def head(self, path: str, **kwargs) -> requests.Response:
        url = self._url(path)
        resp = self.session.head(url, timeout=self.timeout, **kwargs)
        return resp

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        """Build full URL from path."""
        if path.startswith("http"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def _log_response(self, resp: requests.Response):
        logger.debug(
            "%s %s → %d (%.2fs)",
            resp.request.method,
            resp.url,
            resp.status_code,
            resp.elapsed.total_seconds(),
        )

    # ── Helper checks ────────────────────────────────────────────────────────

    def is_ok(self, resp: requests.Response) -> bool:
        return resp.status_code == 200

    def is_redirect(self, resp: requests.Response) -> bool:
        return resp.status_code in (301, 302, 303, 307, 308)

    def json_or_none(self, resp: requests.Response) -> dict | list | None:
        try:
            return resp.json()
        except Exception:
            return None

    def locale_path(self, path: str = "") -> str:
        """Return path with locale prefix: /en/trucks-for-sale"""
        return f"/{self.locale}/{path.lstrip('/')}"
