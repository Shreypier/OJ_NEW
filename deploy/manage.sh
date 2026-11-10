#!/usr/bin/env bash
# Run a Django management command with the production environment loaded.
#   ./deploy/manage.sh createsuperuser
#   ./deploy/manage.sh migrate
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
set -a
. /etc/codelang.env
set +a
cd "$APP_DIR"
exec "$APP_DIR/venv/bin/python" manage.py "$@"
