#!/usr/bin/env bash
# =============================================================================
#  push_to_github.sh — Push truck1.eu QA Framework to GitHub
#
#  Run from the truck1_qa project root:
#    bash scripts/push_to_github.sh
# =============================================================================

set -e

REPO_URL="https://github.com/yaromindzmitry/truck-QA-Automation-Framework.git"

echo "=== truck1.eu QA Framework → GitHub push ==="
echo ""

# Remove any stale git lock or partial git init left by the agent
if [ -f .git/index.lock ]; then
  echo "⚠  Removing stale .git/index.lock ..."
  rm -f .git/index.lock
fi

# If .git already exists from a partial init, remove and re-init cleanly
if [ -d .git ]; then
  echo "🗑  Removing existing (incomplete) .git directory ..."
  rm -rf .git
fi

echo "📁  Initializing fresh git repository ..."
git init
git config user.email "mpc.gdansk.poland@gmail.com"
git config user.name  "yaromindzmitry"

echo "📦  Staging all files ..."
git add .

echo "💾  Creating initial commit ..."
git commit -m "Initial commit: truck1.eu QA Automation Framework

Complete pytest + Playwright black-box QA framework for truck1.eu:
- 157 UI tests across 10 modules (Browser/Search/Filter/Leasing flows)
- 6 API test modules using requests.Session (no browser overhead)
- Multi-locale testing: EN/DE/PL full suite + 8 additional locales smoke
- Cloudflare bot protection handling (CF-guard pattern with pytest.skip)
- Load testing: Locust (4 user classes + 5 advanced scenarios) + k6 (4 levels)
- GitHub Actions CI/CD: 7 jobs (lint→api→locale-smoke→ui-smoke→security→load→notify)
- Page Object Model with CSS fallback selectors
- Security coverage: Clickjacking (SEC-BUG-001) + Tabnapping (SEC-BUG-002)
- Code quality: Ruff linting + pre-commit hooks (detect-secrets, no-commit-to-main)
- Spike test results: 6848 requests, 0 errors, P95=230ms"

echo "🔗  Adding remote origin ..."
git branch -M main
git remote add origin "$REPO_URL"

echo "🚀  Pushing to GitHub ..."
git push -u origin main

echo ""
echo "✅  Done! Project is live at:"
echo "    https://github.com/yaromindzmitry/truck-QA-Automation-Framework"
