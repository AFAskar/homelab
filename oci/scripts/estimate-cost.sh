#!/usr/bin/env bash
set -euo pipefail
# Explicit assumptions. No unverified free allowance is deducted.
exec python3 "$(dirname "$0")/estimate_cost.py" "$@"
