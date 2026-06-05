#!/usr/bin/env bash

_finengine_trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "${value}"
}

load_deploy_env() {
  local env_file="$1"
  shift
  [[ -f "${env_file}" ]] || return 0

  local allowed=" $* "
  local raw line key value
  while IFS= read -r raw || [[ -n "${raw}" ]]; do
    raw="${raw%$'\r'}"
    line="$(_finengine_trim "${raw}")"
    [[ -z "${line}" || "${line:0:1}" == "#" || "${line}" != *"="* ]] && continue
    [[ "${line}" == export\ * ]] && line="${line#export }"

    key="$(_finengine_trim "${line%%=*}")"
    value="$(_finengine_trim "${line#*=}")"
    [[ "${key}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    [[ "${allowed}" == *" ${key} "* ]] || continue
    [[ -n "${!key+x}" ]] && continue

    if [[ "${#value}" -ge 2 ]]; then
      if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]]; then
        value="${value:1:${#value}-2}"
      elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
        value="${value:1:${#value}-2}"
      fi
    fi

    export "${key}=${value}"
  done < "${env_file}"
}
