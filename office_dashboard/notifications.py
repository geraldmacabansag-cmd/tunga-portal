"""Sends an office representative a dashboard notification, respecting the
switches on their My Account page ("Notification Preferences")."""
from datetime import timedelta

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from .models import (Announcement, DownloadableForm, Event, Message, NewsUpdate,
                     Notification, OfficeRepresentative, Photo, Service)

# preference name -> field on OfficeRepresentative
PREFERENCES = {
    "approvals": "notify_approvals",
    "messages": "notify_messages",
    "weekly_summary": "notify_weekly_summary",
    "announcements": "notify_announcements",
}


def wants(rep, kind):
    """True if this rep wants this kind of notification. Kinds without a
    switch (e.g. "account") are always sent."""
    field = PREFERENCES.get(kind)
    return True if field is None else bool(getattr(rep, field, True))


def notify(rep, kind, title, description="", level="info", link_url=""):
    """Creates the notification only if the rep has that kind switched on."""
    if rep is None or not wants(rep, kind):
        return None
    return Notification.objects.create(
        representative=rep, title=title, description=description[:500],
        level=level, link_url=link_url,
    )


def notify_all_reps(kind, title, description="", level="info", link_url="", exclude_slug="lgu-super-admin"):
    """Sends to every office representative who has this kind switched on
    (not the Super Admin's own internal "LGU Super Admin" record)."""
    reps = OfficeRepresentative.objects.exclude(office__slug=exclude_slug).filter(**{PREFERENCES[kind]: True})
    Notification.objects.bulk_create([
        Notification(representative=r, title=title, description=description[:500], level=level, link_url=link_url)
        for r in reps
    ])


def maybe_send_weekly_summary(rep):
    """Called when the rep opens any dashboard page: if "Weekly summary" is
    on and 7 days have passed since the last one, add a digest notification."""
    if not rep.notify_weekly_summary:
        return
    now = timezone.now()
    if rep.last_weekly_summary_at and now - rep.last_weekly_summary_at < timedelta(days=7):
        return
    if rep.last_weekly_summary_at is None:
        # Just switched on: the first summary arrives a week from now.
        OfficeRepresentative.objects.filter(pk=rep.pk).update(last_weekly_summary_at=now)
        rep.last_weekly_summary_at = now
        return

    content = [
        Announcement.objects.filter(representative=rep),
        NewsUpdate.objects.filter(representative=rep),
        Event.objects.filter(representative=rep),
        Photo.objects.filter(representative=rep),
        DownloadableForm.objects.filter(office=rep.office),
        Service.objects.filter(office=rep.office),
    ]
    published = sum(qs.filter(status="published").count() for qs in content)
    pending = sum(qs.filter(status="pending").count() for qs in content)
    returned = sum(qs.filter(status="returned").count() for qs in content)
    views = sum(
        (qs.filter(status="published").aggregate(t=Sum("views"))["t"] or 0)
        for qs in (Announcement.objects.filter(representative=rep), NewsUpdate.objects.filter(representative=rep))
    )
    unread = Message.objects.filter(representative=rep, sender=Message.SENDER_ADMIN, read_at__isnull=True).count()

    parts = [f"{published} published", f"{pending} waiting for approval"]
    if returned:
        parts.append(f"{returned} returned for revision")
    parts.append(f"{views:,} total views on your announcements & news")
    if unread:
        parts.append(f"{unread} unread message{'s' if unread != 1 else ''}")

    Notification.objects.create(
        representative=rep, title="Your weekly summary",
        description=" · ".join(parts) + ".", level="info",
        link_url=reverse("office_dashboard:dashboard"),
    )
    OfficeRepresentative.objects.filter(pk=rep.pk).update(last_weekly_summary_at=now)
    rep.last_weekly_summary_at = now