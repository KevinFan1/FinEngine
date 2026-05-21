#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="$(cd "${BACKEND_DIR}/.." && pwd)"
FRONTEND_DIR="${PROJECT_DIR}/frontend"
LOCK_DIR="${BACKEND_DIR}/tmp/deploy-update.lock"

RUN_GIT_PULL=0
RUN_FRONTEND_BUILD=0
RUN_SEED_ALL=0
RESTART_SUPERVISOR=1
RUN_HEALTH_CHECK=1
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-}"
SUPERVISOR_GROUP="${SUPERVISOR_GROUP:-finengine:*}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${APP_PORT:-8000}/api/v1/health/detailed}"
HEALTH_RETRIES="${HEALTH_RETRIES:-20}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-2}"

usage() {
  cat <<'USAGE'
Usage: bash deploy/update_backend.sh [options]

Options:
  --git-pull              Pull latest code before installing dependencies.
  --branch <name>         Branch to pull. Defaults to current branch when --git-pull is used.
  --remote <name>         Git remote to pull from. Defaults to origin.
  --with-frontend-build   Run npm ci and npm run build in ../frontend.
  --with-seed             Run uv run seed-all after migrations.
  --no-restart            Do not restart supervisor services.
  --no-health-check       Do not call the detailed health endpoint after restart.
  -h, --help              Show this help.

Environment:
  SUPERVISOR_GROUP        Supervisor target. Default: finengine:*
  HEALTH_URL              Health URL. Default: http://127.0.0.1:${APP_PORT:-8000}/api/v1/health/detailed
  HEALTH_RETRIES          Health retry count. Default: 20
  HEALTH_INTERVAL_SECONDS Seconds between health checks. Default: 2
USAGE
}

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

run_step() {
  log "$*"
  "$@"
}

cleanup() {
  if [[ -d "${LOCK_DIR}" ]]; then
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
}

require_command() {
  local command_name="$1"
  command -v "${command_name}" >/dev/null 2>&1 || fail "${command_name} is required but was not found"
}

current_git_branch() {
  git -C "${PROJECT_DIR}" rev-parse --abbrev-ref HEAD
}

wait_for_health() {
  local attempt=1
  local response=""
  local normalized_response=""

  require_command curl

  while (( attempt <= HEALTH_RETRIES )); do
    if response="$(curl -fsS "${HEALTH_URL}")"; then
      normalized_response="$(printf '%s' "${response}" | tr -d '[:space:]')"
    else
      normalized_response=""
    fi

    if [[ "${normalized_response}" == *'"message":"healthy"'* ]] \
      && [[ "${normalized_response}" == *'"api":"ok"'* ]] \
      && [[ "${normalized_response}" == *'"database":"ok"'* ]] \
      && [[ "${normalized_response}" == *'"redis":"ok"'* ]]; then
      log "Health check passed: ${HEALTH_URL}"
      return 0
    fi

    log "Health check not ready (${attempt}/${HEALTH_RETRIES}); retrying in ${HEALTH_INTERVAL_SECONDS}s"
    sleep "${HEALTH_INTERVAL_SECONDS}"
    attempt=$((attempt + 1))
  done

  fail "Health check failed after ${HEALTH_RETRIES} attempts: ${HEALTH_URL}"
}

while (($#)); do
  case "$1" in
    --git-pull)
      RUN_GIT_PULL=1
      shift
      ;;
    --branch)
      [[ $# -ge 2 ]] || fail "--branch requires a value"
      GIT_BRANCH="$2"
      shift 2
      ;;
    --remote)
      [[ $# -ge 2 ]] || fail "--remote requires a value"
      GIT_REMOTE="$2"
      shift 2
      ;;
    --with-frontend-build)
      RUN_FRONTEND_BUILD=1
      shift
      ;;
    --with-seed)
      RUN_SEED_ALL=1
      shift
      ;;
    --no-restart)
      RESTART_SUPERVISOR=0
      shift
      ;;
    --no-health-check)
      RUN_HEALTH_CHECK=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

mkdir -p "${BACKEND_DIR}/tmp"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  fail "Another deploy update is already running: ${LOCK_DIR}"
fi
trap cleanup EXIT

require_command uv

if [[ "${RUN_GIT_PULL}" == "1" ]]; then
  require_command git
  if [[ -z "${GIT_BRANCH}" ]]; then
    GIT_BRANCH="$(current_git_branch)"
  fi
  run_step git -C "${PROJECT_DIR}" pull --ff-only "${GIT_REMOTE}" "${GIT_BRANCH}"
fi

run_step mkdir -p "${BACKEND_DIR}/logs" "${BACKEND_DIR}/logs/supervisor"

cd "${BACKEND_DIR}"

run_step uv sync --frozen
run_step uv run migrate-upgrade

if [[ "${RUN_SEED_ALL}" == "1" ]]; then
  run_step uv run seed-all
fi

run_step uv run python -m compileall app

if [[ "${RUN_FRONTEND_BUILD}" == "1" ]]; then
  [[ -d "${FRONTEND_DIR}" ]] || fail "Frontend directory not found: ${FRONTEND_DIR}"
  require_command npm
  run_step npm --prefix "${FRONTEND_DIR}" ci
  run_step npm --prefix "${FRONTEND_DIR}" run build
fi

if [[ "${RESTART_SUPERVISOR}" == "1" ]]; then
  require_command supervisorctl
  run_step supervisorctl restart "${SUPERVISOR_GROUP}"
fi

if [[ "${RUN_HEALTH_CHECK}" == "1" ]]; then
  wait_for_health
fi

log "Update completed."
