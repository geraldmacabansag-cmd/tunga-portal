"""Backup & Restore for the whole portal.

A backup is one .zip file:
    manifest.json   what is inside (date, counts, migrations, file list)
    data.json       every database row (Django "dumpdata" format, so it
                    loads into PostgreSQL, MySQL or SQLite alike)
    files/...       every uploaded file (photos, PDFs, logos...), read
                    through Django's storage, so it works the same with
                    Cloudinary, DigitalOcean Spaces or a plain folder

Backups are kept in the "backups" storage (see get_backup_storage) and can
be downloaded. Used by the Backup & Restore page and by:
    python manage.py backup_site [--auto] [--no-files]
    python manage.py restore_site <file.zip> --yes
"""
import json
import os
import shutil
import tempfile
import threading
import traceback
import zipfile
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, storages
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import connection, models, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.utils import timezone

from .models import BackupSettings, SiteBackup

FORMAT_VERSION = 1
APP_ID = "tunga-portal"

# Never saved in a backup, never wiped by a restore.
SKIP_MODELS = {
    "contenttypes.contenttype",   # rebuilt by Django itself
    "auth.permission",            # rebuilt by Django itself
    "sessions.session",           # who is logged in right now
    "admin.logentry",             # Django admin's own history
    "admin_dashboard.sitebackup",
    "admin_dashboard.backupsettings",
}
# Wiped by a restore (but not saved, see above).
CLEAR_ON_RESTORE = {"admin.logentry"}

# Shown on the page: "what is inside this backup".
SUMMARY_MODELS = [
    ("Announcements", "office_dashboard.Announcement"),
    ("News", "office_dashboard.NewsUpdate"),
    ("Events", "office_dashboard.Event"),
    ("Photos", "office_dashboard.Photo"),
    ("Forms", "office_dashboard.DownloadableForm"),
    ("Services", "office_dashboard.Service"),
    ("Offices", "offices.Office"),
    ("User accounts", "auth.User"),
    ("Messages", "office_dashboard.Message"),
]

STALE_AFTER = timedelta(hours=3)      # a "running" job older than this has died
AUTO_EVERY = timedelta(hours=24)

_lock = threading.Lock()


class BackupError(Exception):
    pass


# --------------------------------------------------------------------------
# Where backups are kept
# --------------------------------------------------------------------------
def get_backup_storage():
    """settings.STORAGES["backups"] if it exists (e.g. a private DigitalOcean
    Spaces folder), otherwise a private folder on the server that the website
    never serves (settings.BACKUP_ROOT, default <project>/private_backups)."""
    if "backups" in getattr(settings, "STORAGES", {}):
        return storages["backups"]
    root = getattr(settings, "BACKUP_ROOT", None) or os.path.join(settings.BASE_DIR, "private_backups")
    return FileSystemStorage(location=str(root))


def storage_description():
    """(label, is_temporary) for the page."""
    storage = get_backup_storage()
    if isinstance(storage, FileSystemStorage):
        temporary = "RENDER" in os.environ   # Render erases the disk on every deploy
        return "This server's disk (private folder)", temporary
    name = type(storage).__name__
    if "S3" in name:
        endpoint = getattr(storage, "endpoint_url", "") or ""
        if "digitaloceanspaces" in endpoint:
            return "DigitalOcean Spaces (private)", False
        return "S3 storage (private)", False
    return name, False


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _label(model):
    return f"{model._meta.app_label}.{model._meta.model_name}"


def _file_fields():
    """(model, field) for every FileField / ImageField in the project."""
    for model in apps.get_models():
        if _label(model) in SKIP_MODELS:
            continue
        for field in model._meta.get_fields():
            if isinstance(field, models.FileField) and field.concrete:
                yield model, field


def _summary():
    out = {}
    for title, dotted in SUMMARY_MODELS:
        try:
            out[title] = apps.get_model(dotted)._base_manager.count()
        except LookupError:
            pass
    return out


def _migrations():
    applied = {}
    for app, name in MigrationRecorder(connection).applied_migrations():
        applied.setdefault(app, []).append(name)
    return {app: sorted(names) for app, names in applied.items()}


def _now_name(kind):
    return timezone.localtime().strftime(f"tunga-backup-%Y%m%d-%H%M%S-{kind}.zip")


def _mark_stale_jobs():
    SiteBackup.objects.filter(status="running", created_at__lt=timezone.now() - STALE_AFTER).update(
        status="failed", error="The backup stopped before finishing (the server restarted or timed out).",
        finished_at=timezone.now())
    s = BackupSettings.get_solo()
    if s.restore_status == "running" and s.restore_started_at and s.restore_started_at < timezone.now() - STALE_AFTER:
        s.restore_status = "failed"
        s.restore_message = "The restore stopped before finishing. Nothing was changed if it failed midway."
        s.save()


