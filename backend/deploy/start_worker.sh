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
  CELERY_LOG_LEVEL \
  CELERY_POOL \
  CELERY_HOSTNAME \
  CELERY_QUEUES \
  CELERY_CONCURRENCY

CELERY_LOG_LEVEL="${CELERY_LOG_LEVEL:-INFO}"
CELERY_POOL="${CELERY_POOL:-prefork}"
CELERY_HOSTNAME="${CELERY_HOSTNAME:-finengine@%h}"

CELERY_ARGS=(
  -m celery
  -A app.tasks.celery_app:celery_app
  worker
  --loglevel "${CELERY_LOG_LEVEL}"
  --pool "${CELERY_POOL}"
  --hostname "${CELERY_HOSTNAME}"
)

if [[ -n "${CELERY_QUEUES:-}" ]]; then
  CELERY_ARGS+=(--queues "${CELERY_QUEUES}")
fi

if [[ -n "${CELERY_CONCURRENCY:-}" ]]; then
  CELERY_ARGS+=(--concurrency "${CELERY_CONCURRENCY}")
fi

exec "${PYTHON_BIN}" "${CELERY_ARGS[@]}"
