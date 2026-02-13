#!/usr/bin/env bash
set -euo pipefail

# WARNING:
# `docker compose down -v` removes volumes, including Postgres data.
# Always run this backup script before risky compose operations.

usage() {
  cat <<'EOF'
Usage: ./scripts/db/backup.sh

Environment overrides:
  COMPOSE_FILE   (default: infra/compose.yaml)
  COMPOSE        (default: "sudo docker compose")
  DB_SERVICE     (default: postgres)
  DB_NAME        (default: selflink)
  DB_USER        (default: selflink)
  BACKUP_DIR     (default: backups/postgres)

Creates a custom-format pg_dump (-Fc) and updates BACKUP_DIR/LATEST.
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

mkdir -p "$BACKUP_DIR"
timestamp="$(date +%F-%H%M)"
dump_file="$BACKUP_DIR/${DB_NAME}-${timestamp}.dump"
latest_file="$BACKUP_DIR/LATEST"

echo "Creating backup: $dump_file"

if ! "${COMPOSE_CMD[@]}" exec -T "$DB_SERVICE" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc >"$dump_file"; then
  rm -f "$dump_file"
  echo "Error: pg_dump failed." >&2
  exit 1
fi

if [[ ! -s "$dump_file" ]]; then
  rm -f "$dump_file"
  echo "Error: backup file is empty: $dump_file" >&2
  exit 1
fi

basename "$dump_file" >"$latest_file"

size_bytes="$(stat -c%s "$dump_file")"
size_human="$(numfmt --to=iec-i --suffix=B "$size_bytes")"

echo "Backup complete."
echo "File: $dump_file"
echo "Size: $size_human ($size_bytes bytes)"
echo "LATEST: $(cat "$latest_file")"
