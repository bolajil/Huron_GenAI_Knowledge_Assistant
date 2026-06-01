#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Blue/Green Deployment — Test Traffic Hook
# ═══════════════════════════════════════════════════════════════════════════════
# This script runs after test traffic is routed to the green environment
# Use it to validate the deployment before switching production traffic
# ═══════════════════════════════════════════════════════════════════════════════

set -e

echo "🔍 Running deployment validation tests..."

# Get the test ALB endpoint (port 8080)
TEST_ENDPOINT="${TEST_ENDPOINT:-http://localhost:8080}"

# Health check
echo "Checking health endpoint..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${TEST_ENDPOINT}/health" || echo "000")

if [ "$HEALTH_RESPONSE" != "200" ]; then
    echo "❌ Health check failed with status: $HEALTH_RESPONSE"
    exit 1
fi
echo "✅ Health check passed"

# API docs check
echo "Checking API docs endpoint..."
DOCS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${TEST_ENDPOINT}/docs" || echo "000")

if [ "$DOCS_RESPONSE" != "200" ]; then
    echo "❌ API docs check failed with status: $DOCS_RESPONSE"
    exit 1
fi
echo "✅ API docs accessible"

# Authentication endpoint check
echo "Checking auth endpoint..."
AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${TEST_ENDPOINT}/api/v1/auth/login" -X POST -H "Content-Type: application/json" -d '{}' || echo "000")

if [ "$AUTH_RESPONSE" == "000" ]; then
    echo "❌ Auth endpoint not reachable"
    exit 1
fi
echo "✅ Auth endpoint responding (status: $AUTH_RESPONSE)"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ All deployment validation tests passed!"
echo "═══════════════════════════════════════════════════════════════"
exit 0
