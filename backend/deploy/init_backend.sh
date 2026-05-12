#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install uv first: https://docs.astral.sh/uv/"
  exit 1
fi

cd "${BACKEND_DIR}"

RUN_SEED_ALL=0

if [[ "${1:-}" == "--with-seed" ]]; then
  RUN_SEED_ALL=1
fi

uv run migrate-upgrade

if [[ "${RUN_SEED_ALL}" == "1" ]]; then
  uv run seed-all
fi

echo "Backend initialization complete."
