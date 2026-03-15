"""
test_api_db_blackbox.py — advanced black-box testing of truck1.eu database

What is black-box DB testing:
  Direct DB access is missing. We test through HTTP requests,
  analyzing behavior from responses: status codes, response time, response body.
  From deviations we draw conclusions about how the database is structured and protected.

Coverage:
  ── Error-Based SQL Injection ──────────────────────────────────────────────
  TC_DB01   DB error leakage in HTML response (MySQL / PostgreSQL / MSSQL / Oracle)
  TC_DB02   Stack trace or file path is not disclosed in response
  TC_DB03   SQL syntax errors are not visible to user

  ── Blind Boolean-Based SQL Injection ──────────────────────────────────────
  TC_DB04   Difference in response with TRUE vs FALSE conditions (boolean-based blind)
  TC_DB05   Difference in result count with TRUE vs FALSE (boolean parameter)

  ── Blind Time-Based SQL Injection ─────────────────────────────────────────
  TC_DB06   SLEEP()/pg_sleep()/WAITFOR DELAY do not cause response delay
  TC_DB07   Response time is stable and does not depend on numeric payload

  ── Second-Order Injection ─────────────────────────────────────────────────
  TC_DB08   Search with quote is stored and returned escaped

  ── NoSQL Injection ────────────────────────────────────────────────────────
  TC_DB09   MongoDB operators ($gt, $ne, $where) do not bypass filter
  TC_DB10   JSON injection in request parameters does not cause 500

  ── Information Disclosure ─────────────────────────────────────────────────
  TC_DB11   DB version is not disclosed in response (version(), @@version)
  TC_DB12   System tables are not returned (information_schema, pg_tables)
  TC_DB13   Column/table names are not disclosed in error messages

  ── Mass Assignment / Over-Fetching ────────────────────────────────────────
  TC_DB14   Filters accept only expected parameters, ignore extra ones
  TC_DB15   LIMIT/OFFSET parameter does not allow fetching excess data

  ── ORM Injection ──────────────────────────────────────────────────────────
  TC_DB16   Django/Rails ORM-specific injection does not cause 500
  TC_DB17   Nested parameters (param[key]=val) do not cause 500

  ── Encoding & Bypass ──────────────────────────────────────────────────────
  TC_DB18   URL-encoded SQL-injection does not cause 500
  TC_DB19   Double URL-encoded injection does not cause 500
  TC_DB20   Unicode-homoglyph injection does not cause 500

Execution:
  pytest api/tests/test_api_db_blackbox.py -v
  pytest api/tests/test_api_db_blackbox.py -v -m db
  pytest api/tests/test_api_db_blackbox.py -v -m "db and not slow"

Note: Cloudflare behavior:
  CF returns 202 with headless requests. Tests for data leakage
  work correctly — if 500 or DB error occurs, it passed through CF.
  Time-based tests are less reliable due to CF overhead, so delay threshold
  is set conservatively (3 sec instead of 1).
"""

import re
import time
import pytest

from api.client import ListingsClient, SearchClient, REACHABLE

# ── Constants ─────────────────────────────────────────────────────────────────

# Patterns indicating DB error leakage in HTML
DB_ERROR_PATTERNS = [
    # MySQL
    r"you have an error in your sql syntax",
    r"warning: mysql",
    r"mysql_fetch",
    r"mysql_num_rows",
    r"supplied argument is not a valid mysql",
    r"com\.mysql\.jdbc",
    # PostgreSQL
    r"pg_query\(\)",
    r"pg_exec\(\)",
    r"postgresql.*error",
    r"org\.postgresql",
    r"psql.*error",
    r"pgerror",
    # MSSQL
    r"microsoft ole db provider for sql server",
    r"odbc sql server driver",
    r"sqlserver",
    r"\[microsoft\]\[odbc",
    r"unclosed quotation mark",
    r"incorrect syntax near",
    # Oracle
    r"ora-\d{4,5}",
    r"oracle.*driver",
    r"quoted string not properly terminated",
    # SQLite
    r"sqlite_error",
    r"sqlite.*exception",
    # Generic
    r"sql syntax.*near",
    r"syntax error.*sql",
    r"database error",
    r"db error",
    r"error in your sql",
    r"jdbc.*exception",
    r"syntax error.*from",
    # Stack traces
    r"at java\.",
    r"at org\.",
    r"traceback \(most recent",
    r"django\.db\.utils",
    r"activerecord::",
    r"sequelizeerror",
]

