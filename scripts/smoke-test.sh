#!/usr/bin/env bash
# checks the app the same way a user would. usage: smoke-test.sh <base url> [expected version]
set -euo pipefail

BASE_URL=${1:-http://even-odd.localhost:8080}
EXPECTED_VERSION=${2:-}
FAILED=0
BODY_FILE=$(mktemp)
trap 'rm -f "$BODY_FILE"' EXIT

check() {
  local name=$1 url=$2 want_status=$3 want_body=$4
  local status body
  status=$(curl -s -o "$BODY_FILE" -w '%{http_code}' "$url") || true
  body=$(cat "$BODY_FILE")

  if [ "$status" = "$want_status" ] && echo "$body" | grep -q "$want_body"; then
    echo "PASS  $name -> $status $body"
  else
    echo "FAIL  $name -> got $status $body, wanted $want_status containing $want_body"
    FAILED=1
  fi
}

check "even number"   "$BASE_URL/check?number=10"  200 '"even":true'
check "odd number"    "$BASE_URL/check?number=7"   200 '"even":false'
check "negative"      "$BASE_URL/check?number=-4"  200 '"even":true'
check "not a number"  "$BASE_URL/check?number=abc" 400 'error'
check "missing"       "$BASE_URL/check"            400 'error'

if [ -n "$EXPECTED_VERSION" ]; then
  check "version" "$BASE_URL/version" 200 "\"version\":\"$EXPECTED_VERSION\""
else
  check "version" "$BASE_URL/version" 200 'version'
fi

if [ "$FAILED" = "1" ]; then
  echo "smoke test failed"
  exit 1
fi
echo "smoke test passed"
