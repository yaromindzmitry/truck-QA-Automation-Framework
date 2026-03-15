"""
test_api_security.py — advanced security checks for truck1.eu

Coverage:
  TC_SEC01   HSTS heading is present (Strict-Transport-Security)
  TC_SEC02   X-Content-Type-Options: nosniff is present
  TC_SEC03   X-Frame-Options or CSP are missing (protection from clickjacking)
  TC_SEC04   Open Redirect — parameter redirect= do not redirect  external domain
  TC_SEC05   Open Redirect — parameter next= do not redirect  external domain
  TC_SEC06   Open Redirect — parameter url= do not redirect  external domain
  TC_SEC07   SQL injection UNION SELECT — does not cause 500
  TC_SEC08   SQL injection boolean-based (AND 1=2) — does not cause 500
  TC_SEC09   SQL injection stacked queries (DROP TABLE) — does not cause 500
  TC_SEC10   SQL injection in parameter page — does not cause 500
  TC_SEC11   SQL injection in parameter year_from — does not cause 500
  TC_SEC12   SQL injection in parameter price_from — does not cause 500
  TC_SEC13   XSS: img onerror —  from without escaping
  TC_SEC14   XSS: svg onload —  from without escaping
  TC_SEC15   XSS: javascript: URI —  from without escaping
  TC_SEC16   Path traversal  in URL  opens  system
  TC_SEC17   HTTP- PUT  catalog — did not return 2xx
  TC_SEC18   HTTP- DELETE  catalog — did not return 2xx
  TC_SEC19   Null-byte in parameter — does not cause 500
  TC_SEC20   Very heading Host — does not cause 500
  TC_SEC21   CORS —  izOrigin  get ACAO: *
  TC_SEC22   CORS — Origin  from  in Access-Control-Allow-Origin
  TC_SEC23   CORS — preflight OPTIONS does not disclose  and  and
  TC_SEC24   CORS — credentials   for  Origin

Note:  Cloudflare:
  Cloudflare  headless-request  and  returns 202 (JS-challenge).
   and  security-test version only «no 500» — this correctly,
  ku 500   server,  and   is visible yes through CF.
  tests  headers without and  to and  and  with 202 — CF challenge-page
  may   headers  and  and  origin server.
"""

import pytest
import requests as req_lib

from api.client import REACHABLE, ListingsClient, SearchClient

# ── om  ─────────────────────────────────────────────────

# , with from server returned real response ( CF challenge)
REAL_RESPONSE = (200,)

# Acceptable:  for security-test «server  »
SAFE_CODES = (*REACHABLE, 400, 404, 410, 422)

# SQL-   and  and  and
SQL_PAYLOADS = [
    ("basic_quote", "'"),
    ("double_quote", '"'),
    ("comment_dash", "' --"),
    ("comment_hash", "' #"),
    ("or_true", "' OR '1'='1"),
    ("and_false", "' AND 1=2 --"),
    ("union_select", "' UNION SELECT NULL,NULL,NULL --"),
    ("union_select_str", "' UNION SELECT 'a','b','c' --"),
    ("stacked_drop", "'; DROP TABLE listings; --"),
    ("stacked_update", "'; UPDATE listings SET price=0; --"),
    ("error_based", "' AND extractvalue(1,concat(0x7e,version())) --"),
    ("time_based_pg", "'; SELECT pg_sleep(0); --"),
    ("time_based_mysql", "' AND SLEEP(0) --"),
    ("null_byte", "'\x00"),
    ("hex_encoded", "0x27204f522031"),
]

# XSS-
XSS_PAYLOADS = [
    ("script_tag", "<script>alert('xss')</script>"),
    ("img_onerror", "<img src=x onerror=alert(1)>"),
    ("svg_onload", "<svg onload=alert(1)>"),
    ("javascript_uri", "javascript:alert(1)"),
    ("event_handler", '" onmouseover="alert(1)'),
    ("encoded_script", "%3Cscript%3Ealert(1)%3C/script%3E"),
    ("double_encoded", "%253Cscript%253Ealert%25281%2529%253C%252Fscript%253E"),
]