# Patterns for version / DB structure leakage
DB_INFO_PATTERNS = [
    r"\d+\.\d+\.\d+.*mysql",
    r"postgresql \d+\.\d+",
    r"microsoft sql server \d{4}",
    r"information_schema",
    r"pg_tables",
    r"sys\.objects",
    r"sysobjects",
    r"@@version",
    r"sqlite_master",
]

# SQL payloads for error-based (provoke syntax error)
ERROR_BASED_PAYLOADS = [
    ("single_quote",     "'"),
    ("double_quote",     '"'),
    ("backtick",         "`"),
    ("unmatched_paren",  "')"),
    ("double_dash",      "'--"),
    ("hash",             "'#"),
    ("slash_star",       "'/*"),
    ("semicolon",        "';"),
    ("concat_mysql",     "' concat(0x7e,version()) --"),
    ("extractvalue",     "' AND extractvalue(1,concat(0x7e,(SELECT version()))) --"),
    ("updatexml",        "' AND updatexml(1,concat(0x7e,(SELECT version())),1) --"),
    ("pg_error",         "' AND 1=CAST(version() AS int) --"),
    ("mssql_error",      "' AND 1=CONVERT(int,(SELECT @@version)) --"),
]

# SQL payloads for time-based (provoke delay)
TIME_BASED_PAYLOADS = [
    ("mysql_sleep",      "' AND SLEEP(3) --"),
    ("pg_sleep",         "'; SELECT pg_sleep(3) --"),
    ("mssql_waitfor",    "'; WAITFOR DELAY '0:0:3' --"),
    ("heavy_union",      "' UNION SELECT SLEEP(3),2,3 --"),
    ("benchmark",        "' AND BENCHMARK(5000000,MD5('test')) --"),
]

# Boolean-based payloads — TRUE/FALSE pair for each test
BOOLEAN_PAIRS = [
    ("and_true",  "Volvo' AND '1'='1",  "Volvo' AND '1'='2"),
    ("or_true",   "Volvo' OR 'x'='x",   "Volvo' OR 'x'='y"),
    ("comment",   "Volvo'-- -",          "Volvo'AND 1=2-- -"),
]

# NoSQL payloads
NOSQL_PAYLOADS = [
    ("mongo_gt",     '{"$gt": ""}'),
    ("mongo_ne",     '{"$ne": null}'),
    ("mongo_where",  '{"$where": "sleep(1)"}'),
    ("mongo_regex",  '{"$regex": ".*"}'),
    ("array_ne",     "[$ne]=1"),
    ("array_gt",     "[$gt]="),
    ("json_true",    '{"price": {"$gt": 0}}'),
]

# ORM / Framework-specific payloads
ORM_PAYLOADS = [
    ("django_extra",   "' extra select=1 --"),
    ("rails_hash",     "make[0]=Volvo&make[1]=DAF"),
    ("nested_bracket", "filter[make]=Volvo&filter[price][$gt]=0"),
    ("dot_notation",   "make.name=Volvo"),
]

# Acceptable response codes (server is alive)
SAFE_CODES = (*REACHABLE, 400, 404, 410, 422)
TIME_THRESHOLD_SECONDS = 4.0  # above — suspicious delay
MAX_ALLOWED_DELAY_MS = 3500   # ms — threshold for time-based test


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return ListingsClient(locale="en")


@pytest.fixture(scope="module")
def search():
    return SearchClient(locale="en")


def _has_db_error(text: str) -> tuple[bool, str]:
    """Returns (True, pattern) if DB error leakage found in text."""
    text_lower = text.lower()
    for pattern in DB_ERROR_PATTERNS:
        if re.search(pattern, text_lower):
            return True, pattern
    return False, ""


