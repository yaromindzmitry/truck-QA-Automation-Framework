"""
locustfile.py — Load testing truck1.eu

Tool: Locust (https://locust.io)
Installation:  pip install locust

⚠️  important: This is a production site. And only  ku.
           Cloudflare may temporarily to and  IP with  and  .
           For stress testing coordinate with the team fromto and .

User scenarios::
  BrowserUser - regular visitor (home → catalog → listing)
  SearchUser - user search (search  brand/ and )
  FilterUser - user filter in (filter  /)
  LeasingUser - visitor  leasing
  DealerUser - from pages dealer

Load levels::
  Smoke       1–3 user,  30 sec  — check everything works
  Light      10 users,  2 min   — e load
  Normal     25 users,  5 min   — imitation real traffic
  Stress     50 users, 10 min   — str (coordinate with the team)

Execution:
  # Headless (without UI), smoke-
  locust -f load_tests/locustfile.py --headless -u 3 -r 1 -t 30s --host https://www.truck1.eu

  #  web UI (from http://localhost:8089)
  locust -f load_tests/locustfile.py --host https://www.truck1.eu

  # Light load  HTML-fromeom
  locust -f load_tests/locustfile.py --headless -u 10 -r 2 -t 2m \\
         --host https://www.truck1.eu --html reports/load_report.html

  #  one scenario
  locust -f load_tests/locustfile.py BrowserUser --headless -u 5 -r 1 -t 1m \\
         --host https://www.truck1.eu

Metrics to watch::
  - Avg / 95th / 99th percentile response time (target: p95 < 3000ms)
  - Requests/sec (RPS)
  - Failure rate (target: < 1%)
  - Requests  error and  (4xx / 5xx)
"""

import random

from locust import HttpUser, between, events, task

# ──  ─────────────────────────────────────────────────────────────────

LOCALES = ["en", "de", "pl"]

TRUCK_BRANDS = ["volvo", "man", "mercedes", "daf", "scania", "renault", "iveco"]

YEAR_FROM_OPTIONS = ["2015", "2017", "2018", "2019", "2020"]

PRICE_TO_OPTIONS = ["30000", "50000", "80000", "100000"]

# Browser headers — reduce probability CF-blocking
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Acceptable:  response (Cloudflare may return 202 for bot challenge)
ACCEPTABLE_CODES = {200, 202, 301, 302, 304}


# ── Helper functions ───────────────────────────────────────────────────


def _check(response, name: str):
    """Check response  and  om as failure if  unexpected."""
    if response.status_code not in ACCEPTABLE_CODES:
        response.failure(f"{name}: unexpected status {response.status_code}")
    elif response.status_code == 202:
        # CF challenge —  error,  slow
        response.success()


def _locale() -> str:
    """and  (EN  all)."""
    return random.choices(LOCALES, weights=[60, 25, 15], k=1)[0]


# ── scenario 1: browseruser ───────────────────────────────


class BrowserUser(HttpUser):
    """
    And and  and   visitor:
    Homepage → catalog  in  in → point listings
    Pause between requests: 2–5 seconds (realistic page reading)
    Weight: 40% of all users
    """

    weight = 40
    wait_time = between(2, 5)

    def on_start(self):
        """and   home pages."""
        self.locale = _locale()
        self.client.headers.update(BROWSER_HEADERS)

    @task(3)
    def visit_homepage(self):
        """Homepage page."""
        with self.client.get(
            f"/{self.locale}",
            name="[BrowserUser] Homepage",
            catch_response=True,
        ) as resp:
            _check(resp, "Homepage")

    @task(5)
    def visit_catalog(self):
        """Catalog  in ."""
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            name="[BrowserUser] Catalog",
            catch_response=True,
        ) as resp:
            _check(resp, "Catalog")

    @task(2)
    def visit_catalog_page2(self):
        """page catalog (pagination)."""
        with self.client.get(
            f"/{self.locale}/trucks-for-sale?page=2",
            name="[BrowserUser] Catalog page 2",
            catch_response=True,
        ) as resp:
            _check(resp, "Catalog page 2")

    @task(4)
    def visit_listing(self):
        """Page listings ( and  and  and  navigation    iz catalog)."""
        # And  URL- truck1.eu
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            name="[BrowserUser] Catalog (pre-listing)",
            catch_response=True,
        ) as resp:
            _check(resp, "Catalog pre-listing")
            #  in om scenario    or href  iz HTML,
            #  for     and  and  and  from requests

    @task(1)
    def visit_leasing_catalog(self):
        """Catalog leasing."""
        with self.client.get(
            f"/{self.locale}/trucks-for-lease",
            name="[BrowserUser] Leasing catalog",
            catch_response=True,
        ) as resp:
            _check(resp, "Leasing catalog")


# ── scenario 2: User search ──────────────────────────────────────────


