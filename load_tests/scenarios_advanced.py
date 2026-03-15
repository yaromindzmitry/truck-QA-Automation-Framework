"""
scenarios_advanced.py — Advanced load test scenarios truck1.eu

Supplements locustfile.py next  test :

  SpikeTest - to and to   (0 → 50 → 0  2 minutes)
  SoakTest - Long and  load (30+ min,  and  to and   and )
  StepLoadTest - Gradual  and  to and  failure
  ContentValidator - Verify that get real content, not CF challenge
  ApiEndpointTest - JSON API endpointnt (search,  and  and , filter)

Execution:

  # Spike- (to  )
  locust -f load_tests/scenarios_advanced.py SpikeTest \
         --headless --host https://www.truck1.eu

  # Soak- (1  to and ,  and  yes and )
  locust -f load_tests/scenarios_advanced.py SoakTest \
         --headless -u 15 -r 2 -t 1h --host https://www.truck1.eu \
         --html reports/soak_report.html

  # Step-load ( and  ku yes )
  locust -f load_tests/scenarios_advanced.py StepLoadTest \
         --headless -u 100 -r 5 -t 10m --host https://www.truck1.eu

  #  and yes and  content (  status,  real HTML)
  locust -f load_tests/scenarios_advanced.py ContentValidator \
         --headless -u 5 -r 1 -t 1m --host https://www.truck1.eu

  # API-tests
  locust -f load_tests/scenarios_advanced.py ApiEndpointTest \
         --headless -u 10 -r 2 -t 2m --host https://www.truck1.eu

  # All scenario   ( load)
  locust -f load_tests/scenarios_advanced.py \
         --headless -u 30 -r 3 -t 5m --host https://www.truck1.eu \
         --html reports/advanced_load_report.html
"""

import random
import time
from locust import HttpUser, task, between, constant_pacing, events
from locust.exception import StopUser

# ──  and  ───────────────────────────────────────────────────────────

BASE = "https://www.truck1.eu"
LOCALES = ["en", "de", "pl"]
BRANDS = ["volvo", "man", "mercedes", "daf", "scania", "renault", "iveco"]
YEARS = ["2015", "2016", "2017", "2018", "2019", "2020"]
ACCEPTABLE = {200, 202, 301, 302, 304}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

API_HEADERS = {
    **HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def _locale():
    return random.choices(LOCALES, weights=[60, 25, 15], k=1)[0]


def _ok(resp, name):
    if resp.status_code not in ACCEPTABLE:
        resp.failure(f"{name}: {resp.status_code}")
    else:
        resp.success()


# ── 1. Spike Test ─────────────────────────────────────────────────────────────

class SpikeTest(HttpUser):
    """
    And and  and  to  .
    scenario:      in And, link → to and   and .

     and  and to and :
    - Very from  between requests ( and user)
    -  and  load  catalog  and  search
    - Execution: -u 50 -r 25 -t 3m (str + str)
    """
    weight = 1
    wait_time = between(0.5, 2)  #  and user

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(HEADERS)

    @task(4)
    def spike_catalog(self):
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            name="[Spike] Catalog",
            catch_response=True,
        ) as r:
            _ok(r, "Spike Catalog")

    @task(3)
    def spike_search(self):
        brand = random.choice(BRANDS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale?q={brand}",
            name="[Spike] Search",
            catch_response=True,
        ) as r:
            _ok(r, "Spike Search")

    @task(2)
    def spike_homepage(self):
        with self.client.get(
            f"/{self.locale}",
            name="[Spike] Homepage",
            catch_response=True,
        ) as r:
            _ok(r, "Spike Homepage")

    @task(1)
    def spike_leasing(self):
        with self.client.get(
            f"/{self.locale}/trucks-for-lease",
            name="[Spike] Leasing",
            catch_response=True,
        ) as r:
            _ok(r, "Spike Leasing")


# ── 2. Soak Test ──────────────────────────────────────────────────────────────

