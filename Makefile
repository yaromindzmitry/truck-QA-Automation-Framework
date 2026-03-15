# ══════════════════════════════════════════════════════════════════════════════
#  truck1.eu QA — Makefile
#  Usage: make <target> [LOCALE=de] [LEVEL=normal]
# ══════════════════════════════════════════════════════════════════════════════

LOCALE   ?= en
LEVEL    ?= light
HOST     ?= https://www.truck1.eu
REPORTS  := reports
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)

.DEFAULT_GOAL := help

# ── Colors ────────────────────────────────────────────────────────────────────
BOLD  := \033[1m
GREEN := \033[32m
CYAN  := \033[36m
RESET := \033[0m

# ─────────────────────────────────────────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: install
install:  ## Install dependencies (pip + playwright)
	pip install -r requirements.txt
	playwright install chromium

.PHONY: install-k6
install-k6:  ## Install k6 (macOS)
	brew install k6

# ─────────────────────────────────────────────────────────────────────────────
#  UNIT / API TESTS (no browser, fast ~1–2 min)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: api
api:  ## Run API tests (locale=$(LOCALE))
	@printf "$(BOLD)$(CYAN)▶ API tests [$(LOCALE)]$(RESET)\n"
	pytest api/tests/ --locale=$(LOCALE) -m "api" -v

.PHONY: locale-smoke
locale-smoke:  ## Smoke for all locales (no browser)
	@printf "$(BOLD)$(CYAN)▶ Locale smoke — Tier1 + Tier2 + Cross$(RESET)\n"
	pytest tests/test_locale_smoke.py -v \
	  --html=$(REPORTS)/locale_smoke_$(TIMESTAMP).html

.PHONY: locale-tier1
locale-tier1:  ## Smoke for EN/DE/PL only
	pytest tests/test_locale_smoke.py -m "tier1" -v

.PHONY: locale-tier2
locale-tier2:  ## Smoke for secondary locales (LT/LV/EE/...)
	pytest tests/test_locale_smoke.py -m "tier2" -v

# ─────────────────────────────────────────────────────────────────────────────
#  UI TESTS (Playwright, ~5–15 min)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: smoke
smoke:  ## UI smoke tests [LOCALE=en]
	@printf "$(BOLD)$(CYAN)▶ UI Smoke [$(LOCALE)]$(RESET)\n"
	pytest tests/ --locale=$(LOCALE) -m "smoke" \
	  --browser=chromium \
	  --html=$(REPORTS)/smoke_$(LOCALE)_$(TIMESTAMP).html

.PHONY: full
full:  ## Full UI test suite [LOCALE=en]
	@printf "$(BOLD)$(CYAN)▶ Full UI suite [$(LOCALE)]$(RESET)\n"
	pytest tests/ --locale=$(LOCALE) \
	  --browser=chromium \
	  --html=$(REPORTS)/full_$(LOCALE)_$(TIMESTAMP).html

.PHONY: smoke-headed
smoke-headed:  ## UI smoke in visible browser (bypass CF)
	pytest tests/ --locale=$(LOCALE) -m "smoke" \
	  --browser=chromium \
	  --headed \
	  --slowmo=800 \
	  --html=$(REPORTS)/smoke_headed_$(LOCALE)_$(TIMESTAMP).html

.PHONY: security
security:  ## Security tests
	@printf "$(BOLD)$(CYAN)▶ Security tests$(RESET)\n"
	pytest tests/test_security_ui.py --locale=$(LOCALE) \
	  --browser=chromium \
	  --html=$(REPORTS)/security_$(TIMESTAMP).html

.PHONY: user-flows
user-flows:  ## User flow tests
	pytest tests/test_user_flows.py --locale=$(LOCALE) \
	  --browser=chromium --headed --slowmo=500 \
	  --html=$(REPORTS)/userflows_$(LOCALE)_$(TIMESTAMP).html

# ─────────────────────────────────────────────────────────────────────────────
#  PARALLEL RUN (all locales at once)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: smoke-all-locales
smoke-all-locales:  ## Smoke for EN+DE+PL in parallel
	@printf "$(BOLD)$(CYAN)▶ Smoke — EN + DE + PL$(RESET)\n"
	@$(MAKE) smoke LOCALE=en &
	@$(MAKE) smoke LOCALE=de &
	@$(MAKE) smoke LOCALE=pl &
	@wait
	@printf "$(GREEN)✅ All locale smoke tests done$(RESET)\n"

# ─────────────────────────────────────────────────────────────────────────────
#  LOAD TESTING (Locust)
# ─────────────────────────────────────────────────────────────────────────────

# Load level parameters
load-params-smoke  := -u 3   -r 1  -t 30s
load-params-light  := -u 10  -r 2  -t 2m
load-params-normal := -u 25  -r 5  -t 5m
load-params-stress := -u 50  -r 5  -t 10m

.PHONY: load-smoke
load-smoke:  ## Load smoke (3 VU, 30s)
	@printf "$(BOLD)$(CYAN)▶ Load test: SMOKE$(RESET)\n"
	locust -f load_tests/locustfile.py --headless \
	  $(load-params-smoke) --host=$(HOST) \
	  --html=$(REPORTS)/load_smoke_$(TIMESTAMP).html

.PHONY: load-light
load-light:  ## Load light (10 VU, 2 min)
	@printf "$(BOLD)$(CYAN)▶ Load test: LIGHT$(RESET)\n"
	locust -f load_tests/locustfile.py --headless \
	  $(load-params-light) --host=$(HOST) \
	  --html=$(REPORTS)/load_light_$(TIMESTAMP).html

.PHONY: load-normal
load-normal:  ## Load normal (25 VU, 5 min)
	@printf "$(BOLD)$(CYAN)▶ Load test: NORMAL$(RESET)\n"
	locust -f load_tests/locustfile.py --headless \
	  $(load-params-normal) --host=$(HOST) \
	  --html=$(REPORTS)/load_normal_$(TIMESTAMP).html

.PHONY: load-stress
load-stress:  ## Load stress (50 VU, 10 min) ⚠️ coordinate with team
	@printf "$(BOLD)$(CYAN)▶ Load test: STRESS ⚠️$(RESET)\n"
	@printf "$(BOLD)Run only with development team approval!$(RESET)\n"
	@read -p "Confirm stress test run [y/N]: " confirm && [ "$$confirm" = "y" ]
	locust -f load_tests/locustfile.py --headless \
	  $(load-params-stress) --host=$(HOST) \
	  --html=$(REPORTS)/load_stress_$(TIMESTAMP).html \
	  --csv=$(REPORTS)/load_stress_$(TIMESTAMP)

.PHONY: load-ui
load-ui:  ## Load with Web UI (http://localhost:8089)
	locust -f load_tests/locustfile.py --host=$(HOST)

.PHONY: load-spike
load-spike:  ## Spike test (0→50 VU sharp) — find degradation point
	@printf "$(BOLD)$(CYAN)▶ Spike test$(RESET)\n"
	locust -f load_tests/scenarios_advanced.py SpikeTest --headless \
	  -u 50 -r 25 -t 3m --host=$(HOST) \
	  --html=$(REPORTS)/load_spike_$(TIMESTAMP).html

.PHONY: load-soak
load-soak:  ## Soak test (10 VU, 30 min) — find degradation over time
	@printf "$(BOLD)$(CYAN)▶ Soak test (30 min)$(RESET)\n"
	locust -f load_tests/scenarios_advanced.py SoakTest --headless \
	  -u 10 -r 1 -t 30m --host=$(HOST) \
	  --html=$(REPORTS)/load_soak_$(TIMESTAMP).html

.PHONY: load-validate
load-validate:  ## ContentValidator — verify real content under load
	locust -f load_tests/scenarios_advanced.py ContentValidator --headless \
	  -u 5 -r 1 -t 1m --host=$(HOST) \
	  --html=$(REPORTS)/load_validate_$(TIMESTAMP).html

# ─────────────────────────────────────────────────────────────────────────────
#  k6 tests (Locust alternative)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: k6-smoke
k6-smoke:  ## k6 smoke (3 VU, 30s)
	k6 run load_tests/k6_smoke.js

.PHONY: k6-light
k6-light:  ## k6 light (10 VU, 2 min)
	k6 run --env LEVEL=light load_tests/k6_smoke.js

.PHONY: k6-normal
k6-normal:  ## k6 normal (25 VU, 5 min) with JSON report
	mkdir -p $(REPORTS)
	k6 run --env LEVEL=normal \
	  --out json=$(REPORTS)/k6_results_$(TIMESTAMP).json \
	  load_tests/k6_smoke.js

# ─────────────────────────────────────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: reports-clean
reports-clean:  ## Delete HTML reports older than 7 days
	find $(REPORTS) -name "*.html" -mtime +7 -delete
	find $(REPORTS) -name "*.json" -mtime +7 -delete
	@printf "$(GREEN)✅ Old reports cleaned$(RESET)\n"

.PHONY: last-report
last-report:  ## Open latest HTML report
	@open $(shell ls -t $(REPORTS)/*.html | head -1) 2>/dev/null || \
	  xdg-open $(shell ls -t $(REPORTS)/*.html | head -1)

.PHONY: help
help:  ## Show command list
	@printf "\n$(BOLD)truck1.eu QA — available commands:$(RESET)\n\n"
	@printf "$(CYAN)%-25s$(RESET) %s\n" "Variables:" ""
	@printf "  %-23s %s\n" "LOCALE=en|de|pl|..." "Locale for tests (default: en)"
	@printf "  %-23s %s\n" "HOST=https://..."    "Host (default: truck1.eu)"
	@printf "\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)  make %-22s$(RESET) %s\n", $$1, $$2}'
	@printf "\n$(BOLD)Examples:$(RESET)\n"
	@printf "  make smoke LOCALE=de\n"
	@printf "  make load-normal\n"
	@printf "  make locale-smoke\n"
	@printf "  make smoke-headed LOCALE=pl\n\n"
