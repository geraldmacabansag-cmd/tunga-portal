#!/usr/bin/env bash
# =============================================================================
# One-time setup of a DigitalOcean Droplet for the Tunga Portal
# (Ubuntu 24.04, 1 GB RAM or more). See DEPLOY.md, part B.
#
# On the Droplet, as root:
#   git clone https://github.com/YOUR-GITHUB-USERNAME/tunga_sample.git /tmp/tunga
#   bash /tmp/tunga/deploy/setup_droplet.sh
#
# It asks for your domain, GitHub address and e-mail, then installs everything:
# PostgreSQL database, Python, the website (gunicorn), nginx, free HTTPS
# certificate (Let's Encrypt), firewall and a daily backup.
# Safe to run again: it keeps the existing .env and database password.
# =============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "Run this as root (sudo bash $0)"; exit 1; fi

APP_USER=tunga
BASE=/srv/tunga
APP_DIR=$BASE/app
VENV=$BASE/venv
ENV_FILE=$APP_DIR/.env

read -rp "Your domain from Namecheap, without www (e.g. tungaleyte.com): " DOMAIN
DOMAIN=${DOMAIN#https://}; DOMAIN=${DOMAIN#http://}; DOMAIN=${DOMAIN#www.}; DOMAIN=${DOMAIN%/}
read -rp "GitHub repository address (https://github.com/.../....git): " REPO_URL
read -rp "Branch [main]: " BRANCH; BRANCH=${BRANCH:-main}
read -rp "Your e-mail (for the HTTPS certificate notices): " EMAIL

echo "==> 1/9 Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-dev build-essential libpq-dev \
    postgresql postgresql-contrib nginx certbot python3-certbot-nginx git ufw

# small Droplets run out of memory while installing packages: add 1 GB swap
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> 2/9 User and folders"
id -u $APP_USER >/dev/null 2>&1 || adduser --system --group --home $BASE $APP_USER
mkdir -p $BASE/media $BASE/private_backups $BASE/logs
chown -R $APP_USER:$APP_USER $BASE
chmod 755 $BASE                       # nginx must be able to read static and media files
chmod 700 $BASE/private_backups       # backups: only the website itself

echo "==> 3/9 Getting the code"
if [ -d "$APP_DIR/.git" ]; then
  sudo -u $APP_USER git -C $APP_DIR pull
else
  sudo -u $APP_USER git clone --branch "$BRANCH" "$REPO_URL" $APP_DIR
fi

echo "==> 4/9 Database (PostgreSQL)"
if [ -f "$ENV_FILE" ] && grep -q '^DATABASE_URL=postgresql' "$ENV_FILE"; then
  echo "    keeping the existing database settings"
else
  DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='tunga'" | grep -q 1 \
    && sudo -u postgres psql -c "ALTER USER tunga WITH PASSWORD '$DB_PASS';" \
    || sudo -u postgres psql -c "CREATE USER tunga WITH PASSWORD '$DB_PASS';"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='tunga'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE tunga OWNER tunga;"
fi

echo "==> 5/9 Python packages"
[ -d $VENV ] || sudo -u $APP_USER python3 -m venv $VENV
sudo -u $APP_USER $VENV/bin/pip install --upgrade pip wheel
sudo -u $APP_USER $VENV/bin/pip install -r $APP_DIR/requirements.txt

echo "==> 6/9 Settings file ($ENV_FILE)"
if [ ! -f "$ENV_FILE" ]; then
  SECRET=$($VENV/bin/python -c "import secrets; print(secrets.token_urlsafe(50))")
  OTPKEY=$($VENV/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  ADMINURL="lgu-panel-$($VENV/bin/python -c "import secrets; print(secrets.token_hex(4))")"
  IP=$(curl -s --max-time 5 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address || true)
  cat > "$ENV_FILE" <<EOF
# Tunga Portal settings on this Droplet (see .env.example). Keep this file secret.
PRODUCTION=1
SECRET_KEY=$SECRET
SITE_DOMAIN=$DOMAIN
ALLOWED_HOSTS=$IP
ADMIN_URL=$ADMINURL
# the visitor's real IP address, written by nginx (can't be faked by visitors)
CLIENT_IP_HEADER=HTTP_X_REAL_IP
DATABASE_URL=postgresql://tunga:$DB_PASS@127.0.0.1:5432/tunga
OTP_ENCRYPTION_KEY=$OTPKEY

# Uploaded files on this server's disk (served by nginx). For Cloudinary:
# MEDIA_STORAGE=cloudinary and fill the CLOUDINARY_* lines.
MEDIA_STORAGE=local
MEDIA_ROOT=$BASE/media
BACKUP_ROOT=$BASE/private_backups
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Fill these, then run: bash $APP_DIR/deploy/update.sh
RECAPTCHA_SITE_KEY=
RECAPTCHA_SECRET_KEY=
EOF
  chown $APP_USER:$APP_USER "$ENV_FILE"; chmod 600 "$ENV_FILE"
  echo "    created. Django admin address: https://$DOMAIN/$ADMINURL/  (write it down)"
else
  echo "    keeping the existing file"
fi

echo "==> 7/9 Database tables and static files"
cd $APP_DIR
sudo -u $APP_USER $VENV/bin/python manage.py migrate --noinput
sudo -u $APP_USER $VENV/bin/python manage.py collectstatic --noinput
sudo -u $APP_USER $VENV/bin/python manage.py setup_production
chmod 755 $APP_DIR; chmod -R o+rX $APP_DIR/staticfiles $BASE/media

echo "==> 8/9 Website service (gunicorn) and nginx"
cat > /etc/systemd/system/tunga.service <<EOF
[Unit]
Description=Tunga Portal (gunicorn)
After=network.target postgresql.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment=GUNICORN_BIND=127.0.0.1:8000
ExecStart=$VENV/bin/gunicorn tunga_portal.wsgi --config gunicorn.conf.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now tunga
systemctl restart tunga

cat > /etc/nginx/sites-available/tunga <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    client_max_body_size 25M;          # uploads (photos, PDFs, backups)

    location /static/ { alias $APP_DIR/staticfiles/; expires 30d; access_log off; }
    location /media/  { alias $BASE/media/; expires 7d; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/tunga /etc/nginx/sites-enabled/tunga
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

ufw allow OpenSSH >/dev/null
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null

# daily automatic backup at 2:00 AM (only runs if turned on in Super Admin -> Backup & Restore)
echo "0 2 * * * cd $APP_DIR && $VENV/bin/python manage.py backup_site --auto >> $BASE/logs/backup.log 2>&1" \
  | crontab -u $APP_USER -

echo "==> 9/9 HTTPS certificate (Let's Encrypt)"
if certbot --nginx -d "$DOMAIN" -d "www.$DOMAIN" --redirect -m "$EMAIL" --agree-tos -n; then
  echo "    HTTPS is on."
else
  echo "    Could not get the certificate yet. Usually the Namecheap DNS records"
  echo "    are not pointing to this Droplet yet (it can take up to 30 minutes)."
  echo "    Try again later with:"
  echo "    certbot --nginx -d $DOMAIN -d www.$DOMAIN --redirect -m $EMAIL --agree-tos -n"
fi

echo
echo "Done. Open https://$DOMAIN"
echo "Create your first Django superuser with:"
echo "  cd $APP_DIR && sudo -u $APP_USER $VENV/bin/python manage.py createsuperuser"
echo "Update the site after pushing new code to GitHub:  bash $APP_DIR/deploy/update.sh"