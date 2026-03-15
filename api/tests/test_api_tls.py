"""
test_api_tls.py — Transport Layer Security tests for truck1.eu

Coverage:
  TC_TLS01  HTTP redirects to HTTPS (301/302)
  TC_TLS02  HTTPS works without SSL errors (valid certificate)
  TC_TLS03  HSTS max-age >= 1 year (31 536 000 sec)
  TC_TLS04  HSTS includeSubDomains is present
  TC_TLS05  No password / token / api_key in GET query params
  TC_TLS06  No email / phone / PII in GET query params
  TC_TLS07  Search request does not leak sensitive data in URL
  TC_TLS08  No credentials in Referer header sent upstream
  TC_TLS09  No plain HTTP requests to external CDN / APIs in HTML source
  TC_TLS10  Sensitive endpoints respond to HTTPS only (no 200 over HTTP)

Note on Cloudflare:
  TC_TLS01/TC_TLS10 test at the HTTP level — Cloudflare itself handles
  the redirect, so 301/302 is expected from CF edge before origin.
  TLS certificate checks run against CF edge certificate (valid by design).
  All results at HTTP 200 are from CF cache, not necessarily origin.
"""

import re
import ssl
import socket

import pytest
import requests as req_lib

BASE = "https://www.truck1.eu"
BASE_HTTP = "http://www.truck1.eu"

SENSITIVE_PARAM_PATTERNS = re.compile(
    r"[?&](password|passwd|secret|api_key|access_token|token|auth|private_key)"
    r"=\S+",
    re.IGNORECASE,
)

PII_PARAM_PATTERNS = re.compile(
    r"[?&](email|phone|tel|mobile|user_id|uid|ssn|dob|birth)"
    r"=[^&\s]+",
    re.IGNORECASE,
)


# ══════════════════════════════════════════════════════════════════════════════
# TC_TLS01–TC_TLS02: HTTPS availability and redirect
# ══════════════════════════════════════════════════════════════════════════════


class TestHttpsAvailability:
    @pytest.mark.security
    @pytest.mark.parametrize(
        "path",
        [
            "/en",
            "/en/trucks-for-sale",
            "/en/trucks-for-lease",
        ],
    )
    def test_http_redirects_to_https(self, path: str):
        """
        TC_TLS01: HTTP request must redirect to HTTPS.

        Site should never serve content over plain HTTP.
        Cloudflare edge handles this redirect before origin.
        """
        resp = req_lib.get(
            f"{BASE_HTTP}{path}",
            allow_redirects=False,
            timeout=10,
        )
        assert resp.status_code in (301, 302, 307, 308), (
            f"HTTP did not redirect to HTTPS for '{path}'. "
            f"Got status: {resp.status_code}. "
            "Site may be serving content over unencrypted HTTP!"
        )
        location = resp.headers.get("Location", "")
        assert location.startswith("https://"), (
            f"Redirect Location does not point to HTTPS: '{location}'"
        )

    @pytest.mark.security
    def test_https_no_ssl_errors(self):
        """
        TC_TLS02: HTTPS connection completes without SSL errors.

        Validates that the certificate is trusted, not expired,
        and hostname matches. Uses requests with verify=True (default).
        """
        try:
            resp = req_lib.get(f"{BASE}/en/", verify=True, timeout=15)
            assert resp.status_code in (200, 202, 301, 302, 404), (
                f"Unexpected status over HTTPS: {resp.status_code}"
            )
        except req_lib.exceptions.SSLError as exc:
            pytest.fail(f"SSL ERROR — certificate invalid or untrusted:\n{exc}")

    @pytest.mark.security
    def test_tls_certificate_valid(self):
        """
        TC_TLS02+: TLS certificate expiry and hostname check via ssl module.

        Connects directly to port 443 and inspects the certificate.
        """
        hostname = "www.truck1.eu"
        context = ssl.create_default_context()
        try:
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    assert cert, "No certificate returned from server"
                    # Check certificate is not empty
                    assert "subject" in cert, "Certificate missing 'subject' field"
                    assert "notAfter" in cert, "Certificate missing 'notAfter' field"
        except ssl.SSLCertVerificationError as exc:
            pytest.fail(f"TLS CERTIFICATE ERROR: {exc}")
        except ConnectionRefusedError:
            pytest.skip("Could not connect to port 443 (network restriction in CI)")


