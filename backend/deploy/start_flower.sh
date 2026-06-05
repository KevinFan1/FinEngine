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

source "${SCRIPT_DIR}/load_deploy_env.sh"
load_deploy_env "${BACKEND_DIR}/.env" \
  FLOWER_HOST \
  FLOWER_PORT \
  FLOWER_BASIC_AUTH \
  FLOWER_URL_PREFIX

FLOWER_HOST="${FLOWER_HOST:-127.0.0.1}"
FLOWER_PORT="${FLOWER_PORT:-5555}"
FLOWER_URL_PREFIX="${FLOWER_URL_PREFIX:-}"

FLOWER_ARGS=(
  -m celery
  -A app.tasks.celery_app:celery_app
  flower
  --address="${FLOWER_HOST}"
  --port="${FLOWER_PORT}"
)

if [[ -n "${FLOWER_BASIC_AUTH:-}" ]]; then
  FLOWER_ARGS+=(--basic-auth="${FLOWER_BASIC_AUTH}")
fi

if [[ -n "${FLOWER_URL_PREFIX}" ]]; then
  FLOWER_ARGS+=(--url_prefix="${FLOWER_URL_PREFIX}")
fi

exec "${PYTHON_BIN}" "${FLOWER_ARGS[@]}"
