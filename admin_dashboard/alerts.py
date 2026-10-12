"""Extra Super Admin notifications (the bell in the dashboard top bar) for
things that need action or show a problem:

1. Low client rating      - a citizen rated a service 1 or 2 stars
2. Unattended requests    - online submissions not opened for 3+ days
                            (checked once a day, when the Super Admin opens
                            the dashboard)
3. Email problems         - Brevo failed and the backup sender was used,
                            or no email could be sent at all
4. Security warnings      - an Office Representative or Super Admin account
                            was locked after too many wrong passwords/codes

The older ones (content waiting for approval, new messages, backups) are in
admin_dashboard/signals.py and admin_dashboard/backup.py.
"""
import threading
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

UNATTENDED_DAYS = 3
_once_lock = threading.Lock()   # emails are sent in background threads


def notify_once(title, description="", level="info", icon="fa-regular fa-bell", link_url="", within_hours=24):
    """Like notify_super_admins, but skipped if the same title was already
    sent within `within_hours`, so a problem doesn't flood the bell."""
    try:
        from .models import AdminNotification
        from .signals import notify_super_admins
        since = timezone.now() - timedelta(hours=within_hours)
        with _once_lock:
            if AdminNotification.objects.filter(title=title[:255], created_at__gte=since).exists():
                return False
            notify_super_admins(title, description, level, icon, link_url)
        return True
    except Exception:
        return False   # a notification must never break the page that sent it


# 1 ------------------------------------------------------------------------
def low_rating(feedback):
    """Called after a citizen rates a finished request (office_dashboard/submissions.py)."""
    if feedback.rating > 2:
        return
    try:
        from .signals import notify_super_admins
        s = feedback.submission
        office = s.form.office.name if s.form.office else "an office"
        desc = f"{office} · {s.form.title} · {s.reference_no}"
        if feedback.comment:
            desc += f' · "{feedback.comment[:200]}"'
        notify_super_admins(f"Low rating ({feedback.rating}★) for {office}", desc, "danger",
                            "fa-regular fa-face-frown",
                            reverse("admin_dashboard:ad_submissions") + f"?q={s.reference_no}")
    except Exception:
        pass


# 2 ------------------------------------------------------------------------
def check_unattended():
    """Once a day: online requests still "Submitted" (not opened) after
    UNATTENDED_DAYS days, per office. Tells the Super Admin and each office."""
    try:
        from .models import AdminNotification
        title = "Online requests not opened for 3+ days"
        today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        if AdminNotification.objects.filter(title=title, created_at__gte=today).exists():
            return
        from django.db.models import Count
        from office_dashboard.models import FormSubmission, OfficeRepresentative
        from office_dashboard.notifications import notify
        old = timezone.now() - timedelta(days=UNATTENDED_DAYS)
        rows = list(FormSubmission.objects.filter(status="submitted", submitted_at__lt=old)
                    .values("form__office_id", "form__office__name").annotate(n=Count("id"))
                    .order_by("-n"))
        if not rows:
            return
        total = sum(r["n"] for r in rows)
        offices = ", ".join(f'{r["form__office__name"]} ({r["n"]})' for r in rows[:6])
        notify_once(title, f"{total} waiting: {offices}", "warning", "fa-solid fa-hourglass-half",
                    reverse("admin_dashboard:ad_submissions") + "?status=submitted", within_hours=20)
        for r in rows:   # remind each office too
            rep = OfficeRepresentative.objects.filter(office_id=r["form__office_id"]).first()
            notify(rep, "submissions", f'{r["n"]} online request{"s" if r["n"] != 1 else ""} not opened for {UNATTENDED_DAYS}+ days',
                   "Please open them in Submissions and update their status.", level="warning",
                   link_url=reverse("office_dashboard:submissions") + "?status=submitted")
    except Exception:
        pass


# 3 ------------------------------------------------------------------------
def email_backup_used(brevo_error, backup_name):
    notify_once("Brevo could not send — emails are going through the backup",
                f"Using {backup_name}. Brevo said: {brevo_error[:300]}",
                "warning", "fa-solid fa-envelope-circle-check",
                reverse("admin_dashboard:ad_system_settings"), within_hours=24)


def email_failed(error):
    notify_once("Emails are NOT being sent",
                "Sign-up codes, password codes and status emails are failing. " + error[:300],
                "danger", "fa-solid fa-envelope-open-text",
                reverse("admin_dashboard:ad_system_settings"), within_hours=6)


# 4 ------------------------------------------------------------------------
def account_locked(kind, request, account):
    """Called by portal/security.record_failure when an account has just
    been locked. Only staff accounts (Office Representative / Super Admin)
    are reported; citizens forgetting their password is normal."""
    try:
        from django.contrib.auth.models import User
        from django.db.models import Q
        from office_dashboard.models import OfficeRepresentative
        from .models import SuperAdmin
        from portal.security import client_ip
        account = (account or "").strip()
        user = User.objects.filter(Q(email__iexact=account) | Q(username__iexact=account)).first()
        if user is None:
            return
        if SuperAdmin.objects.filter(user=user).exists():
            role = "Super Admin"
        else:
            rep = OfficeRepresentative.objects.filter(user=user).select_related("office").first()
            if rep is None:
                return
            role = f"Office Representative of {rep.office.name}"
        what = {"login": "wrong passwords at login", "password": "wrong current passwords",
                "reset-code": "wrong password-reset codes", "signup-code": "wrong verification codes"}.get(kind, "wrong tries")
        notify_once(f"Account locked: {user.email or user.username}",
                    f"{role}. Too many {what}; locked for 15 minutes. From IP {client_ip(request)}. "
                    "If this wasn't them, someone may be guessing the password.",
                    "danger", "fa-solid fa-user-lock",
                    reverse("admin_dashboard:ad_activity_log"), within_hours=1)
    except Exception:
        pass