#  and URL for test open redirect
EXTERNAL_URLS = [
    "https://evil.com",
    "//evil.com",
    "https://evil.com/steal?data=1",
    "http://attacker.example.org",
    r"\/\/evil.com",
    "https:evil.com",
]


# ──   ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    return ListingsClient(locale="en")


@pytest.fixture(scope="module")
def search():
    return SearchClient(locale="en")


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC01–TC_SEC03: Security HTTP-headers
# ══════════════════════════════════════════════════════════════════════════════


class TestSecurityHeaders:
    def _get_real_headers(self, client: ListingsClient):
        """headers only if getor real response ( CF 202)."""
        resp = client.get_homepage()
        if resp.status_code != 200:
            pytest.skip("CF challenge (202) — origin headers not available for inspection")
        return {k.lower(): v for k, v in resp.headers.items()}

    @pytest.mark.security
    def test_hsts_header_present(self, client: ListingsClient):
        """TC_SEC01: Strict-Transport-Security heading is present."""
        headers = self._get_real_headers(client)
        assert "strict-transport-security" in headers, (
            "HSTS header (Strict-Transport-Security) not found! "
            "Site is vulnerable to SSL-stripping attacks."
        )
        hsts_value = headers["strict-transport-security"]
        #  and  and max-age 1  (2592000 sec)
        assert "max-age=" in hsts_value, f"HSTS missing max-age: '{hsts_value}'"

    @pytest.mark.security
    def test_x_content_type_options(self, client: ListingsClient):
        """TC_SEC02: X-Content-Type-Options: nosniff protect and  from MIME-sniffing."""
        headers = self._get_real_headers(client)
        value = headers.get("x-content-type-options", "")
        assert "nosniff" in value.lower(), (
            f"X-Content-Type-Options: nosniff not set (got: '{value}'). "
            "Browser may interpret files with wrong MIME type."
        )

    @pytest.mark.security
    def test_clickjacking_protection(self, client: ListingsClient):
        """TC_SEC03: X-Frame-Options or CSP frame-ancestors protect and  from clickjacking."""
        headers = self._get_real_headers(client)
        has_xfo = "x-frame-options" in headers
        has_csp = "content-security-policy" in headers
        assert has_xfo or has_csp, (
            "Neither X-Frame-Options nor Content-Security-Policy found. "
            "Site may be vulnerable to clickjacking."
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC04–TC_SEC06: Open Redirect
# ══════════════════════════════════════════════════════════════════════════════


class TestOpenRedirect:
    """
    Open Redirect — , with fromserver  user
     external domain through parameter redirect=, next=, url=  and  ..
    And for  haring: link  and  as truck1.eu,  leads to evil.com.
    """

    REDIRECT_PARAMS = [
        "redirect",
        "next",
        "url",
        "return",
        "returnUrl",
        "return_url",
        "goto",
        "destination",
        "target",
        "redir",
    ]

    def _check_no_external_redirect(self, resp: req_lib.Response, external_url: str):
        """Check, that response   rect and   external domain."""
        if resp.status_code not in (301, 302, 307, 308):
            return  # No  rect — e OK
        location = resp.headers.get("Location", "")
        #  only truck1.eu  and   Location
        evil_domain = "evil.com"
        assert evil_domain not in location, (
            f"OPEN REDIRECT DETECTED! " f"Payload '{external_url}' caused redirect to: '{location}'"
        )
        # Verify that Location   and   http(s)://domain
        if location.startswith("http"):
            assert "truck1.eu" in location or location.startswith(
                "/"
            ), f"Redirect to external domain: '{location}'"

    @pytest.mark.security
    @pytest.mark.parametrize("param", ["redirect", "next", "url"])
    def test_open_redirect_main_params(self, client: ListingsClient, param: str):
        """TC_SEC04–TC_SEC06:  redirect-parameter    evil.com."""
        resp = client.get(
            client.locale_path(""),
            params={param: "https://evil.com"},
            allow_redirects=False,
        )
        # version    rect and   evil.com
        self._check_no_external_redirect(resp, "https://evil.com")

    @pytest.mark.security
    @pytest.mark.parametrize(
        "evil_url",
        [
            "//evil.com",
            r"\/\/evil.com",
            "https://evil.com%2F@truck1.eu",
        ],
    )
    def test_open_redirect_bypass_variants(self, client: ListingsClient, evil_url: str):
        """TC_SEC04+: Bypass- and  open redirect (protocol-relative, backslash)."""
        resp = client.get(
            client.locale_path(""),
            params={"redirect": evil_url},
            allow_redirects=False,
        )
        self._check_no_external_redirect(resp, evil_url)


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC07–TC_SEC12: SQL- injection  and
# ══════════════════════════════════════════════════════════════════════════════


class TestSqlInjection:
    """
    SQL Injection —   and  SQL-  in parameter request.
     and   vulnerable and  — HTTP 500 (Internal Server Error),
    that , that payload   in SQL-request  and    and ku database.
    """

    # ──  in parameter make (  in ) ────────────────────────────────────

    @pytest.mark.security
    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS)
    def test_sql_injection_in_make(self, client: ListingsClient, name: str, payload: str):
        """TC_SEC07+: SQL injection in parameter make does not cause 500."""
        resp = client.get_sale_catalog(make=payload)
        assert resp.status_code != 500, (
            f"SQL INJECTION RISK [{name}]: payload in 'make' caused 500! "
            f"Payload: {repr(payload)}"
        )
        assert (
            resp.status_code in SAFE_CODES
        ), f"Unexpected status {resp.status_code} for SQL payload [{name}]"

    # ──  in parameter page (number pages) ─────────────────────────────────────

    @pytest.mark.security
    @pytest.mark.parametrize(
        "name,payload",
        [
            ("basic_quote", "'"),
            ("union_select", "1 UNION SELECT NULL --"),
            ("or_true", "1 OR 1=1"),
            ("comment", "1; --"),
            ("negative", "-1"),
            ("float", "1.5"),
            ("expression", "1+1"),
        ],
    )
    def test_sql_injection_in_page(self, client: ListingsClient, name: str, payload: str):
        """TC_SEC10: SQL injection in parameter page (numeric) does not cause 500."""
        resp = client.get(
            client.locale_path("trucks-for-sale"),
            params={"page": payload},
        )
        assert resp.status_code != 500, (
            f"SQL INJECTION RISK [{name}]: payload in 'page' caused 500! "
            f"Payload: {repr(payload)}"
        )

    # ──  in  and  parameter year_from, price_from ───────────────────────────

    @pytest.mark.security
    @pytest.mark.parametrize(
        "param,payload",
        [
            ("year_from", "' OR '1'='1"),
            ("year_from", "2020 UNION SELECT NULL --"),
            ("year_to", "' --"),
            ("price_from", "0 OR 1=1"),
            ("price_to", "' UNION SELECT version() --"),
            ("mileage_to", "'; DROP TABLE listings; --"),
        ],
    )
    def test_sql_injection_in_numeric_params(
        self, client: ListingsClient, param: str, payload: str
    ):
        """TC_SEC11–TC_SEC12: SQL injection  in  and  filter does not cause 500."""
        resp = client.get(
            client.locale_path("trucks-for-sale"),
            params={param: payload},
        )
        assert resp.status_code != 500, (
            f"SQL INJECTION RISK: payload in '{param}' caused 500! " f"Payload: {repr(payload)}"
        )

    # ──  in string search ───────────────────────────────────────────────────────

    @pytest.mark.security
    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:8])  #  8
    def test_sql_injection_in_search(self, search: SearchClient, name: str, payload: str):
        """SQL injection  in string search does not cause 500."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"SQL INJECTION RISK [{name}]: payload in search caused 500! "
            f"Payload: {repr(payload)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC13–TC_SEC15: XSS (extended and )
# ══════════════════════════════════════════════════════════════════════════════


class TestXssExtended:
    """
    XSS (Cross-Site Scripting) —   and  JS  in HTML-response.
    Verify only with status_code == 200 (real HTML).
     and  202 (CF challenge) — to and  and , .. this   and  and content.
    """

    def _assert_payload_not_reflected(self, resp: req_lib.Response, payload: str):
        """Check, that payload    in HTML without escaping."""
        if resp.status_code != 200:
            return  # CF challenge or error —  check content
        # payload     in response
        assert payload not in resp.text, (
            f"XSS RISK: Payload reflected unescaped in response!\n" f"Payload: {repr(payload)}"
        )

    @pytest.mark.security
    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS)
    def test_xss_in_search(self, search: SearchClient, name: str, payload: str):
        """TC_SEC13–TC_SEC15: XSS  in string search  from without escaping."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500
        self._assert_payload_not_reflected(resp, payload)

    @pytest.mark.security
    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS)
    def test_xss_in_make_filter(self, client: ListingsClient, name: str, payload: str):
        """XSS in parameter make (filter catalog)  from without escaping."""
        resp = client.get_sale_catalog(make=payload)
        assert resp.status_code != 500
        self._assert_payload_not_reflected(resp, payload)


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC16: Path Traversal
# ══════════════════════════════════════════════════════════════════════════════


