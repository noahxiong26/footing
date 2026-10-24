#!/usr/bin/env bash
# Install the package the way the Dockerfile does (non-editable, into a fresh venv), start it
# in replay mode from another directory, and check the endpoints the app needs.
# Catches missing dependencies and package-data that the editable dev install hides.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
PORT="${PORT:-8790}"
python3 -m venv "$TMP/venv"
"$TMP/venv/bin/pip" install -q "$REPO[api]"
cd "$TMP"
FOOTING_MODE=replay FOOTING_FIXTURES="$REPO/fixtures" "$TMP/venv/bin/uvicorn" footing.api:app --port "$PORT" > "$TMP/server.log" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true; rm -rf "$TMP"' EXIT
for _ in $(seq 1 30); do curl -sf "localhost:$PORT/api/healthz" > /dev/null && break; sleep 0.5; done
Q="lat=37.1299&lon=-80.4089"
fail=0
for path in "/" "/app.js" "/sw.js" "/api/healthz" "/api/receipt?$Q" "/api/plan?$Q" "/api/tonight?$Q" \
            "/api/pocket-card.svg?$Q" "/api/factors" "/api/sources" "/api/compare?points=37.1299,-80.4089;37.2710,-79.9414"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "localhost:$PORT$path")
  printf "%s %s\n" "$code" "$path"
  [ "$code" = "200" ] || fail=1
done
score=$(curl -s "localhost:$PORT/api/receipt?$Q" | python3 -c "import json,sys; print(json.load(sys.stdin)['settle_score'])")
echo "settle_score (replay, Christiansburg) = $score"
[ "$score" != "None" ] || { echo "replay fixtures not found by the installed package"; fail=1; }
[ $fail = 0 ] || { tail -20 "$TMP/server.log"; exit 1; }
echo "clean install OK"
