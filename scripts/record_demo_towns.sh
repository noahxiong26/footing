#!/usr/bin/env bash
# Record a replayable fixture set for each demo town (run on a laptop with normal internet).
# Keys are read from .env if present; sources without a key are listed as "not captured".
# Usage: scripts/record_demo_towns.sh            (writes fixtures/<town>_<YYYY-MM-DD>/)
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
DAY=$(date +%F)
record() {  # slug lat lon label
  echo "== $4"
  python -m footing record --lat "$2" --lon "$3" --label "$4" --out "fixtures/$1_${DAY}"
}
record christiansburg 37.1299 -80.4089 "Downtown Christiansburg, VA"
record blacksburg     37.2296 -80.4139 "Downtown Blacksburg, VA"
record radford        37.1318 -80.5764 "Downtown Radford, VA"
record roanoke        37.2710 -79.9414 "Downtown Roanoke, VA"
echo
echo "Done. Check each fixtures/*_${DAY}/MANIFEST.json 'not_captured' list before the demo."
echo "If a town was recorded before, replay uses the newest set for that tile."
