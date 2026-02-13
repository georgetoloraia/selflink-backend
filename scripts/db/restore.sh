#!/usr/bin/env bash
set -euo pipefail

# WARNING:
# This is destructive: it drops and recreates the target DB.
# `docker compose down -v` also deletes DB volumes; avoid it unless intended.
# Take a backup with ./scripts/db/backup.sh first.

usage() {
  cat <<'EOF'
Usage:
  ./scripts/db/restore.sh [dump_file]

If dump_file is omitted, restores from backups/postgres/$(cat backups/postgres/LATEST).

Environment overrides:
  COMPOSE_FILE    (default: infra/compose.yaml)
  COMPOSE         (default: "sudo docker compose")
  DB_SERVICE      (default: postgres)
  DB_NAME         (default: selflink)
  DB_USER         (default: selflink)
  BACKUP_DIR      (default: backups/postgres)
  FORCE_RESTORE   (required as 1 for non-interactive use)
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
BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
LATEST_FILE="$BACKUP_DIR/LATEST"

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

dump_path="${1:-}"
if [[ -z "$dump_path" ]]; then
  if [[ ! -f "$LATEST_FILE" ]]; then
    echo "Error: no dump path provided and LATEST not found: $LATEST_FILE" >&2
    exit 1
  fi
  latest_name="$(tr -d '[:space:]' <"$LATEST_FILE")"
  if [[ -z "$latest_name" ]]; then
    echo "Error: LATEST file is empty: $LATEST_FILE" >&2
    exit 1
  fi
  dump_path="$BACKUP_DIR/$latest_name"
fi

if [[ ! -f "$dump_path" ]]; then
  echo "Error: dump file not found: $dump_path" >&2
  exit 1
fi

if [[ ! -s "$dump_path" ]]; then
  echo "Error: dump file is empty: $dump_path" >&2
  exit 1
fi

if [[ -t 0 ]]; then
  echo "About to restore into database '$DB_NAME' from: $dump_path"
  read -r -p "Type RESTORE to continue: " confirm
  if [[ "$confirm" != "RESTORE" ]]; then
    echo "Aborted."
    exit 1
  fi
else
  if [[ "${FORCE_RESTORE:-}" != "1" ]]; then
    echo "Error: non-interactive mode requires FORCE_RESTORE=1." >&2
    exit 1
  fi
fi

echo "Terminating active connections to '$DB_NAME'..."
"${COMPOSE_CMD[@]}" exec -T "$DB_SERVICE" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();"

echo "Dropping database '$DB_NAME'..."
"${COMPOSE_CMD[@]}" exec -T "$DB_SERVICE" dropdb -U "$DB_USER" --if-exists "$DB_NAME"

echo "Creating database '$DB_NAME'..."
"${COMPOSE_CMD[@]}" exec -T "$DB_SERVICE" createdb -U "$DB_USER" "$DB_NAME"

echo "Restoring dump..."
cat "$dump_path" | "${COMPOSE_CMD[@]}" exec -T "$DB_SERVICE" \
  pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-privileges

echo "Restore complete."
echo "Restored file: $dump_path"
echo "Next: run migrate only if code/schema changed:"
echo "  ${COMPOSE_STR} -f ${COMPOSE_FILE} run --rm migrate"
