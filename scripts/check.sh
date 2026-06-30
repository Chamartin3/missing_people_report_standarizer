#!/usr/bin/env bash
# Run every quality gate (the same five the README documents) + the web build.
# Usage: scripts/check.sh        → run on the host (after `uv sync`)
#        scripts/check.sh docker → run the Python gates inside the app container
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "docker" ]]; then
  docker compose run --rm app bash -lc \
    "ruff check . && ruff format --check . && pyright && lint-imports && pytest"
else
  ruff check .
  ruff format --check .
  pyright
  lint-imports
  pytest
fi

# Frontend: no eslint config in the repo, so the build is the check that catches
# broken JSX/imports. ponytail: add eslint here if a config ever lands.
( cd web && npm run build )