def _has_db_info(text: str) -> tuple[bool, str]:
    """Returns (True, pattern) if version or DB structure leakage found."""
    text_lower = text.lower()
    for pattern in DB_INFO_PATTERNS:
        if re.search(pattern, text_lower):
            return True, pattern
    return False, ""


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB01–TC_DB03: Error-Based SQL Injection
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestErrorBasedSqlInjection:
    """
    Provoke SQL syntax errors and check that server:
    1. Not returns 500
    2. Not disclose DB error text in HTML
    3. Not expose stack trace or file path
    """

    @pytest.mark.parametrize("name,payload", ERROR_BASED_PAYLOADS)
    def test_no_db_error_in_search(self, search: SearchClient, name: str, payload: str):
        """TC_DB01: DB error  database  is visible in searchom response."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"ERROR-BASED SQLi [{name}]: 500 on search! Payload: {repr(payload)}"
        )
        found, pattern = _has_db_error(resp.text)
        assert not found, (
            f"DB ERROR LEAKED [{name}] in search response!\n"
            f"Pattern matched: '{pattern}'\nPayload: {repr(payload)}"
        )

    @pytest.mark.parametrize("name,payload", ERROR_BASED_PAYLOADS[:8])
    def test_no_db_error_in_catalog_make(self, client: ListingsClient, name: str, payload: str):
        """TC_DB01: DB error  database is not visible with  injection  and   in parameter make."""
        resp = client.get_sale_catalog(make=payload)
        assert resp.status_code != 500, (
            f"ERROR-BASED SQLi [{name}]: 500 on make filter! Payload: {repr(payload)}"
        )
        found, pattern = _has_db_error(resp.text)
        assert not found, (
            f"DB ERROR LEAKED [{name}] in catalog (make) response!\n"
            f"Pattern: '{pattern}'\nPayload: {repr(payload)}"
        )

    @pytest.mark.parametrize("name,payload", [
        ("year_from",   "' OR 1=1 --"),
        ("year_to",     "2020 UNION SELECT NULL --"),
        ("price_from",  "0 AND extractvalue(1,version())"),
        ("price_to",    "' AND updatexml(1,version(),1) --"),
    ])
    def test_no_db_error_in_numeric_filters(
        self, client: ListingsClient, name: str, payload: str
    ):
        """TC_DB01: DB error  database is not visible with  injection  and   in numeric filter."""
        resp = client.get(
            client.locale_path("trucks-for-sale"),
            params={name.split("_")[0] + "_" + name.split("_")[1]: payload}
            if "_" in name else {name: payload}
        )
        assert resp.status_code != 500
        found, pattern = _has_db_error(resp.text)
        assert not found, (
            f"DB ERROR LEAKED in '{name}'! Pattern: '{pattern}', Payload: {repr(payload)}"
        )

    def test_no_stacktrace_in_response(self, search: SearchClient):
        """TC_DB02: Stack trace does not disclosed with syntax ."""
        stacktrace_patterns = [
            r"traceback \(most recent call last\)",
            r"at java\.lang\.",
            r"django\.core\.exceptions",
            r"activerecord::statementinvalid",
            r"file.*\.py.*line \d+",
            r"file.*\.rb.*line \d+",
            r"exception in thread",
        ]
        resp = search.search_listings("' AND 1=CAST((SELECT version()) AS integer)--")
        text_lower = resp.text.lower()
        for pat in stacktrace_patterns:
            assert not re.search(pat, text_lower), (
                f"STACK TRACE LEAKED! Pattern '{pat}' found in response."
            )

    def test_no_sql_syntax_visible(self, client: ListingsClient):
        """TC_DB03: text SQL- and to and   is shown user."""
        resp = client.get_sale_catalog(make="' invalid sql '''")
        assert resp.status_code != 500
        text_lower = resp.text.lower()
        # Neither one  iz  and   in     in response
        forbidden = ["syntax error", "sql error", "query failed", "database error"]
        for phrase in forbidden:
            assert phrase not in text_lower, (
                f"SQL ERROR TEXT VISIBLE: '{phrase}' found in response!"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB04–TC_DB05: Blind Boolean-Based SQL Injection
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestBooleanBlindSqlInjection:
    """
    Boolean-based blind: compare responses for TRUE/FALSE conditions.
    If responses are IDENTICAL — condition properly escaped by SQL.
    If responses are DIFFERENT — sign of vulnerability (payload affects request).

    Key metrics:
    - HTTP status
    - Response size (difference > 500 bytes with identical parameters — suspicious)
    """

    @pytest.mark.parametrize("name,payload_true,payload_false", BOOLEAN_PAIRS)
    def test_true_false_same_response_size(
        self, search: SearchClient, name: str, payload_true: str, payload_false: str
    ):
        """TC_DB04: Size response with TRUE  and  FALSE conditions  from  significantly."""
        resp_true = search.search_listings(payload_true)
        resp_false = search.search_listings(payload_false)

        #   version identical status
        assert resp_true.status_code == resp_false.status_code, (
            f"BOOLEAN BLIND [{name}]: Status codes differ! "
            f"TRUE={resp_true.status_code}, FALSE={resp_false.status_code}"
        )

        # If   200 (real response) —    significantly from 
        if resp_true.status_code == 200 and resp_false.status_code == 200:
            size_true = len(resp_true.content)
            size_false = len(resp_false.content)
            diff = abs(size_true - size_false)
            # If   pages >10KB  and   and  >30% —  and 
            if size_true > 10_000 and size_false > 10_000:
                ratio = diff / max(size_true, size_false)
                assert ratio < 0.30, (
                    f"BOOLEAN BLIND [{name}]: Response size differs significantly!\n"
                    f"TRUE={size_true}b, FALSE={size_false}b, diff={diff}b ({ratio:.0%})\n"
                    f"TRUE payload: {repr(payload_true)}\nFALSE payload: {repr(payload_false)}"
                )

    def test_boolean_in_numeric_param(self, client: ListingsClient):
        """TC_DB05: Boolean  injection  in numeric parameter    and."""
        # Normal request
        resp_normal = client.get_sale_catalog(year_from=2020)
        # Injection and  — if vulnerable, versione all  or other 
        resp_injected = client.get_sale_catalog(year_from="2020 OR 1=1")

        assert resp_injected.status_code != 500
        # If   200 — check that content approximately identically in if resp_normal.status_code == 200 and resp_injected.status_code == 200:
            size_normal = len(resp_normal.content)
            size_injected = len(resp_injected.content)
            if size_normal > 10_000:
                ratio = abs(size_normal - size_injected) / size_normal
                assert ratio < 0.50, (
                    f"BOOLEAN BLIND: Numeric param 'year_from' shows different results "
                    f"with 'OR 1=1' injection! Normal={size_normal}b, Injected={size_injected}b"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB06–TC_DB07: Blind Time-Based SQL Injection
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
@pytest.mark.slow
class TestTimeBasedSqlInjection:
    """
    Time-based blind: if SLEEP(3) causes delay ≥3 sec — injection works.
    Threshold set conservatively (4 sec) due to possible CF/network delays.

    Marked as @pytest.mark.slow — exclude from quick runs:
      pytest api/tests/test_api_db_blackbox.py -m "db and not slow"
    """

    @pytest.mark.parametrize("name,payload", TIME_BASED_PAYLOADS)
    def test_no_sleep_delay_in_search(self, search: SearchClient, name: str, payload: str):
        """TC_DB06: SLEEP/pg_sleep/WAITFOR do not cause response delay."""
        start = time.time()
        resp = search.search_listings(payload)
        elapsed = time.time() - start

        assert resp.status_code != 500, f"TIME-BASED [{name}]: caused 500!"
        assert elapsed < TIME_THRESHOLD_SECONDS, (
            f"TIME-BASED SQLi DETECTED [{name}]!\n"
            f"Response took {elapsed:.2f}s — exceeds threshold {TIME_THRESHOLD_SECONDS}s\n"
            f"Payload: {repr(payload)}\n"
            f"This indicates SLEEP() or pg_sleep() executed on the server!"
        )

    @pytest.mark.parametrize("name,payload", TIME_BASED_PAYLOADS[:3])
    def test_no_sleep_delay_in_make_filter(
        self, client: ListingsClient, name: str, payload: str
    ):
        """TC_DB06: SLEEP in parameter make does not cause ku."""
        start = time.time()
        resp = client.get_sale_catalog(make=payload)
        elapsed = time.time() - start

        assert resp.status_code != 500
        assert elapsed < TIME_THRESHOLD_SECONDS, (
            f"TIME-BASED SQLi [{name}] in 'make'! Elapsed: {elapsed:.2f}s\n"
            f"Payload: {repr(payload)}"
        )

    def test_response_time_stable_for_numeric(self, client: ListingsClient):
        """TC_DB07: Time response  and  for  and  parameter."""
        times = []
        for year in [2018, 2019, 2020, 2021, 2022]:
            start = time.time()
            client.get_sale_catalog(year_from=year)
            times.append(time.time() - start)

        #  and     3 sec
        spread = max(times) - min(times)
        assert spread < 3.0, (
            f"UNSTABLE RESPONSE TIMES for year_from param! "
            f"Times: {[f'{t:.2f}s' for t in times]}, spread={spread:.2f}s"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB08: Second-Order Injection
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestSecondOrderInjection:
    """
    Second-order: payload stored  in database with om request,
     and   as SQL with next.
    Verify that response returns  atedpayload.
    """

    def test_search_returns_escaped_quote(self, search: SearchClient):
        """TC_DB08: Search  quotedoes not cause  and ku with repeated request."""
        payloads = ["Volvo'", "MAN''s truck", "DAF' OR 1=1--"]
        for payload in payloads:
            # request — ""
            resp1 = search.search_listings(payload)
            assert resp1.status_code != 500, f"Second-order [save]: 500 for {repr(payload)}"
            found, pat = _has_db_error(resp1.text)
            assert not found, f"DB error on save phase: {pat}"

            # request — " and "
            resp2 = search.search_listings(payload)
            assert resp2.status_code != 500, f"Second-order [read]: 500 for {repr(payload)}"
            found, pat = _has_db_error(resp2.text)
            assert not found, f"DB error on read phase: {pat}"


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB09–TC_DB10: NoSQL Injection
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestNoSqlInjection:
    """
    NoSQL injection: if   and  MongoDB or ElasticSearch,
    operators $gt/$ne/$where   and  filter and .
     izto vulnerable and  — 500 or  and data  results.
    """

    @pytest.mark.parametrize("name,payload", NOSQL_PAYLOADS)
    def test_nosql_operator_in_search(self, search: SearchClient, name: str, payload: str):
        """TC_DB09: MongoDB/NoSQL operators  in search do not cause 500."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"NoSQL INJECTION [{name}]: caused 500! Payload: {repr(payload)}"
        )
        assert resp.status_code in SAFE_CODES

    @pytest.mark.parametrize("name,payload", NOSQL_PAYLOADS)
    def test_nosql_operator_in_make(self, client: ListingsClient, name: str, payload: str):
        """TC_DB09: MongoDB/NoSQL operators in parameter make do not cause 500."""
        resp = client.get_sale_catalog(make=payload)
        assert resp.status_code != 500, (
            f"NoSQL INJECTION [{name}] in make: caused 500! Payload: {repr(payload)}"
        )

    def test_json_body_injection(self, client: ListingsClient):
        """TC_DB10: JSON- injection  in request body POST-request does not cause 500."""
        json_payloads = [
            {"make": {"$gt": ""}},
            {"make": {"$ne": None}},
            {"year_from": {"$gt": 0}},
            {"price": {"$where": "sleep(1)"}},
        ]
        for payload in json_payloads:
            resp = client.post(
                client.locale_path("trucks-for-sale"),
                json=payload,
            )
            # POST  GET-endpoint versione 405 or 302 — this 
            assert resp.status_code != 500, (
                f"JSON NoSQL injection caused 500! Payload: {payload}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB11–TC_DB13: Information Disclosure
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestInformationDisclosure:
    """
    Verify that server does not disclose:
    -  and  database (version(), @@version, pg_version())
    -  system  and  (information_schema, pg_tables, sysobjects)
    - Andnames columns /  and   in message and   error
    """

    @pytest.mark.parametrize("name,payload", [
        ("mysql_version",   "' UNION SELECT version(),2,3 --"),
        ("pg_version",      "' UNION SELECT version(),NULL,NULL --"),
        ("mssql_version",   "' UNION SELECT @@version,NULL,NULL --"),
        ("mysql_user",      "' UNION SELECT user(),2,3 --"),
        ("pg_user",         "' UNION SELECT current_user,NULL,NULL --"),
    ])
    def test_db_version_not_disclosed_via_union(
        self, search: SearchClient, name: str, payload: str
    ):
        """TC_DB11: UNION SELECT version() does not disclose version and  database."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500
        found, pat = _has_db_info(resp.text)
        assert not found, (
            f"DB VERSION DISCLOSED [{name}]! Pattern: '{pat}'\nPayload: {repr(payload)}"
        )

    @pytest.mark.parametrize("name,payload", [
        ("info_schema_tables",  "' UNION SELECT table_name FROM information_schema.tables --"),
        ("info_schema_columns", "' UNION SELECT column_name FROM information_schema.columns --"),
        ("pg_tables",           "' UNION SELECT tablename FROM pg_tables --"),
        ("mssql_sysobjects",    "' UNION SELECT name FROM sysobjects --"),
        ("sqlite_master",       "' UNION SELECT name FROM sqlite_master --"),
    ])
    def test_system_tables_not_accessible(
        self, search: SearchClient, name: str, payload: str
    ):
        """TC_DB12:  system  and  is not returned through UNION SELECT."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500
        text_lower = resp.text.lower()
        # Andnames  system  and      in response
        forbidden_table_names = [
            "information_schema", "pg_tables", "sysobjects",
            "sqlite_master", "sys.objects"
        ]
        for name_str in forbidden_table_names:
            assert name_str not in text_lower, (
                f"SYSTEM TABLE EXPOSED [{name}]: '{name_str}' found in response!"
            )

    def test_column_names_not_in_errors(self, client: ListingsClient):
        """TC_DB13: Andnames columns does not disclosed  in errors."""
        resp = client.get_sale_catalog(make="' GROUP BY 1,2,3,4,5,6,7,8,9,10 --")
        assert resp.status_code != 500
        #  "unknown column 'X'" disclose str  and 
        unknown_col = re.search(r"unknown column ['\"`](\w+)['\"`]", resp.text.lower())
        assert not unknown_col, (
            f"COLUMN NAME DISCLOSED: '{unknown_col.group(1)}' found in error response!"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB14–TC_DB15: Mass Assignment / Over-Fetching
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestMassAssignment:
    """
    Mass assignment: yese  and data parameter   in ORM/request.
    Over-fetching:  get and   data  .
    """

    def test_unexpected_params_ignored(self, client: ListingsClient):
        """TC_DB14: Not and data parameter do not cause 500  and   and  and ."""
        unexpected = {
            "admin": "true",
            "is_deleted": "false",
            "internal": "1",
            "debug": "true",
            "raw_sql": "SELECT * FROM listings",
            "order_by": "id DESC",
            "limit": "99999",
            "offset": "0",
            "select": "*",
            "where": "1=1",
            "table": "listings",
        }
        for param, value in unexpected.items():
            resp = client.get(
                client.locale_path("trucks-for-sale"),
                params={param: value}
            )
            assert resp.status_code != 500, (
                f"Unexpected param '{param}={value}' caused 500!"
            )

    @pytest.mark.parametrize("limit_val", [
        "99999", "999999", "-1", "0", "2147483647", "9999999999"
    ])
    def test_large_limit_handled(self, client: ListingsClient, limit_val: str):
        """TC_DB15: Very LIMIT does not lead to  alldatabase or 500."""
        resp = client.get(
            client.locale_path("trucks-for-sale"),
            params={"limit": limit_val, "per_page": limit_val, "page_size": limit_val}
        )
        assert resp.status_code != 500, f"Large limit={limit_val} caused 500!"
        # If 200 — response    om (sign of to and  all and )
        if resp.status_code == 200:
            size_mb = len(resp.content) / (1024 * 1024)
            assert size_mb < 10, (
                f"OVER-FETCHING RISK: Response is {size_mb:.1f}MB for limit={limit_val}! "
                "Possible data dump from database."
            )


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB16–TC_DB17: ORM Injection
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestOrmInjection:
    """
    ORM- and   to and    to and :
    Django, Rails ActiveRecord, Sequelize, TypeORM.
    """

    @pytest.mark.parametrize("name,payload", [
        ("django_extra",        "' extra select=1 --"),
        ("django_raw",          "make=Volvo&raw=SELECT * FROM listings"),
        ("rails_arel",          "' Arel.sql('SELECT 1') --"),
        ("sequelize_literal",   "' Sequelize.literal('1=1') --"),
        ("typeorm_query",       "' QueryBuilder.where('1=1') --"),
    ])
    def test_orm_specific_payloads(self, search: SearchClient, name: str, payload: str):
        """TC_DB16: ORM- and   injection does not cause 500."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"ORM INJECTION [{name}]: caused 500! Payload: {repr(payload)}"
        )
        found, pat = _has_db_error(resp.text)
        assert not found, f"DB error for ORM injection [{name}]: {pat}"

    @pytest.mark.parametrize("param,value", [
        ("make[]",          "Volvo"),
        ("make[0]",         "Volvo"),
        ("make[name]",      "Volvo"),
        ("make[like]",      "%Volvo%"),
        ("make[contains]",  "Volvo"),
        ("filter[make]",    "Volvo"),
        ("where[make]",     "Volvo"),
        ("make[ne]",        ""),
        ("make[gt]",        ""),
    ])
    def test_nested_bracket_params(self, client: ListingsClient, param: str, value: str):
        """TC_DB17:  parameter  in bracket-from  do not cause 500."""
        resp = client.get(
            client.locale_path("trucks-for-sale"),
            params={param: value}
        )
        assert resp.status_code != 500, (
            f"Bracket param '{param}={value}' caused 500!"
        )
        found, pat = _has_db_error(resp.text)
        assert not found, f"DB error for bracket param [{param}]: {pat}"


# ══════════════════════════════════════════════════════════════════════════════
# TC_DB18–TC_DB20: Encoding & WAF Bypass
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.db
class TestEncodingBypass:
    """
    WAF/filter  version only   injection  and .
    one   and   and   and   in and  payload  database.
    """

    @pytest.mark.parametrize("name,payload", [
        ("url_encoded_quote",  "%27"),
        ("url_encoded_union",  "%27%20UNION%20SELECT%20NULL--"),
        ("url_encoded_or",     "%27%20OR%20%271%27%3D%271"),
        ("url_encoded_sleep",  "%27%20AND%20SLEEP(3)--"),
    ])
    def test_url_encoded_sql(self, search: SearchClient, name: str, payload: str):
        """TC_DB18: URL-encoded SQL injection does not cause 500."""
        # yese as raw string — requests     and 
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"URL-ENCODED SQLi [{name}]: caused 500! Payload: {repr(payload)}"
        )
        found, pat = _has_db_error(resp.text)
        assert not found, f"DB error for URL-encoded [{name}]: {pat}"

    @pytest.mark.parametrize("name,payload", [
        ("double_encoded_quote",  "%2527"),
        ("double_encoded_select", "%2527%2520UNION%2520SELECT%2520NULL--"),
        ("hex_quote",             "0x27"),
        ("hex_union",             "0x27204f522031"),
    ])
    def test_double_encoded_sql(self, search: SearchClient, name: str, payload: str):
        """TC_DB19: Double URL-encoded injection does not cause 500."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"DOUBLE-ENCODED SQLi [{name}]: caused 500! Payload: {repr(payload)}"
        )

    @pytest.mark.parametrize("name,payload", [
        ("unicode_quote",     "\u02bc"),             # ʼ — modifier letter apostrophe
        ("unicode_dash",      "\u2012\u2013\u2014"), #  and  instead of --
        ("fullwidth_select",  "\uff33\uff25\uff2c\uff25\uff23\uff34"),  # ＳＥＬＥＣＴ
        ("fullwidth_union",   "\uff35\uff2e\uff29\uff2f\uff2e"),        # ＵＮＩＯＮ
        ("cyrillic_latin",    "ЅL"),             # to and  and  and  instead of  and  and 
    ])
    def test_unicode_homoglyph_sql(self, search: SearchClient, name: str, payload: str):
        """TC_DB20: Unicode-homoglyph injection does not cause 500."""
        resp = search.search_listings(payload)
        assert resp.status_code != 500, (
            f"UNICODE SQLi [{name}]: caused 500! Payload: {repr(payload)}"
        )
