"""Make a backup from the command line or a scheduler.

    python manage.py backup_site            # full backup now (data + files)
    python manage.py backup_site --no-files # data only
    python manage.py backup_site --auto     # the daily job: only runs if automatic
                                            # backups are on and the last one is
                                            # more than 24 hours old

DigitalOcean Droplet (cron, every day at 2:00 AM):
    0 2 * * * cd /path/to/project && venv/bin/python manage.py backup_site --auto
DigitalOcean App Platform: add a "Scheduled job" component with the same command.
"""
from django.core.management.base import BaseCommand

from admin_dashboard import backup


class Command(BaseCommand):
    help = "Back up the whole portal (database + uploaded files) to the backup storage."

    def add_arguments(self, parser):
        parser.add_argument("--auto", action="store_true", help="Daily job: skip if not due.")
        parser.add_argument("--no-files", action="store_true", help="Database only, no uploaded files.")

    def handle(self, *args, **opts):
        if backup.is_busy():
            self.stdout.write("A backup or restore is already running. Skipped.")
            return
        if opts["auto"]:
            if not backup.auto_backup_due():
                self.stdout.write("Automatic backups are off, or the last one is less than 24 hours old. Skipped.")
                return
            s = backup.BackupSettings.get_solo()
            include_files = s.auto_include_files and not opts["no_files"]
            kind, who = "auto", "Automatic (scheduler)"
        else:
            include_files = not opts["no_files"]
            kind, who = "manual", "Command line"

        record = backup.create_backup(kind, include_files, who)
        if record.status == "success":
            self.stdout.write(self.style.SUCCESS(f"Backup saved: {record.filename} ({record.size:,} bytes)"))
            if record.error:
                self.stdout.write(self.style.WARNING(record.error))
        else:
            self.stderr.write(self.style.ERROR(f"Backup failed: {record.error}"))
            raise SystemExit(1)