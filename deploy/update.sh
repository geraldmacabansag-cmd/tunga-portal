#!/usr/bin/env bash
# Update the website on the Droplet after pushing new code to GitHub.
#   bash /srv/tunga/app/deploy/update.sh
# Gets the new code, installs new packages, updates the database tables and
# static files, then restarts the website (a few seconds of downtime).
set -euo pipefail

APP_USER=tunga
BASE=/srv/tunga
APP_DIR=$BASE/app
VENV=$BASE/venv
run() { sudo -u $APP_USER "$@"; }

cd $APP_DIR
echo "==> Getting the new code"
run git pull --ff-only
echo "==> Python packages"
run $VENV/bin/pip install -r requirements.txt --quiet
echo "==> Database tables"
run $VENV/bin/python manage.py migrate --noinput
echo "==> Static files"
run $VENV/bin/python manage.py collectstatic --noinput --verbosity 0
run $VENV/bin/python manage.py setup_production
echo "==> Restarting the website"
sudo systemctl restart tunga
sleep 2
systemctl is-active --quiet tunga && echo "Website is running." || { echo "The website did not start:"; journalctl -u tunga -n 40 --no-pager; exit 1; }