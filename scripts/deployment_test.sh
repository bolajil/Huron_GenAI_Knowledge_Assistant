#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Huron GenAI Knowledge Assistant — Deployment Verification Script (Bash)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   ./scripts/deployment_test.sh https://your-deployment-url.com
#   ./scripts/deployment_test.sh https://huron-backend.azurecontainerapps.io
#
# Prerequisites:
#   - curl
#   - jq (optional, for JSON parsing)
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${1:-http://localhost:8004}"
USERNAME="${2:-root}"
PASSWORD="${3:-HuronRoot2026!}"
TIMEOUT=30

# Counters
PASSED=0
FAILED=0

# ─── Helper Functions ────────────────────────────────────────────────────────

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_test() {
    local name="$1"
    local passed="$2"
    local duration="$3"
    local detail="$4"
    
    if [ "$passed" = "true" ]; then
        echo -e "  ${GREEN}✓ PASS${NC} $name ${duration:+(${duration}ms)}${detail:+ - $detail}"
        ((PASSED++))
    else
        echo -e "  ${RED}✗ FAIL${NC} $name ${duration:+(${duration}ms)}${detail:+ - $detail}"
        ((FAILED++))
    fi
}

# ─── Test Functions ──────────────────────────────────────────────────────────

test_health() {
    local start=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$BASE_URL/health" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "200" ] && echo "$body" | grep -q '"status":"healthy"'; then
        print_test "GET /health returns healthy" "true" "$duration"
        return 0
    else
        print_test "GET /health returns healthy" "false" "$duration" "HTTP $http_code"
        return 1
    fi
}

test_docs() {
    local start=$(date +%s%N)
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$BASE_URL/docs" 2>/dev/null || echo "000")
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "200" ]; then
        print_test "Swagger UI accessible" "true" "$duration"
        return 0
    else
        print_test "Swagger UI accessible" "false" "$duration" "HTTP $http_code"
        return 1
    fi
}

test_openapi() {
    local start=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT "$BASE_URL/openapi.json" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "200" ] && echo "$body" | grep -q '"paths"'; then
        local path_count=$(echo "$body" | grep -o '"/api' | wc -l)
        print_test "OpenAPI schema valid" "true" "$duration" "$path_count endpoints"
        return 0
    else
        print_test "OpenAPI schema valid" "false" "$duration" "HTTP $http_code"
        return 1
    fi
}

test_unauthorized() {
    local start=$(date +%s%N)
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$BASE_URL/api/v1/auth/me" 2>/dev/null || echo "000")
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
        print_test "Protected endpoints reject unauthenticated" "true" "$duration"
        return 0
    else
        print_test "Protected endpoints reject unauthenticated" "false" "$duration" "Expected 401/403, got $http_code"
        return 1
    fi
}

test_login() {
    local start=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "200" ]; then
        # Extract token (simple grep, works without jq)
        TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
        if [ -n "$TOKEN" ]; then
            print_test "Login as $USERNAME" "true" "$duration"
            return 0
        fi
    fi
    
    print_test "Login as $USERNAME" "false" "$duration" "HTTP $http_code"
    TOKEN=""
    return 1
}

test_auth_me() {
    if [ -z "$TOKEN" ]; then
        print_test "GET /api/v1/auth/me" "false" "" "No token"
        return 1
    fi
    
    local start=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -H "Authorization: Bearer $TOKEN" \
        "$BASE_URL/api/v1/auth/me" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "200" ]; then
        local role=$(echo "$body" | grep -o '"role":"[^"]*' | cut -d'"' -f4)
        print_test "GET /api/v1/auth/me" "true" "$duration" "role=$role"
        return 0
    else
        print_test "GET /api/v1/auth/me" "false" "$duration" "HTTP $http_code"
        return 1
    fi
}

test_departments() {
    if [ -z "$TOKEN" ]; then
        print_test "GET /api/v1/root/departments" "false" "" "No token"
        return 1
    fi
    
    local start=$(date +%s%N)
    local response=$(curl -s -w "\n%{http_code}" --max-time $TIMEOUT \
        -H "Authorization: Bearer $TOKEN" \
        "$BASE_URL/api/v1/root/departments" 2>/dev/null || echo -e "\n000")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))
    
    if [ "$http_code" = "200" ]; then
        local dept_count=$(echo "$body" | grep -o '"code"' | wc -l)
        print_test "GET /api/v1/root/departments" "true" "$duration" "$dept_count departments"
        return 0
    else
        print_test "GET /api/v1/root/departments" "false" "$duration" "HTTP $http_code"
        return 1
    fi
}

# ─── Main ────────────────────────────────────────────────────────────────────

echo ""
print_header "Huron GenAI Deployment Verification"

echo "  Target URL: ${BOLD}$BASE_URL${NC}"
echo "  Timestamp:  $(date -Iseconds)"

# Run tests
print_header "1. Health Check"
test_health || true

print_header "2. API Documentation"
test_docs || true
test_openapi || true

print_header "3. Authentication"
test_unauthorized || true
test_login || true

print_header "4. Authorized API Access"
test_auth_me || true
test_departments || true

# Summary
print_header "Summary"

TOTAL=$((PASSED + FAILED))

if [ "$FAILED" -eq 0 ]; then
    echo -e "  ${GREEN}${BOLD}All $TOTAL tests passed!${NC}"
    echo ""
    echo -e "  ${GREEN}✓ Deployment is healthy and operational.${NC}"
    exit 0
else
    PASS_RATE=$((PASSED * 100 / TOTAL))
    echo -e "  ${RED}Passed: $PASSED/$TOTAL ($PASS_RATE%)${NC}"
    echo -e "  ${RED}Failed: $FAILED${NC}"
    echo ""
    echo -e "  ${RED}✗ Deployment has issues. Check failed tests above.${NC}"
    exit 1
fi
