#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)

cd "$REPO_ROOT"

SHA="unknown"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  SHA=$(git rev-parse --short HEAD)
else
  echo "git not available or not a git repo; using GIT_SHA=unknown"
fi

export GIT_SHA="$SHA"

echo "Building with GIT_SHA=$GIT_SHA"

docker compose build