class SoakTest(HttpUser):
    """
    Long and  load for  and  yes   iz and  and :
    - to and   and  (response time  e)
    -  and errors  
    - yes and   CDN

     and  and to and :
    - Realistic load (15–25 VU)
    - Long and : 30–60 minutes
    - Pause 5–15 sec (imitation slow  and )

    Execution: -u 20 -r 2 -t 30m
    """
    weight = 1
    wait_time = between(5, 15)

    #  and  yes and  —  time 
    _start_time = None

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(HEADERS)
        if SoakTest._start_time is None:
            SoakTest._start_time = time.time()

    def _elapsed_min(self):
        if SoakTest._start_time:
            return (time.time() - SoakTest._start_time) / 60
        return 0

    @task(3)
    def soak_catalog(self):
        elapsed = self._elapsed_min()
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            name=f"[Soak] Catalog",
            catch_response=True,
        ) as r:
            _ok(r, "Soak Catalog")
            # Detect yes and : if  10 min  long  2
            if elapsed > 10 and r.elapsed.total_seconds() > 2.0:
                r.failure(
                    f"SOAK DEGRADATION at {elapsed:.0f}min: "
                    f"catalog took {r.elapsed.total_seconds():.1f}s"
                )

    @task(2)
    def soak_search(self):
        brand = random.choice(BRANDS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale?q={brand}",
            name="[Soak] Search",
            catch_response=True,
        ) as r:
            _ok(r, "Soak Search")

    @task(2)
    def soak_category(self):
        cats = ["curtainsider-trucks", "refrigerated-trucks", "tipper-trucks", "box-trucks"]
        cat = random.choice(cats)
        with self.client.get(
            f"/{self.locale}/{cat}",
            name="[Soak] Category",
            catch_response=True,
        ) as r:
            _ok(r, "Soak Category")

    @task(1)
    def soak_leasing(self):
        with self.client.get(
            f"/{self.locale}/trucks-for-lease",
            name="[Soak] Leasing",
            catch_response=True,
        ) as r:
            _ok(r, "Soak Leasing")

    @task(1)
    def soak_deep_pagination(self):
        """Verify deepu  and  and  — pages 5, 10, 20."""
        page_num = random.choice([5, 10, 15, 20])
        with self.client.get(
            f"/{self.locale}/trucks-for-sale?page={page_num}",
            name="[Soak] Deep pagination",
            catch_response=True,
        ) as r:
            _ok(r, f"Soak Deep pagination p{page_num}")


# ── 3. Step Load Test (search to and  yes ) ───────────────────────────────

class StepLoadTest(HttpUser):
    """
    Gradual  and to and  for  and  breaking point.
    Run : -u 100 -r 5 -t 20m
    Look  asom  VU p95  and  3000ms or failure rate > 1%.

    Chart to and  (config through locust stages  in CI):
    0→10 VU  1 min → 10→25  2 min → 25→50  3 min → 50→100  5 min
    """
    weight = 1
    wait_time = between(1, 3)

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(HEADERS)

    @task(5)
    def step_catalog(self):
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            name="[Step] Catalog",
            catch_response=True,
        ) as r:
            _ok(r, "Step Catalog")

    @task(3)
    def step_search(self):
        brand = random.choice(BRANDS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale?q={brand}",
            name="[Step] Search",
            catch_response=True,
        ) as r:
            _ok(r, "Step Search")

    @task(2)
    def step_combined_filter(self):
        brand = random.choice(BRANDS)
        year = random.choice(YEARS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale?q={brand}&year_from={year}",
            name="[Step] Combined filter",
            catch_response=True,
        ) as r:
            _ok(r, "Step Combined")

    @task(1)
    def step_homepage(self):
        with self.client.get(
            f"/{self.locale}",
            name="[Step] Homepage",
            catch_response=True,
        ) as r:
            _ok(r, "Step Homepage")


