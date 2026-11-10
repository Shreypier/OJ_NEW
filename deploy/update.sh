#!/usr/bin/env bash
# Deploy the latest code from GitHub:   ./deploy/update.sh
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

git pull --ff-only
"$APP_DIR/venv/bin/pip" install -r requirements.txt
bash deploy/manage.sh migrate --noinput
bash deploy/manage.sh collectstatic --noinput
docker build -t codelang-sandbox sandbox/
sudo systemctl restart codelang
echo "Updated. Check it with: sudo systemctl status codelang"
