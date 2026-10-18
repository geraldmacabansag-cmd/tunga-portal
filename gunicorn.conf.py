"""Settings for gunicorn, the program that runs the website on the server.
Used by the Procfile (DigitalOcean App Platform), .do/app.yaml and the
Droplet service (deploy/setup_droplet.sh)."""
import multiprocessing
import os

# App Platform / Render give the port in $PORT; on a Droplet nginx talks to 127.0.0.1:8000
bind = os.environ.get("GUNICORN_BIND") or f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Render (free plan, 512 MB): 1 worker, the same as before this file existed.
# DigitalOcean: 2 workers. WEB_CONCURRENCY overrides both.
_default_workers = 1 if "RENDER" in os.environ else min(2, multiprocessing.cpu_count() * 2 + 1)
workers = int(os.environ.get("WEB_CONCURRENCY", _default_workers))
threads = int(os.environ.get("GUNICORN_THREADS", 1 if "RENDER" in os.environ else 4))
timeout = 120          # big uploads / backups / PDF generation
graceful_timeout = 30
keepalive = 5
accesslog = "-"        # requests and errors go to the server log
errorlog = "-"
forwarded_allow_ips = "*"   # trust X-Forwarded-Proto from the DigitalOcean / nginx proxy (for HTTPS)