# ── 4. Content Validator ──────────────────────────────────────────────────────

class ContentValidator(HttpUser):
    """
    Check  only status, but also real content page.
    Important: Cloudflare may return 200 with challenge-pageinstead of real content.

    What we check:
    -  in HTML is 'truck1' (brand is present)
    -  in HTML is <h1> (page rendered)
    - Size response > 10KB (not empty page)
    - No signs of CF-challenge  in content
    """
    weight = 1
    wait_time = between(3, 6)

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(HEADERS)

    @task(3)
    def validate_homepage_content(self):
        with self.client.get(
            f"/{self.locale}",
            name="[Content] Homepage — real content check",
            catch_response=True,
        ) as r:
            if r.status_code == 202:
                r.success()  # CF challenge — 
                return
            if r.status_code != 200:
                r.failure(f"Status {r.status_code}")
                return

            body = r.text
            issues = []

            if len(body) < 10_000:
                issues.append(f"Body too small: {len(body)} bytes (CF block?)")
            if "truck1" not in body.lower():
                issues.append("Brand 'truck1' not found in body")
            if "<h1" not in body.lower():
                issues.append("No <h1> found — page may not be rendered")
            if "just a moment" in body.lower() or "checking your browser" in body.lower():
                issues.append("CF Waiting page detected — bot blocked!")

            if issues:
                r.failure(" | ".join(issues))
            else:
                r.success()

    @task(4)
    def validate_catalog_content(self):
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            name="[Content] Catalog — listing cards check",
            catch_response=True,
        ) as r:
            if r.status_code == 202:
                r.success()
                return
            if r.status_code != 200:
                r.failure(f"Status {r.status_code}")
                return

            body = r.text
            issues = []

            if len(body) < 15_000:
                issues.append(f"Catalog body too small: {len(body)} bytes")
            if "trucks-for-sale/" not in body:
                issues.append("No listing links found in catalog HTML")
            if "just a moment" in body.lower():
                issues.append("CF challenge detected")
            # Verify that is from one heading pages
            if "<title" not in body.lower():
                issues.append("No <title> tag found")

            if issues:
                r.failure(" | ".join(issues))
            else:
                r.success()

    @task(2)
    def validate_leasing_content(self):
        with self.client.get(
            f"/{self.locale}/trucks-for-lease",
            name="[Content] Leasing — content check",
            catch_response=True,
        ) as r:
            if r.status_code in (202, 301, 302):
                r.success()
                return
            if r.status_code != 200:
                r.failure(f"Status {r.status_code}")
                return

            body = r.text
            if "just a moment" in body.lower():
                r.failure("CF challenge on leasing catalog")
            elif len(body) < 5_000:
                r.failure(f"Leasing page too small: {len(body)} bytes")
            else:
                r.success()

    @task(1)
    def validate_404_page(self):
        """404-page must from correctly,  yes  500."""
        with self.client.get(
            "/en/this-page-does-not-exist-qa-test-12345",
            name="[Content] 404 page check",
            catch_response=True,
        ) as r:
            # 404 —  and yesresponse. 500 — .
            if r.status_code in (404, 200, 202):
                r.success()
            elif r.status_code >= 500:
                r.failure(f"Server error on 404 URL: {r.status_code}")
            else:
                r.success()


# ── 5. API Endpoint Test ──────────────────────────────────────────────────────

