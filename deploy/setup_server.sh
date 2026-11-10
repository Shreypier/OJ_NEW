#!/usr/bin/env bash
# One-time setup of an Ubuntu 22.04 / 24.04 server (for example an AWS EC2 instance).
#
#   cd ~/codelang
#   sudo bash deploy/setup_server.sh yourname.duckdns.org
#
# It is safe to run again: it will not overwrite an existing /etc/codelang.env.
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then echo "Usage: sudo bash deploy/setup_server.sh <your-domain>"; exit 1; fi
if [ "$(id -u)" -ne 0 ]; then echo "Please run with sudo."; exit 1; fi

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_USER="${SUDO_USER:-ubuntu}"
ENV_FILE=/etc/codelang.env
DATA_DIR=/var/lib/codelang
MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)

echo "==> 1/7 Swap space (lets a small server compile C++)"
if ! swapon --show | grep -q .; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> 2/7 System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y docker.io nginx python3-venv python3-pip certbot python3-certbot-nginx git
systemctl enable --now docker
usermod -aG docker "$APP_USER"

echo "==> 3/7 Python environment"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> 4/7 Configuration ($ENV_FILE)"
mkdir -p "$DATA_DIR"
chown "$APP_USER":"$APP_USER" "$DATA_DIR"
if [ ! -f "$ENV_FILE" ]; then
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
  if [ "$MEM_MB" -lt 1500 ]; then CONC=1; else CONC=2; fi
  cat > "$ENV_FILE" <<EOF
DJANGO_SECRET_KEY=$SECRET
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=$DOMAIN
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DJANGO_HTTPS=0
DJANGO_DB_PATH=$DATA_DIR/db.sqlite3
JUDGE_BACKEND=docker
JUDGE_MAX_CONCURRENT=$CONC
EOF
  chown root:"$APP_USER" "$ENV_FILE"
  chmod 640 "$ENV_FILE"
fi

echo "==> 5/7 Judge sandbox image (takes a few minutes the first time)"
docker build -t codelang-sandbox "$APP_DIR/sandbox"

echo "==> 6/7 Database and static files"
sudo -u "$APP_USER" bash "$APP_DIR/deploy/manage.sh" migrate --noinput
sudo -u "$APP_USER" bash "$APP_DIR/deploy/manage.sh" collectstatic --noinput

echo "==> 7/7 Web server (Gunicorn service + Nginx)"
sed -e "s|@APP_DIR@|$APP_DIR|g" -e "s|@APP_USER@|$APP_USER|g" \
    "$APP_DIR/deploy/codelang.service" > /etc/systemd/system/codelang.service
systemctl daemon-reload
systemctl enable codelang
systemctl restart codelang

sed -e "s|@DOMAIN@|$DOMAIN|g" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/codelang
ln -sf /etc/nginx/sites-available/codelang /etc/nginx/sites-enabled/codelang
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo
echo "Done. The site should answer at http://$DOMAIN"
echo "Next: sudo certbot --nginx -d $DOMAIN    (HTTPS), then set DJANGO_HTTPS=1 in $ENV_FILE"
echo "      and run: sudo systemctl restart codelang"
echo "Log out and back in once so your user can run 'docker' without sudo."