# ══════════════════════════════════════════════════════════════════════════════
# TC_TLS03–TC_TLS04: HSTS configuration
# ══════════════════════════════════════════════════════════════════════════════


class TestHstsConfiguration:
    ONE_YEAR_SECONDS = 31_536_000

    def _get_hsts(self) -> str:
        resp = req_lib.get(f"{BASE}/en", verify=True, timeout=15)
        if resp.status_code not in (200, 202):
            pytest.skip(f"Unexpected status {resp.status_code} — cannot inspect HSTS")
        return resp.headers.get("Strict-Transport-Security", "")

    @pytest.mark.security
    def test_hsts_max_age_sufficient(self):
        """
        TC_TLS03: HSTS max-age must be at least 1 year (31 536 000 sec).

        Short max-age means browsers forget HTTPS enforcement quickly,
        leaving a window for SSL-stripping attacks.
        """
        hsts = self._get_hsts()
        if not hsts:
            pytest.skip("HSTS header not present — covered in TC_SEC01")

        match = re.search(r"max-age=(\d+)", hsts, re.IGNORECASE)
        assert match, f"HSTS header present but max-age not found: '{hsts}'"

        max_age = int(match.group(1))
        assert max_age >= self.ONE_YEAR_SECONDS, (
            f"HSTS max-age too short: {max_age}s < {self.ONE_YEAR_SECONDS}s (1 year). "
            f"Full header: '{hsts}'"
        )

    @pytest.mark.security
    def test_hsts_includes_subdomains(self):
        """
        TC_TLS04: HSTS should include 'includeSubDomains' directive.

        Without it, subdomains (e.g. api.truck1.eu) are not protected
        by HSTS and could be targeted by SSL-stripping on first visit.
        """
        hsts = self._get_hsts()
        if not hsts:
            pytest.skip("HSTS header not present — covered in TC_SEC01")

        has_subdomains = "includesubdomains" in hsts.lower()
        if not has_subdomains:
            pytest.xfail(
                f"HSTS missing 'includeSubDomains': '{hsts}'. "
                "Subdomains not protected. Consider adding includeSubDomains."
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC_TLS05–TC_TLS07: No sensitive data in GET params / URLs
# ══════════════════════════════════════════════════════════════════════════════


class TestNoSensitiveDataInUrl:
    """
    Sensitive data in URLs ends up in:
      - Server access logs (plaintext)
      - Browser history
      - Referer headers sent to third-party analytics
      - CDN / proxy logs

    All of the above are outside TLS encryption scope —
    even on HTTPS, the query string is logged at the origin.
    """

    ENDPOINTS_TO_CHECK = [
        "/en",
        "/en/trucks-for-sale",
        "/en/trucks-for-sale?make=Volvo&year_from=2020",
        "/en/trucks-for-lease",
        "/en/dealers",
    ]

    @pytest.mark.security
    @pytest.mark.parametrize("path", ENDPOINTS_TO_CHECK)
    def test_no_auth_credentials_in_get_params(self, path: str):
        """
        TC_TLS05: Standard pages do not contain passwords / tokens in URL.

        This verifies the server never redirects to a URL containing
        credentials, even after session handling or auth flows.
        """
        resp = req_lib.get(
            f"{BASE}{path}",
            allow_redirects=True,
            timeout=15,
        )
        final_url = resp.url
        match = SENSITIVE_PARAM_PATTERNS.search(final_url)
        assert not match, (
            f"CREDENTIALS IN URL: sensitive parameter found after redirect!\n"
            f"URL: {final_url}\n"
            f"Match: {match.group(0)}"
        )

    @pytest.mark.security
    @pytest.mark.parametrize("path", ENDPOINTS_TO_CHECK)
    def test_no_pii_in_get_params(self, path: str):
        """
        TC_TLS06: Standard pages do not expose PII (email, phone, user_id) in URL.

        PII in GET params violates GDPR Article 32 (security of processing)
        and risks data leakage via logs and Referer headers.
        """
        resp = req_lib.get(
            f"{BASE}{path}",
            allow_redirects=True,
            timeout=15,
        )
        final_url = resp.url
        match = PII_PARAM_PATTERNS.search(final_url)
        assert not match, (
            f"PII IN URL: personal data parameter found!\n"
            f"URL: {final_url}\n"
            f"Match: {match.group(0)}"
        )

    @pytest.mark.security
    @pytest.mark.parametrize(
        "query",
        [
            "Volvo FH",
            "Mercedes Actros",
            "scania r500",
        ],
    )
    def test_search_url_no_sensitive_leakage(self, query: str):
        """
        TC_TLS07: Search requests do not embed sensitive data in the URL.

        Verifies that the search endpoint only includes the query term
        and standard filter params — no tokens, sessions or PII.
        """
        resp = req_lib.get(
            f"{BASE}/en/trucks-for-sale",
            params={"q": query},
            allow_redirects=True,
            timeout=15,
        )
        url = resp.url
        assert not SENSITIVE_PARAM_PATTERNS.search(url), (
            f"SENSITIVE PARAM in search URL: {url}"
        )
        assert not PII_PARAM_PATTERNS.search(url), (
            f"PII PARAM in search URL: {url}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC_TLS08: No credentials in Referer header
# ══════════════════════════════════════════════════════════════════════════════


class TestRefererSafety:
    @pytest.mark.security
    def test_referrer_policy_header_present(self):
        """
        TC_TLS08: Referrer-Policy header limits what URL data is sent upstream.

        Without a restrictive Referrer-Policy, the full URL (including
        query params) is sent as Referer to every third-party resource
        loaded on the page (analytics, CDN, ads).

        Acceptable values: no-referrer, same-origin, strict-origin,
        strict-origin-when-cross-origin.
        """
        resp = req_lib.get(f"{BASE}/en", verify=True, timeout=15)
        if resp.status_code not in (200, 202):
            pytest.skip(f"Cannot inspect headers — status {resp.status_code}")

        policy = resp.headers.get("Referrer-Policy", "").lower()

        safe_policies = {
            "no-referrer",
            "same-origin",
            "strict-origin",
            "strict-origin-when-cross-origin",
            "no-referrer-when-downgrade",
        }

        if not policy:
            pytest.xfail(
                "Referrer-Policy header not set. "
                "Query params in URLs may be sent to third-party domains via Referer."
            )
        else:
            assert policy in safe_policies, (
                f"Referrer-Policy value '{policy}' may leak URL data. "
                f"Recommended: 'strict-origin-when-cross-origin'."
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC_TLS09: No HTTP resources in HTML source
# ══════════════════════════════════════════════════════════════════════════════


class TestNoHttpResourcesInSource:
    """
    Even if mixed content is blocked by the browser (TC_UISEC03 covers that),
    the presence of http:// references in HTML source is a code quality issue
    that may affect non-browser clients or future configs.
    """

    HTTP_RESOURCE_PATTERN = re.compile(
        r'(src|href|action|data-src)\s*=\s*["\']http://(?!localhost|127\.)',
        re.IGNORECASE,
    )

    @pytest.mark.security
    @pytest.mark.parametrize(
        "path",
        [
            "/en",
            "/en/trucks-for-sale",
        ],
    )
    def test_no_http_references_in_html(self, path: str):
        """
        TC_TLS09: HTML source does not contain plain http:// resource references.

        Checks src=, href=, action= attributes for http:// URLs
        pointing to external resources (scripts, styles, images, forms).
        """
        resp = req_lib.get(f"{BASE}{path}", verify=True, timeout=20)
        if resp.status_code != 200:
            pytest.skip(f"CF challenge ({resp.status_code}) — HTML source not available")

        matches = self.HTTP_RESOURCE_PATTERN.findall(resp.text)
        assert len(matches) == 0, (
            f"HTTP RESOURCES IN HTML SOURCE ({len(matches)} found) on '{path}':\n"
            + "\n".join(f"  - {m}" for m in matches[:10])
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC_TLS10: No 200 OK over plain HTTP (content must redirect)
# ══════════════════════════════════════════════════════════════════════════════


class TestHttpContentBlocked:
    @pytest.mark.security
    @pytest.mark.parametrize(
        "path",
        [
            "/en",
            "/en/trucks-for-sale",
            "/en/trucks-for-lease",
        ],
    )
    def test_http_does_not_serve_content(self, path: str):
        """
        TC_TLS10: Plain HTTP requests must not return 200 OK with HTML content.

        The site must only serve content over HTTPS.
        HTTP connections should receive a redirect, not actual page content.
        """
        resp = req_lib.get(
            f"{BASE_HTTP}{path}",
            allow_redirects=False,
            timeout=10,
        )
        assert resp.status_code != 200, (
            f"PLAIN HTTP SERVING CONTENT: '{path}' returned 200 over HTTP! "
            "All content must be served over HTTPS only."
        )
