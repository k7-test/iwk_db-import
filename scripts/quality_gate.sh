#!/usr/bin/env bash

# Quality Gate Script for Excel -> PostgreSQL Import CLI (T039)
# 
# This script ensures all code quality standards are met before code changes
# are accepted. It runs four critical checks:
#
# 1. RUFF: Code linting and formatting checks
# 2. MYPY: Static type checking for type safety
# 3. PYTEST: Unit/integration tests with ≥90% coverage requirement
# 4. PERF_SMOKE: Performance smoke test ensuring execution under threshold
#
# Usage: ./scripts/quality_gate.sh
# Exit codes: 0 = all checks passed, 1 = one or more checks failed
#
# Requirements:
# - Python 3.11+
# - All dev dependencies installed: pip install -e .[dev]
# - Type stubs installed: pip install types-tqdm pandas-stubs types-jsonschema

set -e  # Exit on any error
set -u  # Exit on undefined variables
set -o pipefail  # Exit on pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0
RESULTS=()

# Helper function to run a check and track results
run_check() {
    local name="$1"
    local description="$2"
    shift 2
    
    echo -e "${BLUE}Running ${name}: ${description}${NC}"
    
    if "$@"; then
        echo -e "${GREEN}✓ ${name} PASSED${NC}"
        RESULTS+=("✓ ${name}")
    else
        echo -e "${RED}✗ ${name} FAILED${NC}"
        RESULTS+=("✗ ${name}")
        OVERALL_STATUS=1
    fi
    echo ""
}

# Helper function for final summary
print_summary() {
    echo "=========================================="
    echo "           QUALITY GATE SUMMARY"
    echo "=========================================="
    
    for result in "${RESULTS[@]}"; do
        if [[ $result == ✓* ]]; then
            echo -e "${GREEN}${result}${NC}"
        else
            echo -e "${RED}${result}${NC}"
        fi
    done
    
    echo "=========================================="
    if [ $OVERALL_STATUS -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL QUALITY CHECKS PASSED${NC}"
    else
        echo -e "${RED}❌ QUALITY GATE FAILED${NC}"
        echo "Please fix the failing checks before proceeding."
    fi
    echo "=========================================="
}

# Change to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "Excel -> PostgreSQL Import CLI - Quality Gate"
echo "=============================================="
echo "Repository: $(pwd)"
echo "Timestamp: $(date)"
echo ""

# 1. Ruff linting check
run_check "RUFF" "Code linting and formatting" \
    python -m ruff check src tests

# 2. MyPy type checking
run_check "MYPY" "Static type checking" \
    python -m mypy src

# 3. Pytest with coverage requirement (≥90%)
run_check "PYTEST" "Unit/integration tests with ≥90% coverage" \
    python -m pytest --cov=src --cov-fail-under=90 --quiet

# 4. Performance smoke test (runs as part of pytest but specifically check it)
run_check "PERF_SMOKE" "Performance smoke test under threshold" \
    python -m pytest tests/perf/test_perf_smoke.py -v --tb=short --no-cov

# Print final summary
print_summary

# Exit with appropriate code
exit $OVERALL_STATUS