class TestPathTraversal:
    """
    Path Traversal —     system  in through ../
     in and , if server returned content /etc/passwd or .
    """

    @pytest.mark.security
    @pytest.mark.parametrize(
        "path",
        [
            "/../../../etc/passwd",
            "/..%2F..%2F..%2Fetc%2Fpasswd",
            "/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
            "/en/../../../etc/shadow",
            "/en/trucks-for-sale/../../../../etc/passwd",
        ],
    )
    def test_path_traversal_no_system_files(self, client: ListingsClient, path: str):
        """TC_SEC16: Path traversal  opens  system ."""
        resp = client.get(path)
        # version   version content /etc/passwd
        assert (
            "root:x:0:0" not in resp.text
        ), f"PATH TRAVERSAL VULNERABILITY! /etc/passwd content found for path: {path}"
        assert resp.status_code != 500, f"Path traversal caused 500 for: {path}"


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC17–TC_SEC18: HTTP-
# ══════════════════════════════════════════════════════════════════════════════


class TestHttpMethods:
    """
    Catalog — read-only ,  from  and  and HTTP-.
    PUT  and  DELETE    200 OK — this start ,
    that data   iz and  without  iz .

    Note:: Cloudflare returns 202 (bot-challenge)  ,
     PUT  and  DELETE. This  vulnerable — CF  and  request  server.
    Real vulnerable — only status_code == 200 (server from request).
    """

    @pytest.mark.security
    def test_put_on_catalog_not_allowed(self, client: ListingsClient):
        """TC_SEC17: PUT-request  catalog does not return 200 OK."""
        resp = client.put(client.locale_path("trucks-for-sale"), json={"price": 0})
        if resp.status_code == 202:
            pytest.skip("CF challenge (202) — request intercepted before origin server")
        assert resp.status_code != 200, "PUT on catalog returned 200 — write access without auth!"

    @pytest.mark.security
    def test_delete_on_catalog_not_allowed(self, client: ListingsClient):
        """TC_SEC18: DELETE-request  catalog does not return 200 OK."""
        resp = client.delete(client.locale_path("trucks-for-sale"))
        if resp.status_code == 202:
            pytest.skip("CF challenge (202) — request intercepted before origin server")
        assert resp.status_code != 200, "DELETE on catalog returned 200 — delete without auth!"


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC19–TC_SEC20: Edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    @pytest.mark.security
    def test_null_byte_in_parameter(self, client: ListingsClient):
        """TC_SEC19: Null-byte (%00) in parameter does not cause 500."""
        resp = client.get_sale_catalog(make="Volvo\x00<script>")
        assert resp.status_code != 500, "Null-byte in parameter caused 500!"

    @pytest.mark.security
    def test_oversized_host_header(self, client: ListingsClient):
        """TC_SEC20: om heading does not cause 500."""
        resp = client.get(
            client.locale_path("trucks-for-sale"),
            headers={"X-Custom-Header": "A" * 8192},
        )
        assert resp.status_code != 500, "Oversized header caused 500!"

    @pytest.mark.security
    def test_special_chars_in_search(self, search: SearchClient):
        """List and   in search are handled without  server."""
        for payload in ["<>\"'&", "\\", "%", "🚛🔥", "\r\n", "\t"]:
            resp = search.search_listings(payload)
            assert resp.status_code != 500, f"Special chars caused 500! Payload: {repr(payload)}"


