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


def clean_announcement(post, is_new=True, current_expiration=None):
    """Returns (errors, data). errors is a list of messages to show; data is
    the cleaned values to put on the Announcement when there are no errors."""
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
            if expiration <= timezone.now() and (is_new or not unchanged):
                errors.append("Expiration date must be in the future (or leave it empty if it doesn't expire).")

    return errors, {
        "title": title,
        "subtitle": (post.get("subtitle") or "").strip(),
        "category": category,
        "content": content,
        "author": (post.get("author") or "").strip(),
        "expiration_date": expiration,
        "priority": priority,
    }