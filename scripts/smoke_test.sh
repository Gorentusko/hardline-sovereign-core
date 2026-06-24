#!/usr/bin/env bash
# Smoke test for a running Hardline Sovereign Core instance.
#
# Usage:
#   ./scripts/smoke_test.sh [base_url]
#
# Default base_url is http://localhost:8099
# Requires: curl, python3 (for JSON parsing/pretty checks)
#
# This script only talks to the local instance you point it at. It makes
# no external network calls and performs no destructive actions beyond
# creating one demo task and running it (the same as clicking the demo
# buttons on the dashboard).

set -euo pipefail

BASE_URL="${1:-http://localhost:8099}"
PASS=0
FAIL=0

check() {
  local description="$1"
  local method="$2"
  local path="$3"
  local expect_field="$4"

  echo "-> ${description} (${method} ${path})"
  local response
  if [ "$method" = "POST" ]; then
    response=$(curl -s -X POST "${BASE_URL}${path}")
  else
    response=$(curl -s "${BASE_URL}${path}")
  fi

  if echo "$response" | python3 -c "import sys, json; json.load(sys.stdin)" >/dev/null 2>&1; then
    if [ -n "$expect_field" ] && ! echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
field = '$expect_field'
parts = field.split('.')
cur = data
for p in parts:
    cur = cur[p]
" >/dev/null 2>&1; then
      echo "   FAIL: expected field '$expect_field' not found in response"
      echo "   response: $response"
      FAIL=$((FAIL + 1))
    else
      echo "   OK"
      PASS=$((PASS + 1))
    fi
  else
    echo "   FAIL: response was not valid JSON"
    echo "   response: $response"
    FAIL=$((FAIL + 1))
  fi
  echo "$response"
}

echo "Hardline Sovereign Core smoke test against ${BASE_URL}"
echo "========================================================"

check "Health check" GET "/health" "status"
check "Readiness check" GET "/ready" "ready"
check "Stats" GET "/api/stats" "ledger.valid"
check "Seed demo task" POST "/api/demo/seed" "task_id"

echo "-> Find newest task and run it"
TASK_ID=$(curl -s "${BASE_URL}/api/tasks" | python3 -c "import sys, json; print(json.load(sys.stdin)['tasks'][0]['id'])")
if [ -n "$TASK_ID" ]; then
  RUN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/tasks/${TASK_ID}/run")
  echo "$RUN_RESPONSE"
  if echo "$RUN_RESPONSE" | python3 -c "import sys, json; d = json.load(sys.stdin); assert d['status'] == 'success'" >/dev/null 2>&1; then
    echo "   OK"
    PASS=$((PASS + 1))
  else
    echo "   FAIL: run did not report success"
    FAIL=$((FAIL + 1))
  fi
else
  echo "   FAIL: no task id found to run"
  FAIL=$((FAIL + 1))
fi

check "Verify ledger" GET "/api/ledger/verify" "valid"

echo "========================================================"
echo "Smoke test complete: ${PASS} passed, ${FAIL} failed"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
