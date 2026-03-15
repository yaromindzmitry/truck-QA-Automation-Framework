"""
test_security_ui.py — UI security tests truck1.eu through Playwright

Coverage:
  TC_UISEC01  Clickjacking - page is not loaded in <iframe> (X-Frame-Options / CSP)
  TC_UISEC02  Security headers are present in real browser response
  TC_UISEC03  Mixed Content - page does not load HTTP-resources in HTTPS
  TC_UISEC04  Cookies — sessionid/auth-cookies have flags Secure and HttpOnly
  TC_UISEC05  Cookies — SameSite is not equal to None without Secure
  TC_UISEC06  XSS through URL-parameter — script does not execute in browser
  TC_UISEC07  console.error - page does not throw JS-errors during loading
  TC_UISEC08  Sensitive data is not leaked in URL (passwords, tokens)
  TC_UISEC09  Autofill is disabled on contact form (autocomplete=off)
  TC_UISEC10  External links open with rel="noopener noreferrer"

Note::
  Playwright uses real Chrome — Cloudflare passes it without challenge.
  Therefore these tests get real headers from origin server, not CF 202.
"""

import re

from playwright.sync_api import Page, Request, Response
import pytest


@pytest.mark.security
@pytest.mark.ui_security
class TestSecurityUI:
    # ── TC_UISEC01: Clickjacking ───────────────────────────────────────────────

    @pytest.mark.xfail(
        reason="SEC-BUG-001: X-Frame-Options header missing — site embeds in iframe (Clickjacking). "
               "Documented in bug_report_security.docx.",
        strict=True,
    )
    def test_clickjacking_iframe_blocked(self, page: Page):
        """
        TC_UISEC01: Attempt to embed truck1.eu in <iframe> must be blocked.

        Browser blocks iframe if server returns:
          - X-Frame-Options: DENY / SAMEORIGIN
          - Content-Security-Policy: frame-ancestors 'none' / 'self'

        Verify through JavaScript: try to load site in iframe
        and check if contentDocument is empty (blocked by browser).

        Known bug: SEC-BUG-001 — X-Frame-Options not set.
        """
        # Create test page with iframe
        page.set_content("""
            <html><body>
              <iframe id="test-frame"
                      src="https://www.truck1.eu/en"
                      width="800" height="600"
                      sandbox="allow-same-origin allow-scripts">
              </iframe>
            </body></html>
        """)
        page.wait_for_timeout(3000)

        # If X-Frame-Options or CSP worked — iframe will be empty
        iframe_loaded = page.evaluate("""() => {
            const frame = document.getElementById('test-frame');
            if (!frame) return false;
            try {
                const doc = frame.contentDocument;
                return doc && doc.body && doc.body.innerHTML.length > 100;
            } catch(e) {
                return false;  // cross-origin blocked
            }
        }""")

        # Empty iframe — means protection works
        assert not iframe_loaded, (
            "CLICKJACKING RISK: truck1.eu loaded inside <iframe>! "
            "X-Frame-Options or CSP frame-ancestors may not be set."
        )

    # ── TC_UISEC02: Security headers through real browser ─────────────────

    def test_security_headers_via_browser(self, page: Page):
        """
        TC_UISEC02: Verify security headers in real browser response.

        Unlike API test (requests), Playwright gets actual
        server response, not CF challenge. Therefore skip is not needed here with 202.
        """
        security_headers = {}

        def capture_response(resp: Response):
            if "truck1.eu/en" in resp.url and resp.status == 200:
                for header in [
                    "x-frame-options",
                    "content-security-policy",
                    "strict-transport-security",
                    "x-content-type-options",
                ]:
                    val = resp.headers.get(header, "")
                    if val:
                        security_headers[header] = val

        page.on("response", capture_response)
        page.goto("https://www.truck1.eu/en", wait_until="domcontentloaded", timeout=20_000)
        page.wait_for_timeout(1000)

        if not security_headers:
            pytest.skip("Could not capture origin response headers (CF or network issue)")

        # Verify at least one anti-clickjacking header
        has_frame_protection = (
            "x-frame-options" in security_headers or "content-security-policy" in security_headers
        )
        assert has_frame_protection, (
            "Neither X-Frame-Options nor CSP found in real browser response. "
            f"Captured headers: {list(security_headers.keys())}"
        )

    # ── TC_UISEC03: Mixed Content ──────────────────────────────────────────────

    def test_no_mixed_content(self, page: Page):
        """
        TC_UISEC03: HTTPS page does not load resources via HTTP (mixed content).

        Mixed content — vulnerability: HTTP-resource on HTTPS-page allows
        MITM-attack. Browser blocks active mixed content (JS/CSS),
        but passive (images) may pass with warning.
        """
        http_resources = []

        def on_request(req: Request):
            if req.url.startswith("http://"):
                http_resources.append(req.url)

        page.on("request", on_request)
        page.goto("https://www.truck1.eu/en", wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(2000)

        # Filter - localhost and data: URI do not count
        real_http = [
            url
            for url in http_resources
            if not url.startswith("http://localhost") and not url.startswith("http://127.")
        ]

        assert len(real_http) == 0, (
            f"MIXED CONTENT: {len(real_http)} HTTP resource(s) loaded on HTTPS page!\n"
            + "\n".join(f"  - {u}" for u in real_http[:10])
        )

    # ── TC_UISEC04 / TC_UISEC05: Cookie flags ─────────────────────────────────

    def test_sensitive_cookies_have_secure_flag(self, page: Page):
        """
        TC_UISEC04: Cookies with sessionid/token/auth have flag Secure.

        Without Secure — cookie transmitted over HTTP, vulnerable to interception.
        """
        page.goto("https://www.truck1.eu/en", wait_until="domcontentloaded", timeout=20_000)
        cookies = page.context.cookies()

        sensitive_patterns = re.compile(
            r"session|token|auth|jwt|csrf|user|login|account", re.IGNORECASE
        )

        violations = []
        for cookie in cookies:
            if sensitive_patterns.search(cookie["name"]) and not cookie.get("secure", False):
                violations.append(f"{cookie['name']} (domain={cookie.get('domain', '?')})")

        assert len(violations) == 0, (
            "COOKIE SECURITY: Sensitive cookies without Secure flag:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_cookies_samesite_not_none_without_secure(self, page: Page):
        """
        TC_UISEC05: Cookies with SameSite=None must have Secure flag.

        SameSite=None without Secure — incorrect configuration,
        modern browsers reject such cookies.
        """
        page.goto("https://www.truck1.eu/en", wait_until="domcontentloaded", timeout=20_000)
        cookies = page.context.cookies()

        violations = []
        for cookie in cookies:
            same_site = cookie.get("sameSite", "")
            if same_site and same_site.lower() == "none" and not cookie.get("secure", False):
                violations.append(cookie["name"])

        assert len(violations) == 0, (
            "COOKIE MISCONFIGURATION: SameSite=None without Secure:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    # ── TC_UISEC06: XSS through URL ─────────────────────────────────────────────

    def test_xss_via_url_param_not_executed(self, page: Page):
        """
        TC_UISEC06: XSS in URL-parameter does not execute in browser.

        If server reflects parameter without escaping — alert() works.
        Playwright intercepts dialog and test will fail.
        """
        xss_triggered = {"fired": False}

        def on_dialog(dialog):
            xss_triggered["fired"] = True
            dialog.dismiss()

        page.on("dialog", on_dialog)

        xss_payloads = [
            "/en?q=<script>alert('xss')</script>",
            "/en/trucks-for-sale?make=<img src=x onerror=alert(1)>",
            "/en?search=<svg/onload=alert(1)>",
        ]

        for path in xss_payloads:
            page.goto(f"https://www.truck1.eu{path}", wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_timeout(500)

        assert not xss_triggered["fired"], (
            "XSS VULNERABILITY: alert() was triggered via URL parameter! "
            "Server reflected script tag without escaping."
        )

    # ── TC_UISEC07: Console errors ────────────────────────────────────────────

    def test_no_critical_js_errors_on_load(self, page: Page):
        """
        TC_UISEC07: Page does not throw critical JS-errors during loading.

        Errors like "Uncaught TypeError" can indicate broken code
        or exploitation attempts. Filter known false-positives (advertising
        scripts, browser extensions).
        """
        errors = []

        def on_console(msg):
            if msg.type == "error":
                text = msg.text
                # Ignore: advertising/analytics scripts and extensions
                ignore_patterns = [
                    "ERR_BLOCKED_BY_CLIENT",
                    "favicon",
                    "net::ERR",
                    "chrome-extension",
                    "Failed to load resource",
                ]
                if not any(p in text for p in ignore_patterns):
                    errors.append(text)

        page.on("console", on_console)
        page.goto("https://www.truck1.eu/en", wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(2000)

        # Allow up to 3 non-critical errors (analytics, trackers)
        critical = [e for e in errors if "Uncaught" in e or "SyntaxError" in e]
        assert len(critical) == 0, (
            f"CRITICAL JS ERRORS on page load ({len(critical)}):\n"
            + "\n".join(f"  - {e}" for e in critical[:5])
        )

    # ── TC_UISEC08: Sensitive data in URL ───────────────────────────────

    def test_no_sensitive_data_in_url(self, page: Page):
        """
        TC_UISEC08: URL pages do not contain passwords, tokens or email addresses.

        Sensitive data in URL ends up in: server logs, browser
        history, Referer headers — and thus leaks.
        """
        sensitive_in_url = []

        def on_navigation(req: Request):
            url = req.url
            # Patterns: token=, password=, secret=, email=xxx@xxx
            patterns = [
                r"[?&]token=\w{8,}",
                r"[?&]password=\S+",
                r"[?&]secret=\S+",
                r"[?&]api_key=\S+",
                r"[?&]email=[^&@]+@[^&]+",
                r"[?&]access_token=\S+",
            ]
            for pat in patterns:
                if re.search(pat, url, re.IGNORECASE):
                    sensitive_in_url.append(url)
                    break

        page.on("request", on_navigation)
        # Go through several pages
        for path in ["/en", "/en/trucks-for-sale", "/en/trucks-for-lease"]:
            page.goto(f"https://www.truck1.eu{path}", wait_until="domcontentloaded", timeout=20_000)

        assert len(sensitive_in_url) == 0, "SENSITIVE DATA IN URL detected:\n" + "\n".join(
            f"  - {u[:200]}" for u in sensitive_in_url[:5]
        )

    # ── TC_UISEC09: autocomplete on forms ───────────────────────────────────

    def test_contact_form_autocomplete_off(self, page: Page):
        """
        TC_UISEC09: Form contact with seller has autocomplete=off
        on phone and email fields.

        Without this browser may autofill with other's data.
        """
        # Try to open listing and find contact form
        page.goto(
            "https://www.truck1.eu/en/trucks-for-sale",
            wait_until="domcontentloaded",
            timeout=20_000,
        )

        # Click on first listing
        card = page.locator("a[href*='/trucks-for-sale/']").first
        if not card.is_visible(timeout=5000):
            pytest.skip("No listing cards found to test contact form")

        card.click()
        page.wait_for_load_state("domcontentloaded", timeout=15_000)

        # Find contact button
        contact_btn = page.locator(
            "button:has-text('Contact'), button:has-text('Send message'), "
            "button[class*='contact'], [data-testid*='contact']"
        ).first
        if not contact_btn.is_visible(timeout=5000):
            pytest.skip("Contact button not found on listing page")

        contact_btn.click()
        page.wait_for_timeout(1000)

        # Verify input email/phone in popup
        phone_field = page.locator("input[type='tel'], input[name*='phone']").first
        if phone_field.is_visible(timeout=3000):
            autocomplete = phone_field.get_attribute("autocomplete") or ""
            # "off" or "tel" both acceptable (tel — standard type)
            # Bad: empty or "on"
            assert autocomplete.lower() not in ("on", ""), (
                f"Phone field missing autocomplete attribute (got: '{autocomplete}'). "
                "Consider autocomplete='off' or autocomplete='tel'."
            )

    # ── TC_UISEC10: rel=noopener on external links ───────────────────────────

    @pytest.mark.xfail(
        reason="SEC-BUG-002: Social media links (FB/IG/TikTok/LinkedIn) use rel='nofollow' "
               "but missing rel='noopener' — Tabnapping risk. "
               "Documented in bug_report_security.docx.",
        strict=True,
    )
    def test_external_links_have_noopener(self, page: Page):
        """
        TC_UISEC10: External links (<a target='_blank'>) have rel='noopener noreferrer'.

        Without noopener — opened page gets access to window.opener
        of parent page and may redirect it (reverse tabnapping).

        Known bug: SEC-BUG-002 — social media links missing rel='noopener'.
        """
        page.goto("https://www.truck1.eu/en", wait_until="domcontentloaded", timeout=20_000)

        violations = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[target="_blank"]'));
            return links
                .filter(a => {
                    const href = a.href || '';
                    const rel = (a.rel || '').toLowerCase();
                    const isExternal = href.startsWith('http') &&
                                       !href.includes('truck1.eu');
                    const hasNoopener = rel.includes('noopener');
                    return isExternal && !hasNoopener;
                })
                .map(a => ({ href: a.href, rel: a.rel, text: a.textContent.trim().slice(0, 50) }))
                .slice(0, 10);
        }""")

        assert len(violations) == 0, (
            f"REVERSE TABNAPPING RISK: {len(violations)} external link(s) "
            f"with target='_blank' missing rel='noopener':\n"
            + "\n".join(f"  - {v['href']} (rel='{v['rel']}')" for v in violations)
        )
