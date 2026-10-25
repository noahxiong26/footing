#!/usr/bin/env bash
# Record the five additional demo towns using the existing CLI/pipeline.
# Inherits optional keys from the normal environment; never opens a secret file.
# Usage: scripts/record_demo_towns.sh [roanoke richmond ...] [--resume]
# See docs/TOWN_CAPTURE.md. Existing captures are refused unless --resume is explicit.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${FOOTING_PYTHON:-python}"
if [[ -z "${FOOTING_PYTHON:-}" && -x .venv/Scripts/python.exe ]]; then
  PYTHON=.venv/Scripts/python.exe
elif [[ -z "${FOOTING_PYTHON:-}" && -x .venv/bin/python ]]; then
  PYTHON=.venv/bin/python
fi
exec "$PYTHON" scripts/record_towns.py "$@"
