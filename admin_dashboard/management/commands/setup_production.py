"""Run after every deploy (the deploy scripts do it for you):

    python manage.py migrate --noinput
    python manage.py setup_production

1. Creates the first Django superuser from DJANGO_SUPERUSER_USERNAME /
   DJANGO_SUPERUSER_EMAIL / DJANGO_SUPERUSER_PASSWORD (only if it doesn't exist).
2. Sets the site address used in emails and Google sign-in (Django "Sites")
   to SITE_DOMAIN (or the App Platform / Render address).
3. Lists settings that are missing, so you can see problems in the deploy log.
Safe to run any number of times.
"""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "First-time / after-deploy setup of the live site (safe to run again)."

    def handle(self, *args, **opts):
        self._superuser()
        self._site()
        self._check()

    def _superuser(self):
        User = get_user_model()
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        if not (username and password):
            self.stdout.write("Superuser: DJANGO_SUPERUSER_USERNAME / _PASSWORD not set, skipped.")
        elif User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser: {username} already exists.")
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser: {username} created."))

    def _site(self):
        domain = (getattr(settings, "SITE_DOMAIN", "") or os.environ.get("APP_DOMAIN")
                  or os.environ.get("RENDER_EXTERNAL_HOSTNAME") or "")
        if not domain:
            self.stdout.write("Site address: SITE_DOMAIN not set, skipped.")
            return
        from django.apps import apps
        if not apps.is_installed("django.contrib.sites"):
            return
        from django.contrib.sites.models import Site
        site, _ = Site.objects.update_or_create(
            pk=getattr(settings, "SITE_ID", 1),
            defaults={"domain": domain, "name": "Municipality of Tunga"})
        self.stdout.write(f"Site address: {site.domain}")

    def _check(self):
        missing = []
        if settings.DEBUG:
            missing.append("DEBUG is ON - set PRODUCTION=1 (or DEBUG=0) on the server")
        for name in ("SECRET_KEY", "OTP_ENCRYPTION_KEY", "ADMIN_URL", "RECAPTCHA_SITE_KEY", "RECAPTCHA_SECRET_KEY"):
            if not os.environ.get(name):
                missing.append(name)
        if "sqlite" in settings.DATABASES["default"]["ENGINE"] and not settings.DEBUG:
            missing.append("DATABASE_URL (the site is using SQLite - data is lost on App Platform redeploys)")
        storage = getattr(settings, "MEDIA_STORAGE", "")
        if storage == "cloudinary":
            missing += [n for n in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET") if not os.environ.get(n)]
        elif storage == "spaces":
            missing += [n for n in ("SPACES_BUCKET", "SPACES_KEY", "SPACES_SECRET") if not os.environ.get(n)]
        if not settings.ALLOWED_HOSTS:
            missing.append("SITE_DOMAIN or ALLOWED_HOSTS")
        if missing:
            self.stdout.write(self.style.WARNING("Check these settings:\n  - " + "\n  - ".join(missing)))
        else:
            self.stdout.write(self.style.SUCCESS("All main settings are set."))
        self.stdout.write(f"Uploads are stored in: {storage}. Addresses allowed: {', '.join(settings.ALLOWED_HOSTS)}")