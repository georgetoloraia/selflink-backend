#!/usr/bin/env bash
set -euo pipefail

# WARNING:
# This script is read-only and safe. Still, avoid `docker compose down -v`
# unless you intentionally want to remove DB volumes/data.

usage() {
  cat <<'EOF'
Usage:
  ./scripts/db/health.sh

Environment overrides:
  COMPOSE_FILE   (default: infra/compose.yaml)
  COMPOSE        (default: "sudo docker compose")
  DB_SERVICE     (default: postgres)
  DB_NAME        (default: selflink)
  DB_USER        (default: selflink)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-infra/compose.yaml}"
COMPOSE_STR="${COMPOSE:-sudo docker compose}"
DB_SERVICE="${DB_SERVICE:-postgres}"
DB_NAME="${DB_NAME:-selflink}"
DB_USER="${DB_USER:-selflink}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is required." >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Error: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

read -r -a COMPOSE_ARR <<<"$COMPOSE_STR"
if [[ "${#COMPOSE_ARR[@]}" -eq 0 ]]; then
  echo "Error: COMPOSE command is empty." >&2
  exit 1
fi
COMPOSE_CMD=("${COMPOSE_ARR[@]}" -f "$COMPOSE_FILE")

psql_q() {
  local sql="$1"
  "${COMPOSE_CMD[@]}" exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$DB_NAME" -At -v ON_ERROR_STOP=1 -c "$sql"
}

echo "DB health check for '$DB_NAME' (service: $DB_SERVICE)"
echo

echo "[1/6] Reachability check (SELECT 1)..."
result="$(psql_q "SELECT 1;")"
if [[ "$result" != "1" ]]; then
  echo "Error: DB reachability check failed." >&2
  exit 1
fi
echo "OK"

echo "[2/6] DB info..."
echo "Current DB: $(psql_q "SELECT current_database();")"
echo "Postgres:   $(psql_q "SELECT version();")"

echo "[3/6] django_migrations count..."
migrations_count="$(psql_q "SELECT count(*) FROM django_migrations;")"
echo "django_migrations rows: $migrations_count"

echo "[4/6] Critical table existence..."
check_table() {
  local table_name="$1"
  local exists
  exists="$(psql_q "SELECT to_regclass('public.${table_name}') IS NOT NULL;")"
  if [[ "$exists" != "t" ]]; then
    echo "Missing table: public.${table_name}" >&2
    return 1
  fi
  echo "OK: public.${table_name}"
}

check_table "django_migrations"
check_table "users_user"
check_table "django_site"

coin_exists_primary="$(psql_q "SELECT to_regclass('public.coin_coinaccount') IS NOT NULL;")"
coin_exists_alt="$(psql_q "SELECT to_regclass('public.coin_coin_account') IS NOT NULL;")"
if [[ "$coin_exists_primary" != "t" && "$coin_exists_alt" != "t" ]]; then
  echo "Missing coin account table: expected public.coin_coinaccount (or public.coin_coin_account)." >&2
  exit 1
fi
if [[ "$coin_exists_primary" == "t" ]]; then
  echo "OK: public.coin_coinaccount"
else
  echo "OK: public.coin_coin_account"
fi

echo "[5/6] Row counts..."
users_count="$(psql_q "SELECT count(*) FROM users_user;")"
echo "users_user rows: $users_count"
echo "django_migrations rows: $migrations_count"

echo "[6/6] Summary..."
echo "DB health checks passed."
