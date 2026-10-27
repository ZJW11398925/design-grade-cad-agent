#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}${PYTHONPATH:+:}src"
python -m pytest -q "$@"
