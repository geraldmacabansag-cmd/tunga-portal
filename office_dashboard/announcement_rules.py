"""Rules for saving an announcement — shared by the Office Representative and
Super Admin add/edit forms, so every path checks the same things.

Required: title, category, content (full description).
Priority always has a value (defaults to "Normal").
Optional: subtitle, image, author, expiration date — but an expiration date,
if given, must be in the future.
"""
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Announcement

PRIORITIES = {value for value, _ in Announcement.PRIORITY_CHOICES}


def clean_announcement(post, is_new=True, current_expiration=None, must_be_future=False):
    """Returns (errors, data). errors is a list of messages to show; data is
    the cleaned values to put on the Announcement when there are no errors.
    must_be_future=True: an announcement that expired before it was approved —
    the office has to give it a new expiration date in the future (or none)."""
    errors = []

    title = (post.get("title") or "").strip()
    category = (post.get("category") or "").strip()
    content = (post.get("content") or "").strip()
    priority = post.get("priority") or "Normal"

    if not title:
        errors.append("Title is required.")
    if not category:
        errors.append("Category is required.")
    if not content:
        errors.append("Content / full description is required.")
    if priority not in PRIORITIES:
        priority = "Normal"

    expiration = None
    raw = (post.get("expiration_date") or "").strip()
    if raw:
        expiration = parse_datetime(raw)
        if expiration is None:
            errors.append("Expiration date is not a valid date and time.")
        else:
            if timezone.is_naive(expiration):
                expiration = timezone.make_aware(expiration)
            # A new announcement can't already be expired. When editing, an
            # unchanged old date is allowed (the rep may just be fixing a typo).
            unchanged = current_expiration is not None and abs((expiration - current_expiration).total_seconds()) < 60
            if expiration <= timezone.now() and (is_new or must_be_future or not unchanged):
                errors.append("This announcement has expired. Set a new expiration date in the future (or leave it empty if it doesn't expire)."
                              if must_be_future else
                              "Expiration date must be in the future (or leave it empty if it doesn't expire).")

    return errors, {
        "title": title,
        "subtitle": (post.get("subtitle") or "").strip(),
        "category": category,
        "content": content,
        "author": (post.get("author") or "").strip(),
        "expiration_date": expiration,
        "priority": priority,
    }


def expire_overdue(force=False):
    """Announcements still waiting for approval (pending / returned) whose
    expiration date has passed become "expired": they are not published, they
    leave the Approval Center and show in the office's "Expired" tab, where
    the office can set a new date (it then goes back to pending). The office
    gets a notification. Cheap; runs at most once a minute unless force=True
    (called from the Announcements pages, the Approval Center and the
    Approval Center badge)."""
    from django.core.cache import cache
    if not force and not cache.add("announcements-expire-check", 1, 60):
        return 0
    _mark_past_events()
    due = list(Announcement.objects.filter(status__in=["pending", "returned"],
                                           expiration_date__isnull=False,
                                           expiration_date__lte=timezone.now())
               .select_related("representative"))
    if not due:
        return 0
    Announcement.objects.filter(pk__in=[a.pk for a in due]).update(status="expired")
    from django.urls import reverse
    from .notifications import notify
    for a in due:
        notify(a.representative, "approvals",
               title=f'"{a.title}" expired before it was approved',
               description="It was not published. Open it in the Expired tab, set a new expiration date and save to send it for approval again.",
               level="warning",
               link_url=reverse("office_dashboard:rep_announce") + "?status=expired")
    return len(due)


def _mark_past_events():
    """Events still waiting for approval (pending / returned) whose date is
    over become "past" (not published): they leave the Approval Center and
    show in the office's "Past" tab, where the office can give them a new
    date (they then go back to pending). The office gets a notification."""
    from django.urls import reverse
    from .models import Event
    from .notifications import notify
    due = list(Event.objects.filter(status__in=["pending", "returned"], event_date__isnull=False,
                                    event_date__lt=timezone.localdate()).select_related("representative"))
    if not due:
        return 0
    Event.objects.filter(pk__in=[e.pk for e in due]).update(status="past")
    for e in due:
        notify(e.representative, "approvals",
               title=f'"{e.title}" passed before it was approved',
               description="The event date is over and it was not published. Open it in the Past tab, set a new date and save to send it for approval again.",
               level="warning",
               link_url=reverse("office_dashboard:event") + "?status=past")
    return len(due)


def event_date_problem(event_date):
    """A new event (or one that passed before it was approved) must be today or later."""
    if event_date and event_date < timezone.localdate():
        return "The event date has already passed. Choose today or a later date."
    return ""