#!/usr/bin/env bash
# Build + setup on Render (and works on any Linux server).
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input --clear
python manage.py migrate --no-input
python manage.py setup_production