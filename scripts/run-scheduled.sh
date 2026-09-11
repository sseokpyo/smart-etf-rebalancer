#!/usr/bin/env bash
set -euo pipefail

# Called by systemd. The default is a dry run; a live order needs both this
# explicit mode and DRY_RUN=false in the private .env file.
APP_DIR="${APP_DIR:-/opt/smart-etf-rebalancer}"
VENV_PYTHON="${VENV_PYTHON:-$APP_DIR/.venv/bin/python}"
RUN_MODE="${RUN_MODE:-dry-run}"

cd "$APP_DIR"

if [[ "$RUN_MODE" == "dry-run" ]]; then
  exec "$VENV_PYTHON" -m invest_bot run
fi

if [[ "$RUN_MODE" == "live" && "${DRY_RUN:-true}" == "false" ]]; then
  exec "$VENV_PYTHON" -m invest_bot run --live
fi

echo "Refusing scheduled execution: RUN_MODE must be dry-run, or live with DRY_RUN=false." >&2
exit 2
