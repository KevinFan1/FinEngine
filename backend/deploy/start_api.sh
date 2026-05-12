#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python virtualenv not found at ${PYTHON_BIN}. Run: bash deploy/install_backend.sh"
  exit 1
fi

cd "${BACKEND_DIR}"

mkdir -p logs logs/supervisor

export PYTHONPATH="${BACKEND_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

APP_HOST="${APP_HOST:-127.0.0.1}"
APP_PORT="${APP_PORT:-8000}"
APP_WORKERS="${APP_WORKERS:-1}"
APP_FORWARDED_ALLOW_IPS="${APP_FORWARDED_ALLOW_IPS:-*}"

exec "${PYTHON_BIN}" -m uvicorn app.main:app \
  --host "${APP_HOST}" \
  --port "${APP_PORT}" \
  --workers "${APP_WORKERS}" \
  --proxy-headers \
  --forwarded-allow-ips "${APP_FORWARDED_ALLOW_IPS}"
