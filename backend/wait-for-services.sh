#!/usr/bin/env bash
# Optional TCP waits before app startup. External Postgres/Neo4j/Redis do not use compose
# hostnames, so by default nothing is waited on.
#
# Set only what you need:
#   POSTGRES_WAIT_HOST + POSTGRES_WAIT_PORT (e.g. postgres + 5432 on compose network)
#   NEO4J_WAIT_HOST + NEO4J_WAIT_PORT
#   REDIS_WAIT_HOST + REDIS_WAIT_PORT
#
# Or set SKIP_WAIT_FOR_DEPS=1 to skip even if hosts are set (rare).
set -euo pipefail

case "${SKIP_WAIT_FOR_DEPS:-}" in
  1|true|TRUE|yes|Yes)
    echo "SKIP_WAIT_FOR_DEPS set — skipping TCP waits"
    exit 0
    ;;
esac

POSTGRES_WAIT_HOST="${POSTGRES_WAIT_HOST:-}"
POSTGRES_WAIT_PORT="${POSTGRES_WAIT_PORT:-5432}"
NEO4J_WAIT_HOST="${NEO4J_WAIT_HOST:-}"
NEO4J_WAIT_PORT="${NEO4J_WAIT_PORT:-7687}"
REDIS_WAIT_HOST="${REDIS_WAIT_HOST:-}"
REDIS_WAIT_PORT="${REDIS_WAIT_PORT:-6379}"
WAIT_TIMEOUT_SEC="${WAIT_TIMEOUT_SEC:-60}"

wait_tcp() {
  local host="$1"
  local port="$2"
  local name="$3"
  local deadline=$((SECONDS + WAIT_TIMEOUT_SEC))

  echo "waiting for ${name} (${host}:${port})..."
  while true; do
    if [ "${SECONDS}" -ge "${deadline}" ]; then
      echo "ERROR: ${name} unreachable at ${host}:${port} after ${WAIT_TIMEOUT_SEC}s" >&2
      exit 1
    fi
    if nc -z -w 2 "${host}" "${port}" 2>/dev/null; then
      echo "${name} ready"
      return 0
    fi
    sleep 1
  done
}

any_wait=false
if [ -n "${POSTGRES_WAIT_HOST}" ]; then
  any_wait=true
  wait_tcp "${POSTGRES_WAIT_HOST}" "${POSTGRES_WAIT_PORT}" "postgres"
fi
if [ -n "${NEO4J_WAIT_HOST}" ]; then
  any_wait=true
  wait_tcp "${NEO4J_WAIT_HOST}" "${NEO4J_WAIT_PORT}" "neo4j"
fi
if [ -n "${REDIS_WAIT_HOST}" ]; then
  any_wait=true
  wait_tcp "${REDIS_WAIT_HOST}" "${REDIS_WAIT_PORT}" "redis"
fi

if [ "${any_wait}" = false ]; then
  echo "No *_WAIT_HOST set — skipping TCP waits (external DATABASE_URL / NEO4J_URI / Redis)"
else
  echo "all configured dependencies reachable"
fi