def is_busy():
    _mark_stale_jobs()
    return (SiteBackup.objects.filter(status="running").exists()
            or BackupSettings.get_solo().restore_status == "running")


def _notify(title, description="", level="info", icon="fa-solid fa-database"):
    try:
        from django.urls import reverse
        from .signals import notify_super_admins
        notify_super_admins(title, description, level, icon, reverse("admin_dashboard:ad_backup"))
    except Exception:
        pass


# --------------------------------------------------------------------------
# Making a backup
# --------------------------------------------------------------------------
def _write_zip(path, include_files, created_by):
    """Builds the backup .zip at `path`. Returns (summary, warnings)."""
    tmpdir = tempfile.mkdtemp(prefix="tunga-backup-")
    try:
        data_path = os.path.join(tmpdir, "data.json")
        call_command(
            "dumpdata",
            exclude=sorted(SKIP_MODELS),
            natural_foreign=True,
            use_base_manager=True,
            output=data_path,
            verbosity=0,
        )

        files, missing = [], []
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            zf.write(data_path, "data.json")

            if include_files:
                seen = set()
                for model, field in _file_fields():
                    names = (model._base_manager.exclude(**{field.attname: ""})
                             .exclude(**{f"{field.attname}__isnull": True})
                             .values_list(field.attname, flat=True).distinct())
                    for name in names:
                        if not name or name in seen:
                            continue
                        seen.add(name)
                        try:
                            with field.storage.open(name, "rb") as src, zf.open("files/" + name, "w", force_zip64=True) as dst:
                                shutil.copyfileobj(src, dst, 1024 * 1024)
                            files.append({"name": name, "field": f"{_label(model)}.{field.name}"})
                        except Exception as exc:  # deleted from storage, network hiccup...
                            missing.append({"name": name, "error": str(exc)[:200]})

            summary = _summary()
            summary["Uploaded files"] = len(files)
            manifest = {
                "app": APP_ID,
                "format_version": FORMAT_VERSION,
                "created_at": timezone.now().isoformat(),
                "created_by": created_by,
                "database": connection.vendor,
                "include_files": include_files,
                "summary": summary,
                "migrations": _migrations(),
                "files": files,
                "missing_files": missing,
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=1))
        return summary, missing
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def create_backup(kind="manual", include_files=True, created_by="", record=None):
    """Makes a backup now (in this thread). Returns the SiteBackup row."""
    if record is None:
        record = SiteBackup.objects.create(kind=kind, include_files=include_files,
                                           created_by_name=created_by, status="running")
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip", prefix="tunga-")
    os.close(fd)
    try:
        summary, missing = _write_zip(tmp_zip, include_files, created_by)
        storage = get_backup_storage()
        with open(tmp_zip, "rb") as fh:
            saved_name = storage.save(_now_name(kind), File(fh))
        record.filename = saved_name
        record.size = os.path.getsize(tmp_zip)
        record.summary = summary
        record.status = "success"
        if missing:
            record.error = f"{len(missing)} file(s) could not be read and were skipped: " + \
                ", ".join(m["name"] for m in missing[:5]) + ("…" if len(missing) > 5 else "")
        record.finished_at = timezone.now()
        record.save()
        cleanup_old_backups()
        return record
    except Exception as exc:
        record.status = "failed"
        record.error = f"{exc}"[:2000]
        record.finished_at = timezone.now()
        record.save()
        _notify("Backup failed", record.error[:200], "danger", "fa-solid fa-triangle-exclamation")
        traceback.print_exc()
        return record
    finally:
        try:
            os.remove(tmp_zip)
        except OSError:
            pass


def _in_background(target, *args):
    def run():
        try:
            target(*args)
        finally:
            connection.close()
    threading.Thread(target=run, daemon=True).start()


def start_backup(kind="manual", include_files=True, created_by=""):
    """Starts a backup in the background (so big backups don't time out the
    page). Returns the SiteBackup row, or None if something is already running."""
    with _lock:
        if is_busy():
            return None
        record = SiteBackup.objects.create(kind=kind, include_files=include_files,
                                           created_by_name=created_by, status="running")
    _in_background(create_backup, kind, include_files, created_by, record)
    return record


def auto_backup_due():
    s = BackupSettings.get_solo()
    if not s.auto_enabled:
        return False
    recent = SiteBackup.objects.filter(kind="auto", created_at__gte=timezone.now() - AUTO_EVERY) \
                               .exclude(status="failed").exists()
    return not recent


def maybe_start_auto_backup():
    """Called when a Super Admin opens a dashboard page: if automatic backups
    are on and the last one is more than 24 hours old, start one. (On a
    server with a scheduler, `manage.py backup_site --auto` does the same.)"""
    try:
        if auto_backup_due() and not is_busy():
            s = BackupSettings.get_solo()
            start_backup("auto", s.auto_include_files, "Automatic")
    except Exception:
        traceback.print_exc()