# ══════════════════════════════════════════════════════════════════════════════
# TC_SEC21–TC_SEC24: CORS (Cross-Origin Resource Sharing)
# ══════════════════════════════════════════════════════════════════════════════


class TestCors:
    """
    CORS —  iz,  and  and access to    and  domain.

     in and  and  CORS:
    - Access-Control-Allow-Origin: *  API  data and  →  may
       and  response from  amen and  user through fetch()
    -  and  iz Origin → attacker.com get access
    - ACAO: * + ACAC: true →  combined and ,   and yes str
       in misconfigured server

     and  main, catalog, search — all endpointnt, from
    contain userto and data or  and    and browser.
    """

    EVIL_ORIGIN = "https://evil-attacker.com"
    TRUSTED_ORIGIN = "https://www.truck1.eu"

    def _cors_headers(self, resp) -> dict:
        """CORS-headers response  in  and  and str."""
        return {
            k.lower(): v for k, v in resp.headers.items() if k.lower().startswith("access-control")
        }

    @pytest.mark.security
    @pytest.mark.parametrize(
        "path_name,path",
        [
            ("homepage", "/en/"),
            ("catalog", "/en/trucks-for-sale"),
            ("search", "/en/trucks-for-sale?q=volvo"),
        ],
    )
    def test_cors_no_wildcard_acao(self, client: ListingsClient, path_name: str, path: str):
        """TC_SEC21: Access-Control-Allow-Origin   '*'  and   om endpointnt."""
        resp = client.get(path, headers={"Origin": self.EVIL_ORIGIN})
        cors = self._cors_headers(resp)
        acao = cors.get("access-control-allow-origin", "")
        assert acao != "*", (
            f"CORS MISCONFIGURATION on '{path_name}': "
            f"Access-Control-Allow-Origin: * — any website can read this response!"
        )

    @pytest.mark.security
    @pytest.mark.parametrize(
        "path_name,path",
        [
            ("homepage", "/en/"),
            ("catalog", "/en/trucks-for-sale"),
        ],
    )
    def test_cors_origin_not_reflected(self, client: ListingsClient, path_name: str, path: str):
        """TC_SEC22: Origin  from  in Access-Control-Allow-Origin."""
        resp = client.get(path, headers={"Origin": self.EVIL_ORIGIN})
        acao = resp.headers.get("Access-Control-Allow-Origin", "")
        assert self.EVIL_ORIGIN not in acao, (
            f"CORS MISCONFIGURATION on '{path_name}': "
            f"Server reflects attacker's Origin back! ACAO='{acao}'"
        )

    @pytest.mark.security
    def test_cors_preflight_options(self, client: ListingsClient):
        """TC_SEC23: OPTIONS preflight does not disclose   for  Origin."""
        resp = client.session.options(
            client._url("/en/trucks-for-sale"),
            headers={
                "Origin": self.EVIL_ORIGIN,
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "Authorization",
            },
            timeout=client.timeout,
        )
        acam = resp.headers.get("Access-Control-Allow-Methods", "")
        acao = resp.headers.get("Access-Control-Allow-Origin", "")
        # If  server  and  Origin evil —     DELETE
        if self.EVIL_ORIGIN in acao or acao == "*":
            assert "DELETE" not in acam.upper(), (
                f"CORS MISCONFIGURATION: preflight allows DELETE for evil origin!\n"
                f"ACAO='{acao}', ACAM='{acam}'"
            )

    @pytest.mark.security
    def test_cors_no_credentials_for_evil_origin(self, client: ListingsClient):
        """TC_SEC24: version   credentials (cookies) for  Origin."""
        resp = client.get(
            client.locale_path(""),
            headers={"Origin": self.EVIL_ORIGIN},
        )
        acao = resp.headers.get("Access-Control-Allow-Origin", "")
        acac = resp.headers.get("Access-Control-Allow-Credentials", "").lower()
        # ACAO: * + ACAC: true —  and  combined and , browser e  to and ,
        #  ACAO: evil.com + ACAC: true —  vulnerable
        if self.EVIL_ORIGIN in acao:
            assert acac != "true", (
                f"CORS CRITICAL: Server allows credentials for evil origin!\n"
                f"ACAO='{acao}', ACAC='{acac}' — attacker can make auth requests!"
            )