class SearchUser(HttpUser):
    """
    And and  and  user from and  specific ku:
    Search →  → navigation  listing
    Pause: 3–7 seconds ( request +  and results)
    Weight: 25% of all users
    """

    weight = 25
    wait_time = between(3, 7)

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(BROWSER_HEADERS)

    @task(5)
    def search_by_brand(self):
        """Search  brand  in ."""
        brand = random.choice(TRUCK_BRANDS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"q": brand},
            name="[SearchUser] Search by brand",
            catch_response=True,
        ) as resp:
            _check(resp, f"Search brand={brand}")

    @task(3)
    def search_with_year_filter(self):
        """Search  filterom  ."""
        year = random.choice(YEAR_FROM_OPTIONS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"year_from": year},
            name="[SearchUser] Search with year filter",
            catch_response=True,
        ) as resp:
            _check(resp, f"Search year_from={year}")

    @task(2)
    def search_curtainsider(self):
        """Search by type ku."""
        with self.client.get(
            f"/{self.locale}/curtainsider-trucks",
            name="[SearchUser] Category: curtainsider",
            catch_response=True,
        ) as resp:
            _check(resp, "Curtainsider category")

    @task(2)
    def search_refrigerated(self):
        """Search  and."""
        with self.client.get(
            f"/{self.locale}/refrigerated-trucks",
            name="[SearchUser] Category: refrigerated",
            catch_response=True,
        ) as resp:
            _check(resp, "Refrigerated category")

    @task(1)
    def search_tipper(self):
        """Search ."""
        with self.client.get(
            f"/{self.locale}/tipper-trucks",
            name="[SearchUser] Category: tipper",
            catch_response=True,
        ) as resp:
            _check(resp, "Tipper category")


# ── scenario 3: User filter in ────────────────────────────────────────


class FilterUser(HttpUser):
    """
    And and  and  user from and   and  filter:
    Catalog → filter   → filter   → combined atedfilter
    Pause: 4–8 seconds
    Weight: 20% of all users
    """

    weight = 20
    wait_time = between(4, 8)

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(BROWSER_HEADERS)

    @task(3)
    def filter_by_price(self):
        """filter   and ."""
        price = random.choice(PRICE_TO_OPTIONS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"price_to": price},
            name="[FilterUser] Filter by price",
            catch_response=True,
        ) as resp:
            _check(resp, f"Filter price_to={price}")

    @task(3)
    def filter_by_year(self):
        """filter   ."""
        year = random.choice(YEAR_FROM_OPTIONS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"year_from": year},
            name="[FilterUser] Filter by year",
            catch_response=True,
        ) as resp:
            _check(resp, f"Filter year_from={year}")

    @task(2)
    def filter_combined(self):
        """om and  atedfilter ( + price + )."""
        brand = random.choice(TRUCK_BRANDS)
        year = random.choice(YEAR_FROM_OPTIONS)
        price = random.choice(PRICE_TO_OPTIONS)
        with self.client.get(
            f"/{self.locale}/trucks-for-sale",
            params={"q": brand, "year_from": year, "price_to": price},
            name="[FilterUser] Combined filter",
            catch_response=True,
        ) as resp:
            _check(resp, "Combined filter")

    @task(1)
    def visit_dealers_list(self):
        """Page  and ."""
        with self.client.get(
            f"/{self.locale}/dealers",
            name="[FilterUser] Dealers list",
            catch_response=True,
        ) as resp:
            _check(resp, "Dealers list")


# ── scenario 4: User leasing ─────────────────────────────────────────


class LeasingUser(HttpUser):
    """
    And and  and  user leasingom.
    Pause: 5–10 seconds ( and   iz and  in and )
    Weight: 15% of all users
    """

    weight = 15
    wait_time = between(5, 10)

    def on_start(self):
        self.locale = _locale()
        self.client.headers.update(BROWSER_HEADERS)

    @task(4)
    def visit_leasing_catalog(self):
        """Catalog leasing."""
        with self.client.get(
            f"/{self.locale}/trucks-for-lease",
            name="[LeasingUser] Leasing catalog",
            catch_response=True,
        ) as resp:
            _check(resp, "Leasing catalog")

    @task(3)
    def visit_leasing_page2(self):
        """page leasing."""
        with self.client.get(
            f"/{self.locale}/trucks-for-lease?page=2",
            name="[LeasingUser] Leasing page 2",
            catch_response=True,
        ) as resp:
            _check(resp, "Leasing page 2")

    @task(2)
    def visit_homepage(self):
        """main."""
        with self.client.get(
            f"/{self.locale}",
            name="[LeasingUser] Homepage",
            catch_response=True,
        ) as resp:
            _check(resp, "Homepage")


# ──  and:   and  in ────────────────────────────────────────────────────


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """and   and   and to and  with version  ."""
    stats = environment.runner.stats
    total = stats.total

    print("\n" + "=" * 60)
    print("  LOAD TEST RESULTS — truck1.eu")
    print("=" * 60)
    print(f"  Total requests : {total.num_requests}")
    print(f"  Failures       : {total.num_failures} ({total.fail_ratio * 100:.1f}%)")
    print(f"  Avg resp time  : {total.avg_response_time:.0f} ms")
    print(f"  95th percentile: {total.get_response_time_percentile(0.95):.0f} ms")
    print(f"  99th percentile: {total.get_response_time_percentile(0.99):.0f} ms")
    print(f"  Max resp time  : {total.max_response_time:.0f} ms")
    print(f"  Requests/sec   : {total.current_rps:.1f}")
    print("=" * 60)

    # Thresholds — if violated,   and
    p95 = total.get_response_time_percentile(0.95)
    fail_rate = total.fail_ratio * 100

    issues = []
    if fail_rate > 1.0:
        issues.append(f"❌ Failure rate {fail_rate:.1f}% > 1% threshold")
    if p95 > 3000:
        issues.append(f"❌ P95 response time {p95:.0f}ms > 3000ms threshold")

    if issues:
        print("\n  THRESHOLDS VIOLATED:")
        for issue in issues:
            print(f"  {issue}")
        environment.process_exit_code = 1
    else:
        print("\n  ✅ All thresholds passed")
    print()