class ApiEndpointTest(HttpUser):
    """
     and  JSON API endpointnt (search, filter, data listings).
    And and  and  request from SPA (Single Page App) yes.

    Important: API-endpointnt    and  CDN to  and 
    as HTML-pages, om load  backend .
    """
    weight = 1
    wait_time = between(1, 4)

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(API_HEADERS)

    @task(4)
    def api_search(self):
        """Search through API (AJAX-request  yes)."""
        brand = random.choice(BRANDS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={
                "q": brand,
                "format": "json",  # from   and  ?format=json
            },
            name="[API] Search query",
            catch_response=True,
        ) as r:
            if r.status_code in ACCEPTABLE:
                r.success()
            else:
                r.failure(f"API search failed: {r.status_code}")

    @task(3)
    def api_filter_combined(self):
        """om and  atedfilter — efor database request."""
        brand = random.choice(BRANDS)
        year = random.choice(YEARS)
        prices = ["20000", "30000", "50000", "80000"]
        price = random.choice(prices)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"q": brand, "year_from": year, "price_to": price, "page": 1},
            name="[API] Combined filter (heavy query)",
            catch_response=True,
        ) as r:
            if r.status_code in ACCEPTABLE:
                r.success()
            else:
                r.failure(f"Heavy filter failed: {r.status_code}")

    @task(2)
    def api_category_filter(self):
        """ filter by type ku."""
        bodies = [
            "curtainsider-trucks",
            "refrigerated-trucks",
            "tipper-trucks",
            "box-trucks",
            "flatbed-trucks",
            "container-trucks",
        ]
        body_type = random.choice(bodies)
        with self.client.get(
            f"/{self.locale}/{body_type}",
            name="[API] Category page",
            catch_response=True,
        ) as r:
            if r.status_code in ACCEPTABLE:
                r.success()
            else:
                r.failure(f"Category failed: {r.status_code}")

    @task(2)
    def api_deep_pagination(self):
        """Deep pagination — str for  data (OFFSET )."""
        page_num = random.choice([10, 20, 30, 50])
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"page": page_num},
            name="[API] Deep pagination (DB stress)",
            catch_response=True,
        ) as r:
            if r.status_code in ACCEPTABLE:
                r.success()
            else:
                r.failure(f"Deep pagination p{page_num} failed: {r.status_code}")

    @task(1)
    def api_robots_sitemap(self):
        """Verify robots.txt  and  sitemap — SEO- and   ."""
        path = random.choice(["/robots.txt", "/sitemap.xml", "/sitemap_index.xml"])
        with self.client.get(
            path,
            name="[API] robots/sitemap",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 202, 301, 302):
                r.success()
            elif r.status_code == 404:
                # sitemap may   —  error
                r.success()
            else:
                r.failure(f"{path} returned {r.status_code}")

    @task(1)
    def api_locale_switch(self):
        """ and   and  — check  rect."""
        src_locale = random.choice(LOCALES)
        dst_locale = random.choice([l for l in LOCALES if l != src_locale])
        with self.client.get(
            f"/{dst_locale}/trucks-for-sale",
            name="[API] Locale switch",
            catch_response=True,
            allow_redirects=True,
        ) as r:
            if r.status_code in ACCEPTABLE:
                r.success()
            else:
                r.failure(f"Locale switch {src_locale}→{dst_locale}: {r.status_code}")


# ── frome ─────────────────────────────────────────────────────────────

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.runner.stats
    total = stats.total

    p95 = total.get_response_time_percentile(0.95)
    p99 = total.get_response_time_percentile(0.99)
    fail_rate = total.fail_ratio * 100

    print("\n" + "=" * 65)
    print("  ADVANCED LOAD TEST — truck1.eu")
    print("=" * 65)
    print(f"  Requests total : {total.num_requests}")
    print(f"  Failure rate   : {fail_rate:.2f}%  {'✅' if fail_rate < 1 else '❌'}")
    print(f"  Avg resp time  : {total.avg_response_time:.0f} ms")
    print(f"  P95 resp time  : {p95:.0f} ms  {'✅' if p95 < 3000 else '❌ (>3s!)'}")
    print(f"  P99 resp time  : {p99:.0f} ms  {'✅' if p99 < 5000 else '❌ (>5s!)'}")
    print(f"  Max resp time  : {total.max_response_time:.0f} ms")
    print(f"  RPS (peak)     : {total.current_rps:.1f}")
    print("=" * 65)

    if fail_rate > 1 or p95 > 3000:
        environment.process_exit_code = 1
