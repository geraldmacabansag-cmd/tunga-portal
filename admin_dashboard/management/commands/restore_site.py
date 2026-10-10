"""Restore a backup from the command line — for when the website itself
can't be opened (e.g. moving to a new server).

    python manage.py restore_site tunga-backup-20261010-020000-auto.zip --yes

The file can be a path on this computer, or the name of a backup already in
the backup storage. Run `python manage.py migrate` first on a new server.
"""
import os

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from admin_dashboard import backup
from admin_dashboard.models import SiteBackup


class Command(BaseCommand):
    help = "Replace all site data with a backup (.zip) and put back its uploaded files."

    def add_arguments(self, parser):
        parser.add_argument("backup_file")
        parser.add_argument("--yes", action="store_true", help="Confirm: this replaces all current data.")

    def handle(self, *args, **opts):
        if not opts["yes"]:
            raise CommandError("This replaces ALL current site data. Add --yes to confirm.")
        path = opts["backup_file"]
        record = SiteBackup.objects.filter(filename=path, status="success").first()
        if record is None:
            if not os.path.exists(path):
                raise CommandError(f"File not found: {path}")
            with open(path, "rb") as fh:
                try:
                    record = backup.save_uploaded_backup(File(fh, name=os.path.basename(path)), "Command line")
                except backup.BackupError as exc:
                    raise CommandError(str(exc))
        ok, msg = backup.restore_backup(record, "command line")
        if ok:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            raise CommandError(msg)