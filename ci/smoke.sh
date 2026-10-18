#!/usr/bin/env bash
# ci/smoke.sh: compose smoke test of the running stack (docs/design/foundations.md).
# Builds the API image, starts api + db, checks readiness and the error shape,
# stops the database and checks the 503, then tears everything down (volume too).
# Local run: make smoke. Needs docker compose, curl and jq; uses ports 8000 and 5432.
set -euo pipefail

API=${API_URL:-http://localhost:8000/api/v1}
PROJECT=${COMPOSE_PROJECT_NAME:-devorchestrator-smoke}
compose() { docker compose -p "$PROJECT" "$@"; }

fail() { echo "::error::smoke: $*" >&2; exit 1; }

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "--- compose logs ---" >&2
    compose logs --no-color >&2 || true
  fi
  compose down --volumes --remove-orphans || true
  exit "$status"
}
trap cleanup EXIT

# 1. build and start; --wait returns once db and api are healthy
compose up --detach --build --wait --wait-timeout 120

# 2. readiness: 200, status ok, database ok, a version (with the short SHA when set)
body=$(curl --silent --show-error --fail --max-time 10 "$API/health/ready") \
  || fail "GET /health/ready did not return 200"
echo "ready: $body"
jq -e '.status == "ok" and .checks.database == "ok" and (.version | type == "string")' \
  <<<"$body" >/dev/null || fail "unexpected readiness body: $body"
if [ -n "${GIT_SHA:-}" ]; then
  jq -e --arg sha "${GIT_SHA:0:7}" '.version | endswith("+" + $sha)' <<<"$body" >/dev/null \
    || fail "version does not carry GIT_SHA ${GIT_SHA:0:7}: $body"
fi

# 3. unknown path: 404 as application/problem+json
read -r code type < <(curl --silent --output /dev/null --max-time 10 \
  --write-out '%{http_code} %{content_type}\n' "$API/smoke-unknown-path")
echo "unknown path: $code $type"
[ "$code" = 404 ] || fail "unknown path returned $code, expected 404"
[[ "$type" == application/problem+json* ]] || fail "unknown path content type: $type"

# 4. database down: 503 with status down and database failed, within 3 s
compose stop db
tmp=$(mktemp)
code=$(curl --silent --output "$tmp" --max-time 3 --write-out '%{http_code}' \
  "$API/health/ready") || fail "GET /health/ready with db stopped took more than 3 s"
body=$(cat "$tmp"); rm -f "$tmp"
echo "db stopped: $code $body"
[ "$code" = 503 ] || fail "readiness with db stopped returned $code, expected 503"
jq -e '.status == "down" and .checks.database == "failed"' <<<"$body" >/dev/null \
  || fail "unexpected readiness body with db stopped: $body"

echo "smoke: ok"
