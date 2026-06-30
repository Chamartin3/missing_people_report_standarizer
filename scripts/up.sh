#!/usr/bin/env bash
# Build + start the whole stack (db + backend app + web frontend).
# Usage: scripts/up.sh          → build changed images, start detached
#        scripts/up.sh --logs   → same, then tail app+web logs
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d --build

if [[ "${1:-}" == "--logs" ]]; then
  docker compose logs -f app web
else
  echo "Up. Web → http://localhost:8080  (API proxied at /api)"
fi