def cleanup_old_backups():
    """Keeps the newest `keep_count` manual/automatic backups (and the newest
    3 safety backups); deletes the rest, file and all."""
    s = BackupSettings.get_solo()
    storage = get_backup_storage()

    def prune(qs, keep):
        for old in qs[keep:]:
            delete_backup(old, storage)

    done = SiteBackup.objects.filter(status="success")
    prune(done.filter(kind__in=["manual", "auto"]), max(1, s.keep_count))
    prune(done.filter(kind="safety"), 3)
    prune(SiteBackup.objects.filter(status="failed"), 10)


def delete_backup(record, storage=None):
    storage = storage or get_backup_storage()
    if record.filename:
        try:
            storage.delete(record.filename)
        except Exception:
            pass
    record.delete()


# --------------------------------------------------------------------------
# Checking an uploaded / saved backup
# --------------------------------------------------------------------------
def read_manifest(zip_path):
    """Opens a backup .zip and returns its manifest, or raises BackupError."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            if "manifest.json" not in names or "data.json" not in names:
                raise BackupError("This is not a Tunga portal backup file (manifest.json / data.json is missing).")
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            bad = zf.testzip()
            if bad:
                raise BackupError(f"The backup file is damaged ({bad}).")
    except zipfile.BadZipFile:
        raise BackupError("This file is not a valid .zip backup.")
    except (ValueError, UnicodeDecodeError):
        raise BackupError("The backup's manifest.json can't be read.")
    if manifest.get("app") != APP_ID:
        raise BackupError("This backup was not made by the Tunga portal.")
    if int(manifest.get("format_version", 0)) > FORMAT_VERSION:
        raise BackupError("This backup was made by a newer version of the system. Update the system first.")
    return manifest


def _app_installed(label):
    try:
        apps.get_app_config(label)
        return True
    except LookupError:
        return False


def check_compatible(manifest):
    """A backup made after a newer update (migrations this system doesn't
    have yet) can't be restored safely."""
    current = _migrations()
    for app, names in (manifest.get("migrations") or {}).items():
        missing = set(names) - set(current.get(app, []))
        if missing and _app_installed(app):
            raise BackupError(
                f"This backup is from a newer version of the system ({app}: {sorted(missing)[0]}). "
                "Deploy the latest code and run migrations first, then restore.")


def save_uploaded_backup(uploaded_file, created_by=""):
    """Checks an uploaded .zip and keeps it as an "Uploaded" backup."""
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip", prefix="tunga-up-")
    os.close(fd)
    try:
        with open(tmp_zip, "wb") as fh:
            for chunk in uploaded_file.chunks():
                fh.write(chunk)
        manifest = read_manifest(tmp_zip)
        with open(tmp_zip, "rb") as fh:
            name = get_backup_storage().save(_now_name("uploaded"), File(fh))
        return SiteBackup.objects.create(
            filename=name, kind="uploaded", status="success",
            include_files=bool(manifest.get("include_files")),
            size=os.path.getsize(tmp_zip), summary=manifest.get("summary") or {},
            created_by_name=created_by or "Uploaded", finished_at=timezone.now(),
        )
    finally:
        try:
            os.remove(tmp_zip)
        except OSError:
            pass


def _download_to_temp(record):
    fd, tmp_zip = tempfile.mkstemp(suffix=".zip", prefix="tunga-restore-")
    os.close(fd)
    with get_backup_storage().open(record.filename, "rb") as src, open(tmp_zip, "wb") as dst:
        shutil.copyfileobj(src, dst, 1024 * 1024)
    return tmp_zip


# --------------------------------------------------------------------------
# Restoring
# --------------------------------------------------------------------------
def _models_to_clear():
    """Every table a restore replaces (all of them except SKIP_MODELS, plus
    the many-to-many link tables)."""
    out = []
    for model in apps.get_models(include_auto_created=True):
        label = _label(model)
        if model._meta.proxy or not model._meta.managed:
            continue
        if label in SKIP_MODELS and label not in CLEAR_ON_RESTORE:
            continue
        if model._meta.auto_created:
            # a many-to-many table: skip it if it belongs to a skipped model
            owner = model._meta.auto_created
            if _label(owner) in SKIP_MODELS:
                continue
        out.append(model)
    return out


