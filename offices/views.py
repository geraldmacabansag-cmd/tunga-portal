from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Office
from office_dashboard.models import Announcement, DownloadableForm, Photo, Service
import re

@login_required
def mayor(request):
    return render(request, 'offices/mayorsoffice.html')


def _parse_leading_number(text):
    """Pulls a leading numeric value off a free-text processing-time string
    (e.g. "5 minutes" -> 5.0)."""
    if not text:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _compute_total_processing_time(steps):
    """Sums any steps whose processing time starts with a number, and
    appends the free-text ones (e.g. "Same day") as-is."""
    total = 0
    has_numeric = False
    text_parts = []
    for step in steps:
        n = _parse_leading_number(step.processing_time)
        if n is not None:
            total += n
            has_numeric = True
        elif step.processing_time:
            text_parts.append(step.processing_time)
    parts = []
    if has_numeric:
        parts.append(str(int(total)) if total == int(total) else f"{total:.2f}")
    parts.extend(text_parts)
    return " + ".join(parts) if parts else "—"


def _group_requirements_for_charter(requirements):
    """Requirements with no type of transaction come first as a plain list,
    then the rest are grouped under their type of transaction (alphabetically) —
    same grouping used in the office rep's and Super Admin's Citizen's Charter views."""
    general = [r for r in requirements if not r.transaction_type]
    grouped = {}
    for r in requirements:
        if r.transaction_type:
            grouped.setdefault(r.transaction_type, []).append(r)
    grouped_list = [(key, grouped[key]) for key in sorted(grouped.keys())]
    return general, grouped_list


def office_detail(request, slug):
    office = get_object_or_404(
        Office.objects.exclude(slug="lgu-super-admin"),
        slug=slug,
        is_visible=True,
    )
    rep = getattr(office, "representative", None)

    services = list(
        Service.objects.filter(office=office, status="published")
        .prefetch_related("requirements", "steps", "fees", "forms")
        .order_by("order", "name")
    )

    # Pre-compute each service's "Citizen's Charter" data (same shape the
    # office rep's Preview modal and the Super Admin's service page use) so
    # the floating modal on this page can render it directly, no JS needed.
    for s in services:
        steps = list(s.steps.all())
        requirements = list(s.requirements.all())
        general_requirements, grouped_requirements = _group_requirements_for_charter(requirements)
        s.charter_steps = steps
        s.charter_total_processing_time = _compute_total_processing_time(steps)
        s.charter_general_requirements = general_requirements
        s.charter_grouped_requirements = grouped_requirements
        s.charter_has_requirements = bool(requirements)
        s.charter_forms = s.forms.all().order_by('-date_uploaded')

    announcements = (
        Announcement.objects.filter(representative=rep, status="published")
        .order_by("-date_posted", "-created_at")[:5]
        if rep else []
    )

    forms = (
        DownloadableForm.objects.filter(office=office, status="published")
        .order_by("-date_uploaded")[:6]
    )

    photos = (
        Photo.objects.filter(representative=rep, status="published")
        .order_by("-created_at")[:4]
        if rep else []
    )

    return render(request, "offices/office_detail.html", {
        "office": office,
        "rep": rep,
        "services": services,
        "announcements": announcements,
        "forms": forms,
        "photos": photos,
    })