def _restore_files(zf, manifest, log):
    """Puts back uploaded files that are missing from the current storage.
    Files that already exist are left alone; nothing is ever deleted."""
    restored = skipped = failed = 0
    for entry in manifest.get("files") or []:
        name, field_path = entry.get("name"), entry.get("field", "")
        if not name:
            continue
        storage, model, field = None, None, None
        try:
            app_label, model_name, field_name = field_path.rsplit(".", 2)
            model = apps.get_model(app_label, model_name)
            field = model._meta.get_field(field_name)
            storage = field.storage
        except (ValueError, LookupError, Exception):
            from django.core.files.storage import default_storage
            storage = default_storage
        try:
            if storage.exists(name):
                skipped += 1
                continue
            with zf.open("files/" + name) as src:
                new_name = storage.save(name, File(src, name=os.path.basename(name)))
            restored += 1
            if new_name != name and model is not None:
                # the storage picked a different name: point the rows to it
                model._base_manager.filter(**{field.attname: name}).update(**{field.attname: new_name})
        except Exception as exc:
            failed += 1
            log.append(f"Could not restore file {name}: {str(exc)[:150]}")
    return restored, skipped, failed


def restore_backup(record, restored_by=""):
    """Replaces all site data with the backup's data, then puts back missing
    files. Runs in one database transaction: if anything fails, nothing
    changes. A data-only safety backup is made first."""
    s = BackupSettings.get_solo()
    s.restore_status, s.restore_message = "running", f"Restoring the backup from {timezone.localtime(record.created_at):%b %d, %Y %I:%M %p}…"
    s.restore_started_at, s.restore_finished_at = timezone.now(), None
    s.save()

    tmp_zip = None
    log = []
    try:
        tmp_zip = _download_to_temp(record)
        manifest = read_manifest(tmp_zip)
        check_compatible(manifest)

        safety = create_backup("safety", include_files=False, created_by=f"Before restore by {restored_by}".strip())
        if safety.status != "success":
            raise BackupError("Could not make the safety backup, so the restore was cancelled: " + safety.error)

        tmpdir = tempfile.mkdtemp(prefix="tunga-restore-")
        try:
            with zipfile.ZipFile(tmp_zip) as zf:
                data_path = os.path.join(tmpdir, "data.json")
                with zf.open("data.json") as src, open(data_path, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)

                with transaction.atomic():
                    tables = [m._meta.db_table for m in _models_to_clear()]
                    existing = set(connection.introspection.table_names())
                    tables = [t for t in tables if t in existing]
                    # CASCADE: also empties any leftover table that points at these
                    # (SiteBackup / BackupSettings have no links, so they stay).
                    sql = connection.ops.sql_flush(no_style(), tables, reset_sequences=True, allow_cascade=True)
                    connection.ops.execute_sql_flush(sql)
                    call_command("loaddata", data_path, ignorenonexistent=True, verbosity=0)

                restored, skipped, failed = _restore_files(zf, manifest, log)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        msg = (f"Restored the backup from {timezone.localtime(record.created_at):%b %d, %Y %I:%M %p}. "
               f"Files: {restored} put back, {skipped} already there"
               + (f", {failed} failed" if failed else "") + ".")
        if log:
            msg += " " + " ".join(log[:5])
        s = BackupSettings.get_solo()
        s.restore_status, s.restore_message, s.restore_finished_at = "success", msg, timezone.now()
        s.save()
        _notify("Site restored from backup", msg[:300], "success", "fa-solid fa-rotate-left")
        return True, msg
    except Exception as exc:
        traceback.print_exc()
        msg = f"Restore failed — nothing was changed. {exc}"[:2000]
        s = BackupSettings.get_solo()
        s.restore_status, s.restore_message, s.restore_finished_at = "failed", msg, timezone.now()
        s.save()
        _notify("Restore failed", msg[:300], "danger", "fa-solid fa-triangle-exclamation")
        return False, msg
    finally:
        if tmp_zip:
            try:
                os.remove(tmp_zip)
            except OSError:
                pass


def start_restore(record, restored_by=""):
    with _lock:
        if is_busy():
            return False
        s = BackupSettings.get_solo()
        s.restore_status, s.restore_started_at = "running", timezone.now()
        s.restore_message = "Starting the restore…"
        s.save()
    _in_background(restore_backup, record, restored_by)
    return True


def backup_health():
    """A warning for the dashboard / Backup page, or None if all is well."""
    try:
        last = SiteBackup.objects.exclude(kind="uploaded").exclude(status="running").first()
        last_ok = SiteBackup.objects.filter(status="success").exclude(kind__in=["uploaded", "safety"]).first()
        if last is not None and last.status == "failed":
            return {"level": "danger", "text": "The last backup failed: " + (last.error[:160] or "unknown error") + "."}
        if last_ok is None:
            return {"level": "warning", "text": "No backup of the website has been made yet."}
        age = timezone.now() - last_ok.created_at
        if age > timedelta(days=2):
            return {"level": "warning", "text": f"The last backup was {age.days} days ago."}
    except Exception:
        return None
    return None