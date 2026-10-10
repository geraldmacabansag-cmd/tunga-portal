from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AdminNotification
from .models import SuperAdmin, SiteContactInfo, EmergencyContact, EmailProviderSettings, QuickLink, AboutPageContent, HistoryMilestone, AboutOfficial, Barangay
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from office_dashboard.models import Announcement, NewsUpdate, Event, DownloadableForm, FormField, Photo, Album, Service, OfficeRepresentative, Notification, ServiceEditSettings, ActivityLog, Message
from office_dashboard.models import log_activity
from office_dashboard.notifications import notify, notify_all_reps
from office_dashboard.announcement_rules import clean_announcement
from offices.models import Office
from django.http import Http404, FileResponse, HttpResponse, JsonResponse
from offices.pdf_serve import pdf_response
from office_dashboard.form_fields import fields_json, save_fields
from datetime import timedelta
import csv
import io
from office_dashboard.views import FORM_CATEGORY_CHOICES, serialize_chat_message, MESSAGE_MAX_LENGTH
from office_dashboard.views import org_chart_page
from office_dashboard.content_photos import save_content_photos
from office_dashboard.models import OrgChartNode
from django.db.models import Count
from django.utils.text import slugify
import secrets
import json
import re
from django.urls import reverse
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def _parse_leading_number(text):
    """Pulls a leading numeric value off a free-text processing-time string
    (e.g. "5 minutes" -> 5.0), mirroring the JS parseLeadingNumber() used on
    the office rep's own Client Steps table, so the two totals agree."""
    if not text:
        return None
    match = re.match(r"\s*(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None


def _compute_total_processing_time(steps):
    """Mirrors computeTotalProcessingTime() in office-rep-service-details.html:
    sums any steps whose processing time starts with a number, and appends
    the free-text ones (e.g. "Same day") as-is."""
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

# The synthetic office created by get_or_create_lgu_rep() so the Super
# Admin can post content through the same representative/office FK the
# content models require. It's an internal bookkeeping record, not a
# real municipal office — it must never appear in office listings.
LGU_SUPER_ADMIN_SLUG = "lgu-super-admin"


def get_or_create_lgu_rep(user):
    office, _ = Office.objects.get_or_create(
        slug="lgu-super-admin",
        defaults={"name": "LGU Super Admin"}
    )
    rep, _ = OfficeRepresentative.objects.get_or_create(
        user=user,
        defaults={"office": office, "position": "Super Administrator"}
    )
    return rep

def super_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not SuperAdmin.objects.filter(user=request.user).exists():
            messages.error(request, "You don't have access to the Super Admin dashboard.")
            return redirect("home")
        if request.method != "POST":
            # Automatic daily backup: starts in the background when it's due.
            from .backup import maybe_start_auto_backup
            maybe_start_auto_backup()
            return view_func(request, *args, **kwargs)

        # Activity log: every Super Admin action already ends with a
        # messages.success(...) line ("X was approved and published.").
        # After the view runs, each new success message is saved to the
        # Activity Logs, so no view needs its own log_activity() call.
        before_msgs = len(_queued_messages(request))
        last_log = ActivityLog.objects.order_by("-id").values_list("id", flat=True).first() or 0
        response = view_func(request, *args, **kwargs)
        try:
            new_msgs = _queued_messages(request)[before_msgs:]
            already_logged = ActivityLog.objects.filter(id__gt=last_log).exists()
            texts = [str(m.message) for m in new_msgs if m.level == messages.SUCCESS]
            if texts and not already_logged:
                rep = get_or_create_lgu_rep(request.user)
                for text in texts:
                    _log_admin_action(rep, view_func.__name__, text)
        except Exception:
            pass  # logging must never break the action itself
        return response
    return wrapper


def _queued_messages(request):
    storage = getattr(request, "_messages", None)
    return list(getattr(storage, "_queued_messages", []) or [])


# Which part of the dashboard a view belongs to, checked in this order
# (first word found in the view's name wins):
# (word, area title, category, icon, color)
ADMIN_LOG_AREAS = [
    ("backup", "Backup & Restore", "security", "fa-solid fa-database", "var(--blue-600)"),
    ("approval", "Approval Center", "content", "fa-solid fa-square-check", "var(--green-600)"),
    ("password", "Password changed", "security", "fa-solid fa-lock", "var(--amber-600)"),
    ("my_account", "Account updated", "account", "fa-solid fa-user", "var(--gray-500)"),
    ("system_setting", "System settings", "security", "fa-solid fa-gear", "var(--gray-500)"),
    ("admin_archive", "Archive", "content", "fa-solid fa-box-archive", "var(--amber-600)"),
    ("photo", "Gallery", "content", "fa-regular fa-image", "#12b3c4"),
    ("album", "Gallery", "content", "fa-regular fa-image", "#12b3c4"),
    ("announcement", "Announcements", "content", "fa-solid fa-bullhorn", "var(--blue-600)"),
    ("news", "News", "content", "fa-regular fa-newspaper", "#12b3c4"),
    ("event", "Events", "content", "fa-solid fa-calendar-days", "#7c4fe0"),
    ("form", "Downloadable forms", "content", "fa-solid fa-file-arrow-down", "var(--blue-600)"),
    ("rep", "Representatives", "account", "fa-solid fa-user-tie", "var(--blue-600)"),
    ("office", "Offices", "content", "fa-solid fa-building", "var(--blue-600)"),
    ("service", "Services", "content", "fa-solid fa-list-check", "var(--blue-600)"),
    ("user", "Users", "account", "fa-solid fa-users", "var(--blue-600)"),
    ("role", "Users", "account", "fa-solid fa-users", "var(--blue-600)"),
    ("quicklink", "Homepage", "content", "fa-solid fa-house", "var(--blue-600)"),
    ("homepage", "Homepage", "content", "fa-solid fa-house", "var(--blue-600)"),
    ("about", "About page", "content", "fa-solid fa-landmark", "var(--blue-600)"),
    ("contact", "Emergency contacts", "content", "fa-solid fa-phone", "var(--red-600)"),
    ("web_setting", "Website settings", "content", "fa-solid fa-sliders", "var(--gray-500)"),
    ("org_chart", "Org chart", "content", "fa-solid fa-sitemap", "var(--blue-600)"),
    ("map", "Interactive map", "content", "fa-solid fa-map-location-dot", "var(--green-600)"),
]


def _log_admin_action(rep, view_name, text):
    title, category, icon, color = "Settings updated", "content", "fa-solid fa-circle-info", "var(--blue-600)"
    for word, a_title, a_cat, a_icon, a_color in ADMIN_LOG_AREAS:
        if word in view_name:
            title, category, icon, color = a_title, a_cat, a_icon, a_color
            break
    low = text.lower()
    if any(w in low for w in ("deleted", "removed", "rejected", "deactivated")):
        color = "var(--red-600)"
    elif any(w in low for w in ("archived", "returned", "turned off", "hidden")):
        color = "var(--amber-600)"
    elif any(w in low for w in ("approved", "published", "activated", "restored")):
        color = "var(--green-600)"
    log_activity(rep, title, text[:500], category, icon, color)


def activity_dot(color):
    """Turns an ActivityLog.icon_color into one of the 4 dot colors."""
    c = (color or "").lower()
    if "green" in c:
        return "green"
    if "red" in c:
        return "red"
    if "amber" in c:
        return "amber"
    return "blue"


def activity_tone(color):
    """Turns an ActivityLog.icon_color into a CSS class name for the icon box."""
    c = (color or "").lower()
    for word, tone in (("green", "green"), ("red", "red"), ("amber", "amber"), ("gray", "gray"),
                       ("12b3c4", "teal"), ("7c4fe0", "purple")):
        if word in c:
            return tone
    return "blue"


def activity_when(dt):
    """Short relative time for the dashboard: "Just now", "5 minutes ago", "2 days ago"."""
    from django.utils.timesince import timesince
    first = timesince(dt).split(",")[0]
    return "Just now" if first.startswith("0") else f"{first} ago"


def activity_actor(log):
    """Who did it: the person's name, plus their office (or "Super Admin")."""
    rep = log.representative
    user = rep.user
    name = user.get_full_name() or user.username
    office = rep.office
    if not office or office.slug == LGU_SUPER_ADMIN_SLUG:
        return name, "Super Admin"
    return name, office.name


# Icon/color for each pending-item type shown in the dashboard's "Awaiting
# your approval" panel. Kept separate from TYPE_META (used by the Approval
# Center) because that panel only has 4 accent colors available (blue/green/
# amber/red), not the 6 tag colors TYPE_META uses.
DASH_APPROVAL_META = {
    "Announcement": {"color": "blue", "icon": "fa-solid fa-bullhorn"},
    "News": {"color": "amber", "icon": "fa-regular fa-newspaper"},
    "Event": {"color": "green", "icon": "fa-regular fa-calendar"},
    "Form": {"color": "amber", "icon": "fa-solid fa-file-arrow-down"},
    "Gallery": {"color": "red", "icon": "fa-regular fa-image"},
    "Service": {"color": "red", "icon": "fa-solid fa-list-check"},
}


@super_admin_required
def dashboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
 
    offices = Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG)
 
    # ---- Pending approvals (same statuses as the Approval Center) ----
    pending_announcements = Announcement.objects.filter(status__in=["pending", "returned"])
    pending_news = NewsUpdate.objects.filter(status__in=["pending", "returned"])
    pending_events = Event.objects.filter(status__in=["pending", "returned"])
    pending_forms = DownloadableForm.objects.filter(status__in=["pending", "returned"])
    pending_photos = Photo.objects.filter(status__in=["pending", "returned"])
    pending_services = Service.objects.filter(status__in=["pending", "returned"])
 
    pending_total = (
        pending_announcements.count()
        + pending_news.count()
        + pending_events.count()
        + pending_forms.count()
        + pending_photos.count()
        + pending_services.count()
    )
    pending_today = (
        pending_announcements.filter(created_at__date=today).count()
        + pending_news.filter(created_at__date=today).count()
        + pending_events.filter(created_at__date=today).count()
        + pending_forms.filter(date_uploaded__date=today).count()
        + pending_photos.filter(created_at__date=today).count()
        + pending_services.filter(published_at__date=today).count()
    )
 
    # ---- Awaiting your approval (same pending queries as above, merged into
    # one "what needs a look" list for the dashboard panel, newest first) ----
    recent_pending = []
    for a in pending_announcements.select_related('representative__office'):
        recent_pending.append({
            'item_type': 'Announcement', 'pk': a.pk,
            'title': f'New announcement: "{a.title}"',
            'office': a.representative.office.name if a.representative and a.representative.office else '—',
            'date': a.created_at,
        })
    for n in pending_news.select_related('representative__office'):
        recent_pending.append({
            'item_type': 'News', 'pk': n.pk,
            'title': f'News update: "{n.title}"',
            'office': n.representative.office.name if n.representative and n.representative.office else '—',
            'date': n.created_at,
        })
    for e in pending_events.select_related('representative__office'):
        recent_pending.append({
            'item_type': 'Event', 'pk': e.pk,
            'title': f'New event: "{e.title}"',
            'office': e.representative.office.name if e.representative and e.representative.office else '—',
            'date': e.created_at,
        })
    for f in pending_forms.select_related('office'):
        recent_pending.append({
            'item_type': 'Form', 'pk': f.pk,
            'title': f'Updated form: "{f.title}"',
            'office': f.office.name if f.office else '—',
            'date': f.date_uploaded,
        })
    for p in pending_photos.select_related('representative__office'):
        recent_pending.append({
            'item_type': 'Gallery', 'pk': p.pk,
            'title': f'New photo: "{p.title}"',
            'office': p.representative.office.name if p.representative and p.representative.office else '—',
            'date': p.created_at,
        })
    for s in pending_services.select_related('office'):
        recent_pending.append({
            'item_type': 'Service', 'pk': s.pk,
            'title': f'New service: "{s.name}"',
            'office': s.office.name if s.office else '—',
            'date': s.published_at,
        })

    for item in recent_pending:
        meta = DASH_APPROVAL_META.get(item['item_type'], {})
        item['icon_color'] = meta.get('color', 'blue')
        item['icon'] = meta.get('icon', 'fa-solid fa-file')

    recent_pending.sort(key=lambda i: i['date'] or timezone.now(), reverse=True)
    recent_pending = recent_pending[:4]

    # ---- Registered residents (ordinary citizen accounts only) ----
    resident_qs = User.objects.filter(is_staff=False, is_superuser=False, office_rep__isnull=True)
    residents_total = resident_qs.count()
    residents_new_this_month = resident_qs.filter(date_joined__date__gte=month_start).count()
 
    # ---- Published announcements ----
    published_announcements = Announcement.objects.filter(status="published")
    announcements_total = published_announcements.count()
    announcements_this_week = published_announcements.filter(created_at__date__gte=week_start).count()
 
    # ---- Active (published) services ----
    published_services = Service.objects.filter(status="published")
    services_total = published_services.count()
    services_office_count = published_services.values("office_id").distinct().count()
 
    # ---- Office activity table ----
    office_rows = []
    for office in offices:
        services_count = Service.objects.filter(office=office).count()
        office_pending_count = (
            Announcement.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + NewsUpdate.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + Event.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + DownloadableForm.objects.filter(status__in=["pending", "returned"], office=office).count()
            + Photo.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + Service.objects.filter(status__in=["pending", "returned"], office=office).count()
        )
        office_rows.append({
            "office": office,
            "services_count": services_count,
            "pending_count": office_pending_count,
        })

    # Drop offices that have nothing to show at all (no services listed and
    # nothing pending) — otherwise an office that has simply never been set
    # up yet still took one of the 5 slots below just because the table was
    # sorted and sliced without checking whether there was anything to show.
    office_rows = [r for r in office_rows if r["services_count"] > 0 or r["pending_count"] > 0]

    # Busiest offices first: whoever needs the most attention, then whoever
    # has the most services listed.
    office_rows.sort(key=lambda r: (-r["pending_count"], -r["services_count"]))
    office_rows = office_rows[:5]

    # ---- Recent activity (latest 8 entries from all offices + Super Admin) ----
    recent_activity = []
    for log in ActivityLog.objects.select_related("representative__user", "representative__office")[:8]:
        name, office_label = activity_actor(log)
        recent_activity.append({
            "log": log, "name": name, "office": office_label, "dot": activity_dot(log.icon_color),
            "when": activity_when(log.created_at),
        })

    # ---- Backup reminder ----
    from .backup import backup_health
    backup_warning = backup_health()

    return render(request, "admin_dashboard/super-admin-dashboard.html", {
        "backup_warning": backup_warning,
        "recent_activity": recent_activity,
        "pending_total": pending_total,
        "pending_today": pending_today,
        "recent_pending": recent_pending,
        "residents_total": residents_total,
        "residents_new_this_month": residents_new_this_month,
        "announcements_total": announcements_total,
        "announcements_this_week": announcements_this_week,
        "services_total": services_total,
        "services_office_count": services_office_count,
        "office_rows": office_rows,
    })


@super_admin_required
def admin_my_account(request):
    """Mirrors office_dashboard's my_account view, but for the Super Admin's
    own User account plus the SuperAdmin model's own mobile_number/photo
    fields."""
    super_admin = SuperAdmin.objects.get(user=request.user)

    # The synthetic "LGU Super Admin" Office (see get_or_create_lgu_rep()) —
    # its name is what shows up as the office label on everything the Super
    # Admin posts directly (announcements, news, events, forms, gallery
    # uploads), so it's editable right here alongside the rest of the Super
    # Admin's own profile rather than on the real Offices management page
    # (which deliberately excludes this bookkeeping-only record).
    lgu_office, _ = Office.objects.get_or_create(
        slug=LGU_SUPER_ADMIN_SLUG,
        defaults={"name": "LGU Super Admin"},
    )

    if request.method == "POST":
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        office_name = request.POST.get('office_name', '').strip()

        if not full_name:
            messages.error(request, "Full name is required.")
        elif not office_name:
            messages.error(request, "Office/Department name is required.")
        else:
            name_parts = full_name.split(' ', 1)
            request.user.first_name = name_parts[0]
            request.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            request.user.email = email
            request.user.save()

            super_admin.mobile_number = request.POST.get('mobile_number', '')
            uploaded_photo = request.FILES.get('photo')
            if uploaded_photo:
                super_admin.photo = uploaded_photo

            try:
                # SuperAdmin.save() calls self.full_clean() internally (it's
                # how the "only one Super Admin" rule is enforced) — that
                # means a freshly uploaded photo also gets Django's normal
                # ImageField validation (valid image, readable by Pillow)
                # run on it right here, and if it fails, this raises
                # ValidationError instead of silently doing nothing.
                super_admin.save()
            except ValidationError as e:
                error_text = " ".join(
                    msg for messages_list in e.message_dict.values() for msg in messages_list
                ) if hasattr(e, 'message_dict') else " ".join(e.messages)
                messages.error(request, f"Could not save your changes: {error_text}")
            else:
                if lgu_office.name != office_name:
                    lgu_office.name = office_name
                    lgu_office.save()
                messages.success(request, "Account details updated.")
        return redirect('admin_dashboard:admin_account')

    return render(request, "admin_dashboard/super-admin-my-account.html", {
        "super_admin": super_admin,
        "lgu_office": lgu_office,
    })


@super_admin_required
def admin_change_password(request):
    if request.method == "POST":
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
        else:
            try:
                validate_password(new_password, user=request.user)
            except ValidationError as e:
                for err in e.messages:
                    messages.error(request, err)
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)  # keeps them logged in
                messages.success(request, "Password updated successfully.")

        return redirect('admin_dashboard:admin_change_pass')

    return render(request, "admin_dashboard/super-admin-change-password.html")


TYPE_META = {
    "Announcement": {"tag_class": "tag-blue", "icon": "fa-solid fa-bullhorn", "thumb_class": "tag-blue"},
    "Form": {"tag_class": "tag-green", "icon": "fa-regular fa-file-lines", "thumb_class": "tag-green"},
    "News": {"tag_class": "tag-purple", "icon": "fa-regular fa-newspaper", "thumb_class": "tag-purple"},
    "Event": {"tag_class": "tag-blue", "icon": "fa-regular fa-calendar", "thumb_class": "tag-blue"},
    "Gallery": {"tag_class": "tag-pink", "icon": "fa-regular fa-image", "thumb_class": "tag-pink"},
    "Service": {"tag_class": "tag-indigo", "icon": "fa-solid fa-list-check", "thumb_class": "tag-indigo"},
}

STATUS_BADGE = {"pending": "badge-amber", "returned": "badge-red"}


@super_admin_required
def admin_approval_center(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', 'all')

    items = []

    for a in Announcement.objects.filter(status__in=['pending', 'returned']).select_related('representative__office'):
        items.append({'pk': a.pk, 'title': a.title, 'type': 'Announcement',
                       'office': a.representative.office.name if a.representative.office else '—',
                       'date': a.created_at, 'status': a.status})

    for n in NewsUpdate.objects.filter(status__in=['pending', 'returned']).select_related('representative__office'):
        items.append({'pk': n.pk, 'title': n.title, 'type': 'News',
                       'office': n.representative.office.name if n.representative.office else '—',
                       'date': n.created_at, 'status': n.status})

    for e in Event.objects.filter(status__in=['pending', 'returned']).select_related('representative__office'):
        items.append({'pk': e.pk, 'title': e.title, 'type': 'Event',
                       'office': e.representative.office.name if e.representative.office else '—',
                       'date': e.created_at, 'status': e.status})

    for f in DownloadableForm.objects.filter(status__in=['pending', 'returned']).select_related('office'):
        items.append({'pk': f.pk, 'title': f.title, 'type': 'Form',
                       'office': f.office.name if f.office else '—',
                       'date': f.date_uploaded, 'status': f.status})

    for p in Photo.objects.filter(status__in=['pending', 'returned']).select_related('representative__office'):
        items.append({'pk': p.pk, 'title': p.title, 'type': 'Gallery',
                       'office': p.representative.office.name if p.representative.office else '—',
                       'date': p.created_at, 'status': p.status})

    for s in Service.objects.filter(status__in=['pending', 'returned']).select_related('office'):
        items.append({'pk': s.pk, 'title': s.name, 'type': 'Service',
                       'office': s.office.name if s.office else '—',
                       'date': s.published_at, 'status': s.status})

    type_counts = {}
    for item in items:
        type_counts[item['type']] = type_counts.get(item['type'], 0) + 1

    filtered = items
    if type_filter != 'all':
        filtered = [i for i in filtered if i['type'] == type_filter]
    if status_filter:
        filtered = [i for i in filtered if i['status'] == status_filter]
    if q:
        ql = q.lower()
        filtered = [i for i in filtered if ql in i['title'].lower()]

    filtered.sort(key=lambda i: i['date'] or timezone.now(), reverse=True)

    for item in filtered:
        meta = TYPE_META.get(item['type'], {})
        item['tag_class'] = meta.get('tag_class', 'tag-gray')
        item['icon'] = meta.get('icon', 'fa-solid fa-file')
        item['thumb_class'] = meta.get('thumb_class', 'tag-gray')
        item['badge_class'] = STATUS_BADGE.get(item['status'], 'badge-gray')
        item['status_label'] = 'Returned' if item['status'] == 'returned' else 'Pending'

    paginator = Paginator(filtered, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "admin_dashboard/super-admin-approval-center.html", {
        "page_obj": page_obj,
        "total_count": len(items),
        "type_counts": type_counts,
        "current_q": q,
        "current_status": status_filter,
        "current_type": type_filter,
    })

MODEL_MAP = {
    'Announcement': Announcement,
    'News': NewsUpdate,
    'Event': Event,
    'Form': DownloadableForm,
    'Gallery': Photo,
    'Service': Service,
}

def _stamp_published_date(obj):
    """Sets the "date published" field to today, the moment the Super Admin
    actually approves/publishes (or re-publishes from the archive) a piece
    of content. This is the ONLY place these fields are ever set — there is
    no manual date input anywhere for them anymore. Announcement uses
    date_posted, NewsUpdate uses date_published; anything else (Event, Form,
    Gallery) has no such field and is left alone. Service records the exact
    approval time in approved_at."""
    if isinstance(obj, Announcement):
        obj.date_posted = timezone.localdate()
    elif isinstance(obj, NewsUpdate):
        obj.date_published = timezone.localdate()
    elif isinstance(obj, Service):
        obj.approved_at = timezone.now()

@super_admin_required
def admin_approval_details(request, item_type, pk):
    model = MODEL_MAP.get(item_type)
    if model is None:
        raise Http404("Unknown submission type.")

    if model is DownloadableForm:
        obj = get_object_or_404(model.objects.select_related('office'), pk=pk)
        office = obj.office
        submitted_by_name = obj.uploaded_by or "—"
        notify_rep = getattr(office, 'representative', None)
    elif model is Service:
        obj = get_object_or_404(model.objects.select_related('office'), pk=pk)
        office = obj.office
        rep = getattr(office, 'representative', None)
        submitted_by_name = (rep.user.get_full_name() or rep.user.username) if rep else "—"
        notify_rep = rep
    else:
        obj = get_object_or_404(model.objects.select_related('representative__office', 'representative__user'), pk=pk)
        office = obj.representative.office
        submitted_by_name = obj.representative.user.get_full_name() or obj.representative.user.username
        notify_rep = obj.representative

    obj_label = getattr(obj, 'title', None) or getattr(obj, 'name', '')

    REP_PAGE_URL_NAMES = {
        'Announcement': 'office_dashboard:rep_announce',
        'News': 'office_dashboard:news_update',
        'Event': 'office_dashboard:event',
        'Form': 'office_dashboard:downloadable_form',
        'Gallery': 'office_dashboard:gallery',
        'Service': 'office_dashboard:services',
    }
    url_name = REP_PAGE_URL_NAMES.get(item_type)
    content_link_url = reverse(url_name) if url_name else ''

    if request.method == "POST":
        action = request.POST.get('action')
        note = request.POST.get('note', '').strip()

        if note:
            obj.admin_note = note

        display_name = getattr(obj, 'title', None) or getattr(obj, 'name', '')

        if action == 'approve':
            obj.status = 'published'
            _stamp_published_date(obj)
            messages.success(request, f'"{display_name}" was approved and published.')
            if notify_rep:
                notify(
                    notify_rep, 'approvals',
                    link_url=content_link_url,
                    title=f'"{display_name}" was approved',
                    description=f'Your {item_type.lower()} submission is now published on the public website.',
                    level='success',
                )
        elif action == 'return':
            obj.status = 'returned'
            messages.success(request, f'"{display_name}" was returned for revision.')
            if notify_rep:
                notify(
                    notify_rep, 'approvals',
                    link_url=content_link_url,
                    title=f'"{display_name}" was returned for revision',
                    description=note or f'Your {item_type.lower()} submission needs changes before it can be published. Check the admin note for details.',
                    level='warning',
                )
        elif action == 'reject':
            obj.status = 'reject'
            messages.success(request, f'"{display_name}" was rejected.')
            if notify_rep:
                notify(
                    notify_rep, 'approvals',
                    link_url=content_link_url,
                    title=f'"{display_name}" was rejected',
                    description=note or f'Your {item_type.lower()} submission was not approved.',
                    level='danger',
                )
        obj.save()
        return redirect('admin_dashboard:approval_center')

    date_submitted = getattr(obj, 'created_at', None) or getattr(obj, 'date_uploaded', None) or getattr(obj, 'published_at', None)

    extra_context = {}
    if model is Service:
        steps = list(obj.steps.all())
        reminder_lines = [line.strip() for line in (obj.reminders or '').splitlines() if line.strip()]
        extra_context = {
            "service_steps": steps,
            "service_total_processing_time": _compute_total_processing_time(steps),
            "service_requirements": obj.requirements.all(),
            "service_forms": obj.forms.all(),
            "service_reminder_lines": reminder_lines,
        }

    return render(request, "admin_dashboard/super-admin-approval-details.html", {
        "obj": obj,
        "obj_label": obj_label,
        "item_type": item_type,
        "office": office,
        "submitted_by_name": submitted_by_name,
        "date_submitted": date_submitted,
        "tag_class": TYPE_META.get(item_type, {}).get('tag_class', 'tag-gray'),
        **extra_context,
    })

ANNOUNCEMENT_STATUS_BADGE = {
    "pending": "badge-amber",
    "published": "badge-green",
    "returned": "badge-red",
    "reject": "badge-red",
    "archive": "badge-gray",
}

@super_admin_required
def admin_announcement(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'newest')

    qs = (Announcement.objects
          .select_related('representative__office')
          .filter(status='published'))

    if q:
        qs = qs.filter(title__icontains=q)
    if category:
        qs = qs.filter(category=category)

    if sort == 'oldest':
        qs = qs.order_by('date_posted', 'created_at')
    elif sort == 'most_viewed':
        qs = qs.order_by('-views')
    else:
        sort = 'newest'
        qs = qs.order_by('-date_posted', '-created_at')

    total_count = qs.count()
    total_views = qs.aggregate(total=Sum('views'))['total'] or 0

    announcements = list(qs)
    for a in announcements:
        a.badge_class = ANNOUNCEMENT_STATUS_BADGE.get(a.status, 'badge-gray')

    return render(request, "admin_dashboard/super-admin-announcements.html", {
        "announcements": announcements,
        "total_count": total_count,
        "total_views": total_views,
        "current_q": q,
        "current_category": category,
        "current_sort": sort,
        "offices_with_reps": Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).filter(representative__isnull=False).select_related('representative').order_by('name'),
        "lgu_office_name": Office.objects.filter(slug=LGU_SUPER_ADMIN_SLUG).values_list('name', flat=True).first() or "LGU Super Admin",
    })

@super_admin_required
def admin_create_announcement(request):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        office_choice = request.POST.get('office')

        if office_choice == 'super_admin':
            rep = get_or_create_lgu_rep(request.user)
        else:
            office = Office.objects.filter(pk=office_choice).select_related('representative').first() if office_choice else None
            rep = getattr(office, 'representative', None) if office else None

        errors, data = clean_announcement(request.POST, is_new=True)
        if errors:
            for err in errors:
                messages.error(request, err)
        elif not rep:
            messages.error(request, "Please select an office with an assigned representative.")
        else:
            ann = Announcement.objects.create(
                representative=rep,
                image=request.FILES.get('image'),
                # Super Admin publishes this immediately, so "date posted" is
                # simply today — never a manually-entered date.
                date_posted=timezone.localdate(),
                status='published',
                **data,
            )
            for problem in save_content_photos(request, ann):   # "More photos"
                messages.warning(request, problem)
            messages.success(request, f'"{title}" was published.')
            if office_choice == 'super_admin':
                # An LGU-wide announcement: tell the office representatives
                # who keep "System announcements" switched on.
                notify_all_reps(
                    'announcements',
                    title=f'New LGU announcement: {title}'[:255],
                    description=request.POST.get('subtitle', '').strip() or 'The Super Admin posted a new announcement on the public website.',
                    level='info',
                    link_url=reverse('announcement'),
                )

    return redirect('admin_dashboard:ad_announcement')

@super_admin_required
def admin_edit_announcement(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        office_choice = request.POST.get('office')

        if office_choice == 'super_admin':
            rep = get_or_create_lgu_rep(request.user)
        else:
            office = Office.objects.filter(pk=office_choice).select_related('representative').first() if office_choice else None
            rep = getattr(office, 'representative', None) if office else None

        errors, data = clean_announcement(request.POST, is_new=False, current_expiration=announcement.expiration_date)
        if errors:
            for err in errors:
                messages.error(request, err)
        elif not rep:
            messages.error(request, "Please select an office with an assigned representative.")
        else:
            announcement.representative = rep
            for field, value in data.items():
                setattr(announcement, field, value)
            if request.FILES.get('image'):
                announcement.image = request.FILES.get('image')
            # date_posted is intentionally left untouched here — it's only
            # ever set automatically, when the announcement is approved/
            # published (see admin_approval_details / _stamp_published_date).
            announcement.save()
            for problem in save_content_photos(request, announcement):   # "More photos": add / remove
                messages.warning(request, problem)
            messages.success(request, f'"{title}" was updated.')

    return redirect('admin_dashboard:ad_announcement')

@super_admin_required
def admin_delete_announcement(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)

    if request.method == "POST":
        title = announcement.title
        announcement.status = 'archive'
        announcement.save()
        messages.success(request, f'"{title}" was archived.')

    return redirect('admin_dashboard:ad_announcement')

@super_admin_required
def admin_announcement_toggle_pin(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)

    if request.method == "POST":
        announcement.is_pinned = not announcement.is_pinned
        announcement.save()
        messages.success(
            request,
            f'"{announcement.title}" was {"pinned as the notice" if announcement.is_pinned else "unpinned"}.'
        )

    return redirect('admin_dashboard:ad_announcement')

NEWS_STATUS_BADGE = {
    "pending": "badge-amber",
    "published": "badge-green",
    "returned": "badge-red",
    "reject": "badge-red",
    "archive": "badge-gray",
}

@super_admin_required
def admin_news_update(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    qs = (NewsUpdate.objects
          .select_related('representative__office')
          .filter(status='published')
          .order_by('-date_published', '-created_at'))

    categories = list(qs.exclude(category='').values_list('category', flat=True).distinct().order_by('category'))

    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(content__icontains=q))

    total_count = NewsUpdate.objects.filter(status='published').count()
    total_views = NewsUpdate.objects.filter(status='published').aggregate(total=Sum('views'))['total'] or 0

    news_items = list(qs)
    for n in news_items:
        n.badge_class = NEWS_STATUS_BADGE.get(n.status, 'badge-gray')

    return render(request, "admin_dashboard/super-admin-news-updates.html", {
        "news_items": news_items,
        "total_count": total_count,
        "total_views": total_views,
        "categories": categories,
        "current_q": q,
        "current_category": category,
        "office_reps": OfficeRepresentative.objects.select_related('office').order_by('office__name'),
        "lgu_office_name": Office.objects.filter(slug=LGU_SUPER_ADMIN_SLUG).values_list('name', flat=True).first() or "LGU Super Admin",
    })

@super_admin_required
def admin_news_save(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard:ad_news_update')

    title = request.POST.get('title', '').strip()
    rep_choice = request.POST.get('representative')

    if rep_choice == 'super_admin':
        representative = get_or_create_lgu_rep(request.user)
    else:
        representative = OfficeRepresentative.objects.filter(pk=rep_choice).first() if rep_choice else None

    if not title or not representative:
        messages.error(request, "Headline and posting office are required.")
        return redirect('admin_dashboard:ad_news_update')

    if pk:
        n = get_object_or_404(NewsUpdate, pk=pk)
    else:
        n = NewsUpdate()
        # Super Admin publishes this immediately, so "date published" is
        # simply today, set once at creation — never a manually-entered
        # date, and never touched again on later edits.
        n.date_published = timezone.localdate()

    n.representative = representative
    n.title = title
    n.category = request.POST.get('category', '').strip()
    n.summary = request.POST.get('summary', '').strip()
    n.content = request.POST.get('content', '').strip()
    n.author = request.POST.get('author', '').strip()
    n.source = request.POST.get('source', '').strip()
    n.tags = request.POST.get('tags', '').strip()
    n.status = 'published'

    image = request.FILES.get('image')
    if image:
        n.image = image

    n.save()
    for problem in save_content_photos(request, n):   # "More photos": add / remove
        messages.warning(request, problem)
    messages.success(request, f'"{title}" was published.')
    return redirect('admin_dashboard:ad_news_update')

@super_admin_required
def admin_news_delete(request, pk):
    n = get_object_or_404(NewsUpdate, pk=pk)
    if request.method == "POST":
        title = n.title
        n.status = 'archive'
        n.save()
        messages.success(request, f'"{title}" was archived.')
    return redirect('admin_dashboard:ad_news_update')

EVENT_STATUS_BADGE = {
    "pending": "badge-amber",
    "published": "badge-green",
    "returned": "badge-red",
    "reject": "badge-red",
    "archive": "badge-gray",
}

@super_admin_required
def admin_events(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    when = request.GET.get('when', 'all')

    today = timezone.localdate()

    qs = Event.objects.filter(status='published').select_related('representative__office').order_by('-event_date', '-created_at')

    categories = list(qs.exclude(category='').values_list('category', flat=True).distinct().order_by('category'))

    if when == 'upcoming':
        qs = qs.filter(event_date__gte=today)
    elif when == 'past':
        qs = qs.filter(event_date__lt=today)

    if category:
        qs = qs.filter(category=category)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))

    total_count = Event.objects.filter(status='published').count()
    past_count = Event.objects.filter(status='published', event_date__lt=today).count()

    events = list(qs)
    for e in events:
        e.badge_class = EVENT_STATUS_BADGE.get(e.status, 'badge-gray')

    office_reps = OfficeRepresentative.objects.select_related('office', 'user').order_by('office__name')

    return render(request, "admin_dashboard/super-admin-events.html", {
        "events": events,
        "total_count": total_count,
        "past_count": past_count,
        "office_reps": office_reps,
        "categories": categories,
        "current_q": q,
        "current_category": category,
        "current_when": when,
        "lgu_office_name": Office.objects.filter(slug=LGU_SUPER_ADMIN_SLUG).values_list('name', flat=True).first() or "LGU Super Admin",
    })

@super_admin_required
def admin_event_save(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard:ad_events')

    title = request.POST.get('title', '').strip()
    rep_choice = request.POST.get('representative')

    if rep_choice == 'super_admin':
        representative = get_or_create_lgu_rep(request.user)
    else:
        representative = OfficeRepresentative.objects.filter(pk=rep_choice).first() if rep_choice else None

    if not title or not representative:
        messages.error(request, "Title and organizing office are required.")
        return redirect('admin_dashboard:ad_events')

    if pk:
        e = get_object_or_404(Event, pk=pk)
    else:
        e = Event()

    e.representative = representative
    e.title = title
    e.category = request.POST.get('category', '').strip()
    e.description = request.POST.get('description', '').strip()
    e.event_date = request.POST.get('event_date') or None
    e.start_time = request.POST.get('start_time') or None
    e.end_time = request.POST.get('end_time') or None
    e.location = request.POST.get('location', '').strip()
    e.organizer = request.POST.get('organizer', '').strip()
    e.contact_person = request.POST.get('contact_person', '').strip()
    e.contact_info = request.POST.get('contact_info', '').strip()
    e.is_featured = request.POST.get('is_featured') == 'on'
    e.status = 'published'

    poster = request.FILES.get('poster')
    if poster:
        e.poster = poster

    e.save()
    for problem in save_content_photos(request, e):   # "More photos": add / remove
        messages.warning(request, problem)
    messages.success(request, f'"{title}" was published.')
    return redirect('admin_dashboard:ad_events')

@super_admin_required
def admin_event_delete(request, pk):
    e = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        title = e.title
        e.status = 'archive'
        e.save()
        messages.success(request, f'"{title}" was archived.')
    return redirect('admin_dashboard:ad_events')

@super_admin_required
def admin_download_forms(request):
    qs = DownloadableForm.objects.select_related('office').filter(status='published')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(title__icontains=q)

    category = request.GET.get('category', '')
    if category:
        qs = qs.filter(category=category)

    sort = request.GET.get('sort', 'newest')
    if sort == 'oldest':
        qs = qs.order_by('date_uploaded')
    elif sort == 'downloads':
        qs = qs.order_by('-download_count')
    else:
        qs = qs.order_by('-date_uploaded')

    published = DownloadableForm.objects.filter(status='published')

    return render(request, "admin_dashboard/super-admin-downloadable-forms.html", {
        "forms": qs,
        "total_count": published.count(),
        "total_downloads": published.aggregate(total=Sum('download_count'))['total'] or 0,
        "office_count": published.values('office').distinct().count(),
        "current_q": q,
        "current_category": category,
        "current_sort": sort,
        "category_choices": FORM_CATEGORY_CHOICES,
        "offices_with_reps": Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).filter(representative__isnull=False).order_by('name'),
        "lgu_office_name": Office.objects.filter(slug=LGU_SUPER_ADMIN_SLUG).values_list('name', flat=True).first() or "LGU Super Admin",
    })

@super_admin_required
def admin_form_save(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard:ad_forms')

    title = request.POST.get('title', '').strip()
    office_choice = request.POST.get('office')
    uploaded_file = request.FILES.get('file')

    if office_choice == 'super_admin':
        office = get_or_create_lgu_rep(request.user).office
    else:
        office = Office.objects.filter(pk=office_choice).first() if office_choice else None

    if pk:
        f = get_object_or_404(DownloadableForm, pk=pk)
    else:
        f = None

    if not title or not office:
        messages.error(request, "Form name and posting office are required.")
    elif not f and not uploaded_file:
        messages.error(request, "Please attach a PDF file.")
    elif uploaded_file and not uploaded_file.name.lower().endswith('.pdf'):
        messages.error(request, "Only PDF files are allowed.")
    else:
        if f is None:
            f = DownloadableForm(uploaded_by=office.name, status='published')
        f.office = office
        f.title = title
        f.description = request.POST.get('description', '').strip()
        f.category = request.POST.get('category', '').strip()
        if uploaded_file:
            f.file = uploaded_file
        f.save()
        messages.success(request, f'"{title}" was published.')

    return redirect('admin_dashboard:ad_forms')

@super_admin_required
def admin_form_delete(request, pk):
    f = get_object_or_404(DownloadableForm, pk=pk)
    if request.method == "POST":
        title = f.title
        f.status = 'archive'
        f.save()
        messages.success(request, f'"{title}" was archived.')
    return redirect('admin_dashboard:ad_forms')

@super_admin_required
def admin_download_form_file(request, pk):
    form = get_object_or_404(DownloadableForm, pk=pk)

    DownloadableForm.objects.filter(pk=pk).update(download_count=F('download_count') + 1)

    try:
        filename = form.file.name.rsplit('/', 1)[-1]
        return FileResponse(form.file.open('rb'), as_attachment=True, filename=filename)
    except FileNotFoundError:
        raise Http404("File not found.")


@super_admin_required
def admin_view_form_file(request, pk):
    """PDF for the Super Admin's View File link and field builder preview."""
    form = get_object_or_404(DownloadableForm, pk=pk)
    return pdf_response(request, form.file, filename="form.pdf")


@super_admin_required
def admin_preview_form(request, pk):
    """Page that shows the PDF with pdf.js (works even when Chrome is set to
    download PDFs or a download-manager extension grabs them)."""
    form = get_object_or_404(DownloadableForm, pk=pk)
    return render(request, "pdf_viewer.html", {
        "title": form.title,
        "pdf_url": reverse("admin_dashboard:admin_view_form_file", args=[form.pk]),
        "download_url": reverse("admin_dashboard:admin_download_form_file", args=[form.pk]),
    })


@super_admin_required
def admin_form_fields_builder(request, pk):
    form = get_object_or_404(DownloadableForm, pk=pk)
    return render(request, "admin_dashboard/super-admin-form-fields-builder.html", {
        "form_obj": form,
        "fields_json": fields_json(form),
    })


@super_admin_required
def admin_save_form_fields(request, pk):
    form = get_object_or_404(DownloadableForm, pk=pk)
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)
    try:
        incoming = json.loads(request.body).get("fields", [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "error": "Invalid data."}, status=400)

    count = save_fields(form, incoming)
    messages.success(request, f'"{form.title}" is now fillable — fields were saved.' if count else f'All fields were removed from "{form.title}".')
    return JsonResponse({"success": True, "fields": json.loads(fields_json(form))})


@super_admin_required
def admin_gallery(request):
    albums = (Album.objects
              .annotate(photo_count=Count('photos', filter=Q(photos__status='published')))
              .filter(photo_count__gt=0)
              .select_related('representative__office'))

    q = request.GET.get('q', '').strip()
    if q:
        albums = albums.filter(name__icontains=q)

    sort = request.GET.get('sort', 'newest')
    if sort == 'oldest':
        albums = albums.order_by('created_at')
    elif sort == 'photos':
        albums = albums.order_by('-photo_count')
    elif sort == 'name':
        albums = albums.order_by('name')
    else:
        albums = albums.order_by('-created_at')

    albums = list(albums)
    for a in albums:
        a.published_cover = a.photos.filter(status='published').order_by('-created_at').first()

    published_photos = Photo.objects.filter(status='published')
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    albums_by_office = {}
    for rep in OfficeRepresentative.objects.select_related('office').prefetch_related('albums'):
        albums_by_office[str(rep.office_id)] = [{"id": a.id, "name": a.name} for a in rep.albums.all()]

    lgu_rep = OfficeRepresentative.objects.filter(office__slug='lgu-super-admin').prefetch_related('albums').first()
    albums_by_office['super_admin'] = [{"id": a.id, "name": a.name} for a in lgu_rep.albums.all()] if lgu_rep else []

    return render(request, "admin_dashboard/super-admin-gallery.html", {
        "albums": albums,
        "total_albums": len(albums),
        "total_photos": published_photos.count(),
        "archived_photos": Photo.objects.filter(status='archive').count(),
        "recent_photos": published_photos.filter(created_at__gte=month_start).count(),
        "current_q": q,
        "current_sort": sort,
        "albums_by_office": albums_by_office,
        "offices_with_reps": Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).filter(representative__isnull=False).order_by('name'),
        "photo_category_choices": Photo.CATEGORY_CHOICES,
        "lgu_office_name": Office.objects.filter(slug=LGU_SUPER_ADMIN_SLUG).values_list('name', flat=True).first() or "LGU Super Admin",
    })

@super_admin_required
def admin_photo_save(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard:ad_gallery')

    title = request.POST.get('title', '').strip()
    image = request.FILES.get('image')
    category = request.POST.get('category', '').strip()

    if pk:
        photo = get_object_or_404(Photo, pk=pk)
        if not title:
            messages.error(request, "Title is required.")
        else:
            photo.title = title
            photo.category = category
            if image:
                photo.image = image
            photo.save()
            messages.success(request, f'"{title}" was saved.')
        if photo.album_id:
            return redirect('admin_dashboard:ad_album_detail', pk=photo.album_id)
        return redirect('admin_dashboard:ad_gallery')

    office_choice = request.POST.get('office')
    album_choice = request.POST.get('album')
    new_album_name = request.POST.get('new_album_name', '').strip()

    if office_choice == 'super_admin':
        representative = get_or_create_lgu_rep(request.user)
    else:
        office = Office.objects.filter(pk=office_choice).select_related('representative').first() if office_choice else None
        representative = getattr(office, 'representative', None) if office else None

    if not title or not representative:
        messages.error(request, "Title and posting office are required.")
    elif not image:
        messages.error(request, "Please choose a photo to upload.")
    else:
        if album_choice == '__new__' and new_album_name:
            album, _ = Album.objects.get_or_create(representative=representative, name=new_album_name)
        elif album_choice and album_choice != '__new__':
            album = Album.objects.filter(pk=album_choice, representative=representative).first()
        else:
            album = None

        Photo.objects.create(
            representative=representative,
            album=album,
            title=title,
            image=image,
            category=category,
            status='published',
        )
        messages.success(request, f'"{title}" was published.')

    return redirect('admin_dashboard:ad_gallery')

@super_admin_required
def admin_album_detail(request, pk):
    album = get_object_or_404(Album.objects.select_related('representative__office'), pk=pk)
    photos = album.photos.filter(status__in=['published', 'archive']).order_by('-created_at')

    tab = request.GET.get('tab', 'active')
    if tab == 'active':
        photos = photos.filter(status='published')
    elif tab == 'archived':
        photos = photos.filter(status='archive')

    return render(request, "admin_dashboard/super-admin-album-detail.html", {
        "album": album,
        "photos": photos,
        "current_tab": tab,
        "all_count": album.photos.filter(status__in=['published', 'archive']).count(),
        "active_count": album.photos.filter(status='published').count(),
        "archived_count": album.photos.filter(status='archive').count(),
        "photo_category_choices": Photo.CATEGORY_CHOICES,
    })


MAX_FEATURED_ALBUMS = 4  # matches the 4 card slots in the public Gallery's "Featured Albums" row


@super_admin_required
def admin_album_toggle_featured(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if request.method == "POST":
        if not album.is_featured and Album.objects.filter(is_featured=True).count() >= MAX_FEATURED_ALBUMS:
            messages.error(
                request,
                f'Only {MAX_FEATURED_ALBUMS} albums can be featured at once. '
                f'Unfeature one first before adding "{album.name}".'
            )
        else:
            album.is_featured = not album.is_featured
            album.save(update_fields=["is_featured"])
            messages.success(
                request,
                f'"{album.name}" was {"added to" if album.is_featured else "removed from"} Featured Albums.'
            )
    return redirect(request.POST.get('next') or 'admin_dashboard:ad_gallery')


@super_admin_required
def admin_photo_archive_toggle(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    if request.method == "POST":
        photo.status = 'archive' if photo.status == 'published' else 'published'
        photo.save()
        messages.success(request, f'"{photo.title}" was {"archived" if photo.status == "archive" else "restored"}.')
    return redirect('admin_dashboard:ad_album_detail', pk=photo.album_id)


@super_admin_required
def admin_photo_delete(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    if request.method == "POST":
        title = photo.title
        photo.status = 'archive'
        photo.save()
        messages.success(request, f'"{title}" was archived.')
        return redirect('admin_dashboard:ad_archive')
    return redirect('admin_dashboard:ad_album_detail', pk=photo.album_id)

@super_admin_required
def admin_offices(request):
    all_offices = list(Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).select_related('representative__user'))

    rows = []
    active_count = 0
    pending_count = 0
    inactive_count = 0

    for office in all_offices:
        rep = getattr(office, 'representative', None)

        if rep is None:
            status = 'pending'
            pending_count += 1
        elif not rep.user.is_active:
            status = 'inactive'
            inactive_count += 1
        else:
            status = 'active'
            active_count += 1

        published_count = 0
        last_update = None
        if rep:
            published_count = (
                Announcement.objects.filter(representative=rep, status='published').count()
                + NewsUpdate.objects.filter(representative=rep, status='published').count()
                + Event.objects.filter(representative=rep, status='published').count()
                + Photo.objects.filter(representative=rep, status='published').count()
            )
            last_update = rep.user.last_login

        rows.append({
            "office": office,
            "rep": rep,
            "status": status,
            "published_count": published_count,
            "last_update": last_update,
        })

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')

    if q:
        rows = [r for r in rows if q.lower() in r["office"].name.lower()]
    if status_filter:
        rows = [r for r in rows if r["status"] == status_filter]

    rows.sort(key=lambda r: (r["office"].display_order, r["office"].name))

    return render(request, "admin_dashboard/super-admin-office-overview.html", {
        "rows": rows,
        "total_offices": len(all_offices),
        "active_count": active_count,
        "pending_count": pending_count,
        "inactive_count": inactive_count,
        "current_q": q,
        "current_status": status_filter,
        "reorder_rows": sorted(
            all_offices, key=lambda o: (o.display_order, o.name)
        ),
    })


@super_admin_required
def admin_offices_reorder(request):
    """Saves the drag-and-drop order of offices (position on the public site).
    Expects JSON: {"order": [office_id, office_id, ...]} in the new order."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        ids = [int(i) for i in payload.get("order", [])]
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid data."}, status=400)

    offices = {
        o.pk: o
        for o in Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).filter(pk__in=ids)
    }
    changed = []
    position = 0
    for pk in ids:
        office = offices.get(pk)
        if office is None:
            continue
        position += 1
        if office.display_order != position:
            office.display_order = position
            changed.append(office)
    if changed:
        Office.objects.bulk_update(changed, ["display_order"])
    return JsonResponse({"ok": True, "count": position})


@super_admin_required
def admin_office_edit(request, pk):
    office = get_object_or_404(Office, pk=pk)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()

        if not name:
            messages.error(request, "Office name is required.")
        elif Office.objects.filter(name__iexact=name).exclude(pk=office.pk).exists():
            messages.error(request, f'An office named "{name}" already exists.')
        else:
            office.name = name
            office.about = request.POST.get('about', '').strip()
            office.description = request.POST.get('description', '').strip()
            office.head_name = request.POST.get('head_name', '').strip()
            office.position_title = request.POST.get('position_title', '').strip()
            office.office_hours = request.POST.get('office_hours', '').strip()
            office.location = request.POST.get('location', '').strip()
            office.email = request.POST.get('email', '').strip()
            office.telephone = request.POST.get('telephone', '').strip()
            if request.FILES.get('logo'):
                office.logo = request.FILES.get('logo')
            office.save()
            messages.success(request, f'"{name}" was updated.')

    return redirect('admin_dashboard:ad_offices')

@super_admin_required
def admin_office_toggle_visibility(request, pk):
    office = get_object_or_404(Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG), pk=pk)
    if request.method == "POST":
        office.is_visible = not office.is_visible
        office.save(update_fields=["is_visible"])
        if office.is_visible:
            messages.success(request, f'"{office.name}" is now shown on the public Offices page.')
        else:
            messages.success(request, f'"{office.name}" is now hidden from the public Offices page.')
    return redirect('admin_dashboard:ad_offices')

@super_admin_required
def admin_office_rep(request):
    reps = list(OfficeRepresentative.objects.exclude(office__slug=LGU_SUPER_ADMIN_SLUG).select_related('user', 'office'))

    week_ago = timezone.now() - timedelta(days=7)

    rows = []
    active_count = 0
    pending_count = 0
    inactive_count = 0

    for rep in reps:
        if not rep.user.is_active:
            status = 'inactive'
            inactive_count += 1
        elif rep.user.last_login is None:
            status = 'pending'
            pending_count += 1
        elif rep.user.last_login >= week_ago:
            status = 'active'
            active_count += 1
        else:
            status = 'inactive'
            inactive_count += 1

        rows.append({"rep": rep, "status": status})

    total_offices = Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).count()
    assigned_office_ids = {r["rep"].office_id for r in rows}
    offices_without_rep = total_offices - len(assigned_office_ids)

    q = request.GET.get('q', '').strip()
    office_id = request.GET.get('office', '')
    status_filter = request.GET.get('status', '')

    if q:
        rows = [r for r in rows if q.lower() in (r["rep"].user.get_full_name() or r["rep"].user.username).lower()
                or q.lower() in r["rep"].user.email.lower()]
    if office_id:
        rows = [r for r in rows if str(r["rep"].office_id) == office_id]
    if status_filter:
        rows = [r for r in rows if r["status"] == status_filter]

    rows.sort(key=lambda r: r["rep"].office.name)

    return render(request, "admin_dashboard/super-admin-office-reps.html", {
        "rows": rows,
        "offices": Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).order_by('name'),
        "total_reps": len(reps),
        "total_offices": total_offices,
        "active_count": active_count,
        "pending_count": pending_count,
        "inactive_count": inactive_count,
        "offices_without_rep": offices_without_rep,
        "current_q": q,
        "current_office": office_id,
        "current_status": status_filter,
        "available_offices": Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).filter(representative__isnull=True).order_by('name'),
        "available_users": User.objects.filter(office_rep__isnull=True, is_superuser=False).order_by('username'),
    })

@super_admin_required
def admin_assign_representative(request):
    if request.method == "POST":
        user_id = request.POST.get('user')
        office_id = request.POST.get('office')
        position = request.POST.get('position', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        photo = request.FILES.get('photo')

        user = User.objects.filter(pk=user_id, office_rep__isnull=True).first() if user_id else None
        office = Office.objects.filter(pk=office_id, representative__isnull=True).first() if office_id else None

        if not user or not office:
            messages.error(request, "Please choose a user and an office that don't already have a representative assigned.")
        else:
            rep = OfficeRepresentative(user=user, office=office, position=position, mobile_number=mobile_number)
            if photo:
                rep.photo = photo
            rep.save()
            label = user.get_full_name() or user.username
            messages.success(request, f'{label} was assigned as the representative for {office.name}.')

    return redirect('admin_dashboard:ad_office_rep')

@super_admin_required
def admin_rep_replace_user(request, pk):
    rep = get_object_or_404(OfficeRepresentative, pk=pk)
    if request.method == "POST":
        new_user_id = request.POST.get('new_user')
        new_user = User.objects.filter(pk=new_user_id, office_rep__isnull=True).first() if new_user_id else None

        if not new_user:
            messages.error(request, "Please choose a user who isn't already assigned to another office.")
        else:
            old_label = rep.user.get_full_name() or rep.user.username
            rep.user = new_user
            rep.save()
            new_label = new_user.get_full_name() or new_user.username
            messages.success(request, f'{rep.office.name} is now represented by {new_label} (replacing {old_label}). All content stays linked to this office.')

    return redirect('admin_dashboard:ad_office_rep')

@super_admin_required
def admin_rep_toggle_active(request, pk):
    rep = get_object_or_404(OfficeRepresentative, pk=pk)
    if request.method == "POST":
        rep.user.is_active = not rep.user.is_active
        rep.user.save()
        label = rep.user.get_full_name() or rep.user.username
        messages.success(request, f'{label} was {"activated" if rep.user.is_active else "deactivated"}.')
        Notification.objects.create(
            representative=rep,
            title="Account activated" if rep.user.is_active else "Account deactivated",
            description=(
                "Your office representative account has been reactivated. You now have access to the dashboard again."
                if rep.user.is_active else
                "Your office representative account has been deactivated by a Super Admin."
            ),
            level='success' if rep.user.is_active else 'danger',
        )
    return redirect('admin_dashboard:ad_office_rep')

SERVICE_STATUS_BADGE = {
    "pending": "badge-amber",
    "published": "badge-green",
    "returned": "badge-red",
    "reject": "badge-red",
    "archive": "badge-gray",
}

@super_admin_required
def admin_services(request):
    q = request.GET.get('q', '').strip()

    services = Service.objects.filter(status='published').select_related('office').order_by('name')

    if q:
        services = services.filter(Q(name__icontains=q) | Q(office__name__icontains=q))

    total_count = Service.objects.filter(status='published').count()
    archived_count = Service.objects.filter(status='archive').count()

    services = list(services)
    for s in services:
        s.badge_class = SERVICE_STATUS_BADGE.get(s.status, 'badge-gray')

    paginator = Paginator(services, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "admin_dashboard/super-admin-services.html", {
        "page_obj": page_obj,
        "total_count": total_count,
        "archived_count": archived_count,
        "current_q": q,
        "editing_enabled": ServiceEditSettings.get_solo().editing_enabled,
    })

def _group_requirements_for_charter(requirements):
    """Mirrors buildPreviewRequirementsTable() in office-rep-service-details.html:
    requirements with no type of transaction come first as a plain list, then
    the rest are grouped under their type of transaction (alphabetically),
    so the Super Admin sees the exact same Citizen's Charter grouping the
    office rep sees in their own Preview."""
    general = [r for r in requirements if not r.transaction_type]
    grouped = {}
    for r in requirements:
        if r.transaction_type:
            grouped.setdefault(r.transaction_type, []).append(r)
    grouped_list = [(key, grouped[key]) for key in sorted(grouped.keys())]
    return general, grouped_list


@super_admin_required
def admin_service_detail(request, pk):
    service = get_object_or_404(Service.objects.select_related('office'), pk=pk)
    service.badge_class = SERVICE_STATUS_BADGE.get(service.status, 'badge-gray')

    steps = list(service.steps.all())
    requirements = list(service.requirements.all())
    general_requirements, grouped_requirements = _group_requirements_for_charter(requirements)

    return render(request, "admin_dashboard/super-admin-service-detail.html", {
        "service": service,
        "steps": steps,
        "total_processing_time": _compute_total_processing_time(steps),
        "general_requirements": general_requirements,
        "grouped_requirements": grouped_requirements,
        "has_requirements": bool(requirements),
        "forms": service.forms.all().order_by('-date_uploaded'),
    })

@super_admin_required
def admin_service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        name = service.name
        service.delete()
        messages.success(request, f'"{name}" was deleted.')
    return redirect('admin_dashboard:ad_services')

@super_admin_required
def admin_toggle_service_editing(request):
    """Single site-wide switch (not per-service): turns the office
    representatives' ability to edit a service's basic info on/off for
    every office at once."""
    settings_obj = ServiceEditSettings.get_solo()
    if request.method == "POST":
        settings_obj.editing_enabled = not settings_obj.editing_enabled
        settings_obj.save(update_fields=["editing_enabled"])
        if settings_obj.editing_enabled:
            messages.success(request, "Service editing was turned back on for all offices.")
        else:
            messages.success(request, "Service editing was turned off for all offices. Representatives can no longer edit a service's basic info until you turn it back on.")
    return redirect('admin_dashboard:ad_services')

@super_admin_required
def admin_users(request):
    users = (User.objects
            .filter(office_rep__isnull=True, super_admin__isnull=True)
            .exclude(is_staff=True)
            .exclude(is_superuser=True)
            .select_related('profile'))

    total_users = users.count()
    active_count = users.filter(is_active=True).count()
    inactive_count = users.filter(is_active=False).count()

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = users.filter(date_joined__gte=month_start).count()

    q = request.GET.get('q', '').strip()
    if q:
        users = users.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        )

    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    users = users.order_by('-date_joined')

    return render(request, "admin_dashboard/super-admin-users.html", {
        "users": users,
        "total_users": total_users,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "new_this_month": new_this_month,
        "current_q": q,
        "current_status": status_filter,
    })


@super_admin_required
def admin_user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk, office_rep__isnull=True, super_admin__isnull=True)
    if request.method == "POST":
        user.is_active = not user.is_active
        user.save()
        label = user.get_full_name() or user.username
        messages.success(request, f'{label} was {"activated" if user.is_active else "deactivated"}.')
    return redirect('admin_dashboard:ad_users')

@super_admin_required
def admin_roles(request):
    return render(request, "admin_dashboard/super-admin-roles.html")

@super_admin_required
def admin_homepage(request):
    quick_links = list(QuickLink.objects.all())
    today = timezone.localdate()

    # ---- Pages/content a Quick Link can point to, for the "Link
    # Destination" picker -- static site pages, plus every office and every
    # published service, so the Super Admin picks a real destination instead
    # of hand-typing a URL that can drift out of date or get mistyped. ----
    static_pages_for_links = [
        {"label": "Home", "url": "/"},
        {"label": "Announcements & News", "url": "/announcement/"},
        {"label": "-- Announcements tab", "url": "/announcement/#announcements"},
        {"label": "-- News tab", "url": "/announcement/#news"},
        {"label": "-- Events tab", "url": "/announcement/#events"},
        {"label": "Gallery", "url": "/gallery/"},
        {"label": "Offices Directory", "url": "/offices/"},
        {"label": "About Us", "url": "/about/"},
        {"label": "-- About: History", "url": "/about/#history"},
        {"label": "-- About: Municipal Officials", "url": "/about/#officials"},
        {"label": "-- About: Barangays", "url": "/about/#barangays"},
        {"label": "Contact Us", "url": "/contact/"},
    ]

    offices_for_links = list(Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).order_by('name'))
    for o in offices_for_links:
        o.quicklink_url = f"/offices/{o.slug}/"

    services_for_links = list(
        Service.objects.filter(status="published").select_related('office').order_by('office__name', 'name')
    )
    for s in services_for_links:
        s.quicklink_url = f"/offices/{s.office.slug}/#svc-{s.id}" if s.office else ""

    known_urls = {p["url"] for p in static_pages_for_links}
    known_urls |= {o.quicklink_url for o in offices_for_links}
    known_urls |= {s.quicklink_url for s in services_for_links if s.quicklink_url}

    for l in quick_links:
        l.is_custom_url = l.url not in known_urls

    return render(request, "admin_dashboard/super-admin-homepage.html", {
        "quick_links": quick_links,
        "static_pages_for_links": static_pages_for_links,
        "offices_for_links": offices_for_links,
        "services_for_links": services_for_links,
        "quick_links_active_count": sum(1 for l in quick_links if l.is_active),
        "quick_links_total_count": len(quick_links),
        "emergency_contacts_count": EmergencyContact.objects.count(),
        "home_announcements_count": Announcement.objects.filter(status="published").count(),
        "upcoming_events_count": Event.objects.filter(status="published", event_date__gte=today).count(),
        "published_news_count": NewsUpdate.objects.filter(status="published").count(),
        "gallery_photos_count": Photo.objects.filter(status="published").count(),
    })
 
 
@super_admin_required
def admin_quicklink_save(request, pk):
    link = get_object_or_404(QuickLink, pk=pk) if pk else QuickLink()
 
    if request.method == "POST":
        label = request.POST.get('label', '').strip()
        url = request.POST.get('url', '').strip()
        if url == '__custom__':
            # The "Link Destination" <select> submits this sentinel when the
            # Super Admin picked "Custom URL..." instead of one of the real
            # site pages/offices/services it lists -- the actual address
            # they typed is in the paired text field shown only in that case.
            url = request.POST.get('url_custom', '').strip()

        if not label or not url:
            messages.error(request, "Please fill in both the label and the link destination.")
        else:
            is_create = link.pk is None
            link.label = label
            link.icon = request.POST.get('icon', 'fa-file-lines')
            link.url = url
            link.open_in_new_tab = request.POST.get('open_in_new_tab') == 'on'
            link.is_active = request.POST.get('is_active') == 'on'
            if is_create:
                link.order = QuickLink.objects.count()
            link.save()
            messages.success(request, f'"{label}" was saved.')
 
    return redirect('admin_dashboard:ad_homepage')
 
 
@super_admin_required
def admin_quicklink_delete(request, pk):
    link = get_object_or_404(QuickLink, pk=pk)
    if request.method == "POST":
        label = link.label
        link.delete()
        messages.success(request, f'"{label}" was removed.')
    return redirect('admin_dashboard:ad_homepage')
 
 
@super_admin_required
def admin_quicklink_move(request, pk, direction):
    """direction: 'up' or 'down' — swaps this link's position with its
    neighbor in the Quick Links list."""
    if request.method == "POST":
        links = list(QuickLink.objects.order_by('order', 'id'))
        index = next((i for i, l in enumerate(links) if l.pk == pk), None)
        if index is not None:
            target = index - 1 if direction == 'up' else index + 1
            if 0 <= target < len(links):
                links[index].order, links[target].order = links[target].order, links[index].order
                links[index].save(update_fields=['order'])
                links[target].save(update_fields=['order'])
    return redirect('admin_dashboard:ad_homepage')


@super_admin_required
def admin_about_page(request):
    """Super Admin's "About Us Page" screen — one page with a tab per
    section of the public About Us page (About Us / History / Municipal
    Officials / Barangays / At a Glance), mirroring the tabbed layout
    already used for Website Settings. AboutPageContent.get_solo() seeds
    itself with the page's original hardcoded copy on first use, so nothing
    on the live site changes until an admin actually edits something here."""
    content = AboutPageContent.get_solo()

    if request.method == "POST":
        section = request.POST.get('section')

        if section == 'history':
            content.history_intro = request.POST.get('history_intro', '').strip()
            if request.FILES.get('history_image'):
                content.history_image = request.FILES.get('history_image')
            content.save()
            messages.success(request, "History content was updated.")
        elif section == 'barangays':
            content.barangays_intro = request.POST.get('barangays_intro', '').strip()
            content.save()
            messages.success(request, "Barangays section was updated.")
        elif section == 'glance':
            content.glance_population_value = request.POST.get('glance_population_value', '').strip()
            content.glance_population_label = request.POST.get('glance_population_label', '').strip()
            content.glance_land_area_value = request.POST.get('glance_land_area_value', '').strip()
            content.glance_land_area_label = request.POST.get('glance_land_area_label', '').strip()
            content.glance_households_value = request.POST.get('glance_households_value', '').strip()
            content.glance_households_label = request.POST.get('glance_households_label', '').strip()
            content.glance_established_value = request.POST.get('glance_established_value', '').strip()
            content.glance_established_label = request.POST.get('glance_established_label', '').strip()
            content.save()
            messages.success(request, '"Municipality at a Glance" was updated.')
        else:
            content.hero_intro = request.POST.get('hero_intro', '').strip()
            content.vision_text = request.POST.get('vision_text', '').strip()
            content.mission_text = request.POST.get('mission_text', '').strip()
            content.core_values = request.POST.get('core_values', '').strip()
            content.save()
            messages.success(request, "About Us content was updated.")

        return redirect(reverse('admin_dashboard:ad_about_page') + '#' + (section or 'about'))

    return render(request, "admin_dashboard/super-admin-about-page.html", {
        "content": content,
        "milestones": HistoryMilestone.objects.all(),
        "officials": AboutOfficial.objects.all(),
        "barangays_poblacion": Barangay.objects.filter(group='poblacion'),
        "barangays_rural": Barangay.objects.filter(group='rural'),
    })


@super_admin_required
def admin_about_milestone_save(request, pk):
    m = get_object_or_404(HistoryMilestone, pk=pk) if pk else HistoryMilestone()
    if request.method == "POST":
        year_label = request.POST.get('year_label', '').strip()
        description = request.POST.get('description', '').strip()
        if not year_label or not description:
            messages.error(request, "Please fill in both the year/label and the description.")
        else:
            is_create = m.pk is None
            m.year_label = year_label
            m.description = description
            m.is_present = request.POST.get('is_present') == 'on'
            if is_create:
                m.order = HistoryMilestone.objects.count()
            m.save()
            messages.success(request, f'"{year_label}" was saved.')
    return redirect(reverse('admin_dashboard:ad_about_page') + '#history')


@super_admin_required
def admin_about_milestone_delete(request, pk):
    m = get_object_or_404(HistoryMilestone, pk=pk)
    if request.method == "POST":
        label = m.year_label
        m.delete()
        messages.success(request, f'"{label}" was removed.')
    return redirect(reverse('admin_dashboard:ad_about_page') + '#history')


@super_admin_required
def admin_about_official_save(request, pk):
    o = get_object_or_404(AboutOfficial, pk=pk) if pk else AboutOfficial()
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        position = request.POST.get('position', '').strip()
        if not name or not position:
            messages.error(request, "Please fill in both the name and the position.")
        else:
            is_create = o.pk is None
            o.name = name
            o.position = position
            if request.FILES.get('photo'):
                o.photo = request.FILES.get('photo')
            if is_create:
                o.order = AboutOfficial.objects.count()
            o.save()
            messages.success(request, f'"{name}" was saved.')
    return redirect(reverse('admin_dashboard:ad_about_page') + '#officials')


@super_admin_required
def admin_about_official_delete(request, pk):
    o = get_object_or_404(AboutOfficial, pk=pk)
    if request.method == "POST":
        name = o.name
        o.delete()
        messages.success(request, f'"{name}" was removed.')
    return redirect(reverse('admin_dashboard:ad_about_page') + '#officials')


@super_admin_required
def admin_about_barangay_save(request, pk):
    b = get_object_or_404(Barangay, pk=pk) if pk else Barangay()
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Please enter a barangay name.")
        else:
            is_create = b.pk is None
            b.name = name
            b.group = request.POST.get('group', 'poblacion')
            if is_create:
                b.order = Barangay.objects.filter(group=b.group).count()
            b.save()
            messages.success(request, f'"{name}" was saved.')
    return redirect(reverse('admin_dashboard:ad_about_page') + '#barangays')


@super_admin_required
def admin_about_barangay_delete(request, pk):
    b = get_object_or_404(Barangay, pk=pk)
    if request.method == "POST":
        name = b.name
        b.delete()
        messages.success(request, f'"{name}" was removed.')
    return redirect(reverse('admin_dashboard:ad_about_page') + '#barangays')


# The page's original hardcoded content — shared by the "Reset to Default"
# button below so it restores exactly what a brand-new install seeds via
# admin_dashboard/migrations/0012_seed_about_page.py.
_ABOUT_DEFAULT_MILESTONES = [
    ("1949", "Executive Order No. 266 was signed on September 26, 1949, creating Tunga as an independent municipality.", False),
    ("1950s", "Establishment of the municipal government and initial development of public services.", False),
    ("1970s", "Expansion of infrastructure, schools, and health services in the municipality.", False),
    ("1990s", "Growth of agriculture and local industries, improving the livelihood of residents.", False),
    ("2000s", "Strengthening of governance and community participation in local development.", False),
    ("Present", "Tunga continues to progress towards a more resilient, inclusive, and sustainable future.", True),
]
_ABOUT_DEFAULT_OFFICIALS = [
    ("Hon. Pedro D. Dela Cruz", "Municipal Mayor"),
    ("Hon. Maria L. Santos", "Vice Mayor"),
    ("Hon. Juanito R. Reyes", "SB Member"),
    ("Hon. Liza M. Alegre", "SB Member"),
    ("Hon. Ricardo P. Torres", "SB Member"),
]
_ABOUT_DEFAULT_BARANGAYS_POBLACION = ["San Antonio", "San Pedro", "San Roque", "San Vicente", "Santo Niño"]
_ABOUT_DEFAULT_BARANGAYS_RURAL = ["Astorga", "Balire", "Banawang"]


@super_admin_required
def admin_about_reset_defaults(request):
    """Resets just the ONE tab named by POST['tab'] back to the page's
    original hardcoded content — the other 4 tabs' edits are left alone.
    "defaults" is a throwaway, unsaved AboutPageContent() instance, which
    Django populates with each field's declared default the moment it's
    instantiated — an easy way to read "what's the factory value for this
    field" without hardcoding it a second time here."""
    tab = request.POST.get('tab', 'about')
    defaults = AboutPageContent()

    if request.method == "POST":
        content = AboutPageContent.get_solo()

        if tab == 'history':
            content.history_intro = defaults.history_intro
            content.history_image = None
            content.save()
            HistoryMilestone.objects.all().delete()
            for order, (year_label, description, is_present) in enumerate(_ABOUT_DEFAULT_MILESTONES):
                HistoryMilestone.objects.create(year_label=year_label, description=description, is_present=is_present, order=order)
            messages.success(request, "The History tab was reset to its default content.")

        elif tab == 'officials':
            AboutOfficial.objects.all().delete()
            for order, (name, position) in enumerate(_ABOUT_DEFAULT_OFFICIALS):
                AboutOfficial.objects.create(name=name, position=position, order=order)
            messages.success(request, "The Municipal Officials tab was reset to its default content.")

        elif tab == 'barangays':
            content.barangays_intro = defaults.barangays_intro
            content.save()
            Barangay.objects.all().delete()
            for order, name in enumerate(_ABOUT_DEFAULT_BARANGAYS_POBLACION):
                Barangay.objects.create(name=name, group="poblacion", order=order)
            for order, name in enumerate(_ABOUT_DEFAULT_BARANGAYS_RURAL):
                Barangay.objects.create(name=name, group="rural", order=order)
            messages.success(request, "The Barangays tab was reset to its default content.")

        elif tab == 'glance':
            content.glance_population_value = defaults.glance_population_value
            content.glance_population_label = defaults.glance_population_label
            content.glance_land_area_value = defaults.glance_land_area_value
            content.glance_land_area_label = defaults.glance_land_area_label
            content.glance_households_value = defaults.glance_households_value
            content.glance_households_label = defaults.glance_households_label
            content.glance_established_value = defaults.glance_established_value
            content.glance_established_label = defaults.glance_established_label
            content.save()
            messages.success(request, '"Municipality at a Glance" was reset to its default content.')

        else:
            tab = 'about'
            content.hero_intro = defaults.hero_intro
            content.vision_text = defaults.vision_text
            content.mission_text = defaults.mission_text
            content.core_values = defaults.core_values
            content.save()
            messages.success(request, "The About Us tab was reset to its default content.")

    return redirect(reverse('admin_dashboard:ad_about_page') + '#' + tab)


@super_admin_required
def admin_interactive_map(request):
    return render(request, "admin_dashboard/super-admin-interactive-map.html")

@super_admin_required
def admin_org_chart(request, office_id=None):
    """Organizational Chart builder in the Super Admin dashboard, with the same
    features as the Office Representative's builder.
      /Admin-Org-Chart/                  -> the LGU's own chart (Municipality of
                                            Tunga), shown in "Our Officials" on
                                            the About Us page when turned on
      /Admin-Org-Chart/office/<id>/      -> any office's chart: view and edit it,
                                            and show/hide it on that office's page
    """
    actor = get_or_create_lgu_rep(request.user)   # recorded as the one who made the changes
    offices = list(Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG).order_by("display_order", "name"))
    counts = dict(
        OrgChartNode.objects.exclude(office__slug=LGU_SUPER_ADMIN_SLUG)
        .values("office_id").annotate(n=Count("id")).values_list("office_id", "n")
    )
    for o in offices:
        o.org_box_count = counts.get(o.id, 0)

    if office_id is None:
        office = actor.office
        extra = {
            "chart_title": "Municipality of Tunga",
            "publish_place": "the About Us page (Our Officials)",
            "publish_view_url": reverse("about") + "#org-chart",
            "publish_show_label": "Show on About Us page",
            "publish_hide_label": "Hide from About Us page",
        }
    else:
        office = get_object_or_404(Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG), pk=office_id)
        extra = {
            "chart_title": office.name,
            "publish_place": "the office's public page",
            "publish_view_url": (reverse("offices:office_detail", args=[office.slug]) + "#org-chart") if office.slug else "",
        }
    extra.update({"super_admin_page": True, "picker_offices": offices, "picker_office": None if office_id is None else office,
                  "picker_has_charts": any(o.org_box_count for o in offices),
                  "lgu_box_count": OrgChartNode.objects.filter(office__slug=LGU_SUPER_ADMIN_SLUG).count()})
    return org_chart_page(request, actor, "admin_dashboard/super-admin-org-chart.html",
                          can_publish=True, extra=extra, office=office)

@super_admin_required
def admin_emergency_contact(request):
    contacts = EmergencyContact.objects.all()
    return render(request, "admin_dashboard/super-admin-emergency-contacts.html", {"contacts": contacts})


@super_admin_required
def admin_contact_save(request, pk):
    contact = get_object_or_404(EmergencyContact, pk=pk) if pk else EmergencyContact()

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        number = request.POST.get('phone_number', '').strip()

        if not name or not number:
            messages.error(request, "Please fill in at least the service name and phone number.")
        else:
            contact.name = name
            contact.category = request.POST.get('category', 'General')
            contact.carrier_label = request.POST.get('carrier_label', '')
            contact.phone_number = number
            contact.extra_detail = request.POST.get('extra_detail', '')
            contact.icon = request.POST.get('icon', 'fa-phone')
            contact.color = request.POST.get('color', 'gray')
            if not contact.pk:
                # New contacts go to the end, after the default hotlines.
                last = EmergencyContact.objects.order_by('-order').first()
                contact.order = (last.order + 1) if last else 0
            contact.save()
            
            messages.success(request, f'"{name}" was saved.')

    return redirect('admin_dashboard:ad_emergency_contact')


@super_admin_required
def admin_contact_delete(request, pk):
    contact = get_object_or_404(EmergencyContact, pk=pk)
    if request.method == "POST":
        name = contact.name
        contact.delete()
        messages.success(request, f'"{name}" was removed.')
    return redirect('admin_dashboard:ad_emergency_contact')


@super_admin_required
def admin_contact_reset(request):
    """"Reset to default" button: restores the BFP, PNP and MDRRMO hotlines first."""
    if request.method == "POST":
        EmergencyContact.reset_defaults()
        messages.success(request, "Emergency contacts were reset to the defaults: BFP, PNP and MDRRMO.")
    return redirect('admin_dashboard:ad_emergency_contact')

@super_admin_required
def admin_web_setting(request):
    info = SiteContactInfo.get_solo()

    if request.method == "POST":
        section = request.POST.get('section')

        if section == 'appearance':
            if request.FILES.get('logo'):
                info.logo = request.FILES.get('logo')
            if request.FILES.get('hero_banner'):
                info.hero_banner = request.FILES.get('hero_banner')
            elif request.POST.get('reset_hero_banner') == '1' and info.hero_banner:
                # Back to the default LGU building photo: delete the uploaded file
                # (from Cloudinary / media) and clear the field.
                try:
                    info.hero_banner.delete(save=False)
                except Exception:
                    pass  # file already gone — just clear the field
                info.hero_banner = None
            # Header tagline: empty (or "Reset to default") = the original tagline.
            tagline = request.POST.get('site_tagline', '').strip()[:120]
            info.site_tagline = tagline or SiteContactInfo.DEFAULT_TAGLINE
            # Announcement bar speed: a number + "seconds" / "minutes",
            # kept between 1 second and 60 minutes.
            try:
                amount = int(request.POST.get('ticker_interval_value', '') or 0)
            except ValueError:
                amount = 0
            if amount > 0:
                unit = request.POST.get('ticker_interval_unit', 'seconds')
                seconds = amount * 60 if unit == 'minutes' else amount
                info.ticker_interval_seconds = max(1, min(seconds, 3600))
            # Home page News slider speed (seconds per story, 3 to 120)
            try:
                news_secs = int(request.POST.get('news_slider_seconds', '') or 0)
            except ValueError:
                news_secs = 0
            if news_secs > 0:
                info.news_slider_seconds = max(3, min(news_secs, 120))
            info.save()
            messages.success(request, "Appearance settings were updated.")
        elif section == 'social':
            info.social_facebook = request.POST.get('social_facebook', '').strip()
            info.social_twitter = request.POST.get('social_twitter', '').strip()
            info.social_instagram = request.POST.get('social_instagram', '').strip()
            info.social_youtube = request.POST.get('social_youtube', '').strip()
            info.show_facebook_footer = request.POST.get('show_facebook_footer') == 'on'
            info.show_twitter_footer = request.POST.get('show_twitter_footer') == 'on'
            info.show_instagram_footer = request.POST.get('show_instagram_footer') == 'on'
            info.show_youtube_footer = request.POST.get('show_youtube_footer') == 'on'
            info.save()
            messages.success(request, "Social media settings were updated.")
        else:
            info.phone = request.POST.get('phone', '').strip()
            info.phone_local = request.POST.get('phone_local', '').strip()
            info.email = request.POST.get('email', '').strip()
            info.email_secondary = request.POST.get('email_secondary', '').strip()
            info.address = request.POST.get('address', '').strip()
            info.facebook_name = request.POST.get('facebook_name', '').strip()
            info.facebook_url = request.POST.get('facebook_url', '').strip()
            info.office_hours = request.POST.get('office_hours', '').strip()
            # "Our Location" map pin (Contact Us page). Kept inside a box
            # around Leyte so a slip of the mouse can't put it at sea.
            info.map_place_name = request.POST.get('map_place_name', '').strip()[:120] or "Municipal Hall of Tunga"
            try:
                lat = float(request.POST.get('map_latitude', ''))
                lng = float(request.POST.get('map_longitude', ''))
                if 9.8 <= lat <= 12.6 and 124.0 <= lng <= 125.9:
                    info.map_latitude, info.map_longitude = round(lat, 6), round(lng, 6)
                else:
                    messages.error(request, "The map pin must be inside Leyte. The old location was kept.")
            except (TypeError, ValueError):
                pass
            info.save()
            messages.success(request, "Contact information was updated.")

        return redirect(reverse('admin_dashboard:ad_web_setting') + '#' + (section or 'general'))

    return render(request, "admin_dashboard/super-admin-website-settings.html", {
        "info": info,
    })


# Config for every content type that feeds the Analytics & Reports page.
# "date_field" is whichever timestamp each model actually has for "when was
# this submitted" (they're not all named the same), and "office_filter" is
# the lookup used to trace a row back to an office — most content hangs off
# an OfficeRepresentative, but Forms and Services are linked to an Office
# directly.
CONTENT_TYPES_ANALYTICS = [
    {"label": "Announcements", "model": Announcement, "icon": "fa-solid fa-bullhorn", "date_field": "created_at", "office_filter": "representative__office"},
    {"label": "News & Updates", "model": NewsUpdate, "icon": "fa-regular fa-newspaper", "date_field": "created_at", "office_filter": "representative__office"},
    {"label": "Events", "model": Event, "icon": "fa-regular fa-calendar", "date_field": "created_at", "office_filter": "representative__office"},
    {"label": "Downloadable Forms", "model": DownloadableForm, "icon": "fa-solid fa-file-arrow-down", "date_field": "date_uploaded", "office_filter": "office"},
    {"label": "Gallery Photos", "model": Photo, "icon": "fa-regular fa-image", "date_field": "created_at", "office_filter": "representative__office"},
    {"label": "Services", "model": Service, "icon": "fa-solid fa-list-check", "date_field": "published_at", "office_filter": "office"},
]


def _weekly_buckets(dates, week_start, num_weeks=8):
    """Buckets a flat list of date objects into num_weeks weekly buckets
    ending on the current week (oldest first), with each bucket's bar_pct
    scaled against the busiest week — used to draw the plain CSS bar charts
    on the Analytics page without pulling in a charting library."""
    buckets = []
    for i in range(num_weeks - 1, -1, -1):
        w_start = week_start - timedelta(weeks=i)
        w_end = w_start + timedelta(days=6)
        count = sum(1 for d in dates if w_start <= d <= w_end)
        buckets.append({"label": w_start.strftime("%b %d"), "count": count})
    peak = max((b["count"] for b in buckets), default=0) or 1
    for b in buckets:
        b["bar_pct"] = round(b["count"] / peak * 100)
    return buckets


def _avg_turnaround_days(qs, created_field, published_field):
    """Average days between submission and the moment it was actually
    approved — only meaningful for the two content types that stamp a
    separate "published on" date (see _stamp_published_date above); other
    types only know their current status, not when it changed."""
    diffs = []
    for obj in qs.filter(status="published"):
        published = getattr(obj, published_field, None)
        created = getattr(obj, created_field, None)
        if not published or not created:
            continue
        created_date = created.date() if hasattr(created, 'date') else created
        diffs.append((published - created_date).days)
    if not diffs:
        return None
    return round(sum(diffs) / len(diffs), 1)


@super_admin_required
def admin_analytics(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    trend_start = week_start - timedelta(weeks=7)

    offices = Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG)

    # ---- 1. Content Activity Overview ----
    content_overview = []
    submission_dates = []
    for ct in CONTENT_TYPES_ANALYTICS:
        qs = ct["model"].objects.all()
        content_overview.append({
            "label": ct["label"],
            "icon": ct["icon"],
            "total": qs.count(),
            "published": qs.filter(status="published").count(),
            "pending": qs.filter(status__in=["pending", "returned"]).count(),
            "rejected": qs.filter(status="reject").count(),
            "archived": qs.filter(status="archive").count(),
        })
        field = ct["date_field"]
        for v in qs.filter(**{f"{field}__gte": trend_start}).values_list(field, flat=True):
            if v is not None:
                submission_dates.append(v.date() if hasattr(v, 'date') else v)

    submission_weeks = _weekly_buckets(submission_dates, week_start)
    total_published_content = sum(c["published"] for c in content_overview)
    total_pending_content = sum(c["pending"] for c in content_overview)
    services_published_total = Service.objects.filter(status="published").count()

    # ---- 2. Approval turnaround ----
    announcement_turnaround = _avg_turnaround_days(Announcement.objects.all(), 'created_at', 'date_posted')
    news_turnaround = _avg_turnaround_days(NewsUpdate.objects.all(), 'created_at', 'date_published')

    # ---- 3. Office performance ----
    office_performance = []
    for office in offices:
        services_count = Service.objects.filter(office=office).count()
        published_count = (
            Announcement.objects.filter(status="published", representative__office=office).count()
            + NewsUpdate.objects.filter(status="published", representative__office=office).count()
            + Event.objects.filter(status="published", representative__office=office).count()
            + DownloadableForm.objects.filter(status="published", office=office).count()
            + Photo.objects.filter(status="published", representative__office=office).count()
            + Service.objects.filter(status="published", office=office).count()
        )
        pending_count = (
            Announcement.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + NewsUpdate.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + Event.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + DownloadableForm.objects.filter(status__in=["pending", "returned"], office=office).count()
            + Photo.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + Service.objects.filter(status__in=["pending", "returned"], office=office).count()
        )
        office_performance.append({
            "office": office,
            "services_count": services_count,
            "published_count": published_count,
            "pending_count": pending_count,
        })
    office_performance.sort(key=lambda r: (-r["pending_count"], -r["published_count"]))
    offices_with_no_services = [r["office"] for r in office_performance if r["services_count"] == 0]

    # ---- Most active office representatives this month, by logged actions ----
    active_reps_qs = (
        ActivityLog.objects.filter(created_at__date__gte=month_start)
        .values(
            "representative__user__first_name",
            "representative__user__last_name",
            "representative__user__username",
            "representative__office__name",
        )
        .annotate(action_count=Count("id"))
        .order_by("-action_count")[:5]
    )
    active_reps = [
        {
            "name": (f"{r['representative__user__first_name']} {r['representative__user__last_name']}".strip()
                      or r['representative__user__username']),
            "office": r["representative__office__name"],
            "action_count": r["action_count"],
        }
        for r in active_reps_qs
    ]

    # ---- 4. Resident engagement ----
    resident_qs = User.objects.filter(is_staff=False, is_superuser=False, office_rep__isnull=True)
    residents_total = resident_qs.count()
    residents_new_this_week = resident_qs.filter(date_joined__date__gte=week_start).count()
    residents_new_this_month = resident_qs.filter(date_joined__date__gte=month_start).count()
    signup_dates = [
        d.date() if hasattr(d, 'date') else d
        for d in resident_qs.filter(date_joined__date__gte=trend_start).values_list('date_joined', flat=True)
    ]
    signup_weeks = _weekly_buckets(signup_dates, week_start)

    # ---- 5. Most viewed / downloaded content ----
    # Only Announcements, News and Forms actually track this (views /
    # download_count fields) — Events, Photos and Services don't have an
    # equivalent counter yet, so they're left out rather than faked.
    top_announcements = Announcement.objects.filter(status="published").order_by("-views")[:5]
    top_news = NewsUpdate.objects.filter(status="published").order_by("-views")[:5]
    top_forms = DownloadableForm.objects.filter(status="published").order_by("-download_count")[:5]

    # ---- 6. Service directory health ----
    recent_services = Service.objects.filter(status="published").select_related("office").order_by("-published_at")[:5]

    return render(request, "admin_dashboard/super-admin-analytics.html", {
        "content_overview": content_overview,
        "total_published_content": total_published_content,
        "total_pending_content": total_pending_content,
        "services_published_total": services_published_total,
        "submission_weeks": submission_weeks,
        "announcement_turnaround": announcement_turnaround,
        "news_turnaround": news_turnaround,
        "office_performance": office_performance[:8],
        "offices_with_no_services": offices_with_no_services,
        "active_reps": active_reps,
        "residents_total": residents_total,
        "residents_new_this_week": residents_new_this_week,
        "residents_new_this_month": residents_new_this_month,
        "signup_weeks": signup_weeks,
        "top_announcements": top_announcements,
        "top_news": top_news,
        "top_forms": top_forms,
        "recent_services": recent_services,
    })


@super_admin_required
def admin_export_office_activity(request):
    """Downloads the Office Performance table (all offices, not just the
    top 8 shown on-page) as a CSV."""
    offices = Office.objects.exclude(slug=LGU_SUPER_ADMIN_SLUG)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="office-activity-{timezone.localdate()}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Office", "Services Listed", "Published Content", "Pending Items", "Status"])
    for office in offices:
        services_count = Service.objects.filter(office=office).count()
        published_count = (
            Announcement.objects.filter(status="published", representative__office=office).count()
            + NewsUpdate.objects.filter(status="published", representative__office=office).count()
            + Event.objects.filter(status="published", representative__office=office).count()
            + DownloadableForm.objects.filter(status="published", office=office).count()
            + Photo.objects.filter(status="published", representative__office=office).count()
            + Service.objects.filter(status="published", office=office).count()
        )
        pending_count = (
            Announcement.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + NewsUpdate.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + Event.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + DownloadableForm.objects.filter(status__in=["pending", "returned"], office=office).count()
            + Photo.objects.filter(status__in=["pending", "returned"], representative__office=office).count()
            + Service.objects.filter(status__in=["pending", "returned"], office=office).count()
        )
        writer.writerow([
            office.name, services_count, published_count, pending_count,
            "Needs review" if pending_count > 0 else "Up to date",
        ])
    return response


@super_admin_required
def admin_export_approval_history(request):
    """Downloads every item resolved (published or rejected) this month as
    a CSV — the "approval history" report for the current month."""
    today = timezone.localdate()
    month_start = today.replace(day=1)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="approval-history-{today.strftime("%Y-%m")}.csv"'
    writer = csv.writer(response)
    writer.writerow(["Type", "Title", "Office", "Submitted", "Status"])

    rows = []
    for a in Announcement.objects.filter(status__in=["published", "reject"], created_at__date__gte=month_start).select_related('representative__office'):
        rows.append(("Announcement", a.title, a.representative.office.name if a.representative.office else "—", a.created_at.date(), a.get_status_display()))
    for n in NewsUpdate.objects.filter(status__in=["published", "reject"], created_at__date__gte=month_start).select_related('representative__office'):
        rows.append(("News", n.title, n.representative.office.name if n.representative.office else "—", n.created_at.date(), n.get_status_display()))
    for e in Event.objects.filter(status__in=["published", "reject"], created_at__date__gte=month_start).select_related('representative__office'):
        rows.append(("Event", e.title, e.representative.office.name if e.representative.office else "—", e.created_at.date(), e.get_status_display()))
    for f in DownloadableForm.objects.filter(status__in=["published", "reject"], date_uploaded__date__gte=month_start).select_related('office'):
        rows.append(("Form", f.title, f.office.name if f.office else "—", f.date_uploaded.date(), f.get_status_display()))
    for p in Photo.objects.filter(status__in=["published", "reject"], created_at__date__gte=month_start).select_related('representative__office'):
        rows.append(("Gallery", p.title, p.representative.office.name if p.representative.office else "—", p.created_at.date(), p.get_status_display()))
    for s in Service.objects.filter(status__in=["published", "reject"], published_at__date__gte=month_start).select_related('office'):
        rows.append(("Service", s.name, s.office.name if s.office else "—", s.published_at.date(), s.get_status_display()))

    rows.sort(key=lambda r: r[3], reverse=True)
    for row in rows:
        writer.writerow(row)
    return response

@super_admin_required
def admin_activity_log(request):
    q = request.GET.get("q", "").strip()
    office_filter = request.GET.get("office", "").strip()
    category = request.GET.get("category", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    logs = ActivityLog.objects.select_related("representative__user", "representative__office")
    all_count = logs.count()

    if q:
        logs = logs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
            | Q(representative__user__first_name__icontains=q)
            | Q(representative__user__last_name__icontains=q)
            | Q(representative__user__username__icontains=q)
            | Q(representative__office__name__icontains=q)
        )
    if office_filter:
        logs = logs.filter(representative__office__slug=office_filter)
    if category in dict(ActivityLog.CATEGORY_CHOICES):
        logs = logs.filter(category=category)
    else:
        category = ""
    try:
        if date_from:
            logs = logs.filter(created_at__date__gte=date_from)
        if date_to:
            logs = logs.filter(created_at__date__lte=date_to)
    except ValidationError:
        date_from = date_to = ""

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    rows = []
    for log in page_obj:
        name, office_label = activity_actor(log)
        rows.append({"log": log, "name": name, "office": office_label, "tone": activity_tone(log.icon_color)})

    today = timezone.localdate()
    all_logs = ActivityLog.objects.all()
    stats = {
        "total": all_count,
        "today": all_logs.filter(created_at__date=today).count(),
        "week": all_logs.filter(created_at__date__gte=today - timedelta(days=6)).count(),
        "security": all_logs.filter(category="security").count(),
    }

    # Offices that actually have log entries, for the filter dropdown.
    office_options = (
        Office.objects.filter(representative__activity_logs__isnull=False)
        .distinct().order_by("name")
    )

    # Keeps the current filters on the page links.
    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "admin_dashboard/super-admin-activity-logs.html", {
        "rows": rows,
        "page_obj": page_obj,
        "page_range": paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
        "stats": stats,
        "office_options": office_options,
        "category_choices": ActivityLog.CATEGORY_CHOICES,
        "lgu_slug": LGU_SUPER_ADMIN_SLUG,
        "current_q": q,
        "current_office": office_filter,
        "current_category": category,
        "current_from": date_from,
        "current_to": date_to,
        "filters_on": bool(q or office_filter or category or date_from or date_to),
        "query_string": params.urlencode(),
    })

@super_admin_required
def admin_notifications(request):
    """All of the Super Admin's notifications (the bell's "View all")."""
    show = request.GET.get("show", "all")
    notes = AdminNotification.objects.filter(user=request.user)
    unread_count = notes.filter(is_read=False).count()
    if show == "unread":
        notes = notes.filter(is_read=False)
    page_obj = Paginator(notes, 15).get_page(request.GET.get("page"))
    return render(request, "admin_dashboard/super-admin-notifications.html", {
        "page_obj": page_obj,
        "unread_count": unread_count,
        "show": show,
    })


def _safe_next(request, fallback):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback


@super_admin_required
def admin_notification_open(request, pk):
    """Clicking a notification: mark it read, then go to what it is about."""
    note = get_object_or_404(AdminNotification, pk=pk, user=request.user)
    if not note.is_read:
        note.is_read = True
        note.save(update_fields=["is_read"])
    if note.link_url.startswith("/"):
        return redirect(note.link_url)
    return redirect("admin_dashboard:ad_notifications")


@super_admin_required
def admin_notifications_read_all(request):
    if request.method == "POST":
        AdminNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(_safe_next(request, reverse("admin_dashboard:ad_notifications")))


@super_admin_required
def admin_notification_delete(request, pk):
    if request.method == "POST":
        AdminNotification.objects.filter(pk=pk, user=request.user).delete()
    return redirect(_safe_next(request, reverse("admin_dashboard:ad_notifications")))


# ---------------------------------------------------------------------------
# Backup & Restore (the work itself is in admin_dashboard/backup.py)
# ---------------------------------------------------------------------------
@super_admin_required
def admin_backup(request):
    from . import backup
    from .models import BackupSettings, SiteBackup

    settings_obj = BackupSettings.get_solo()
    if request.method == "POST":
        settings_obj.auto_enabled = request.POST.get("auto_enabled") == "on"
        settings_obj.auto_include_files = request.POST.get("auto_include_files") == "on"
        try:
            settings_obj.keep_count = min(60, max(1, int(request.POST.get("keep_count", 14))))
        except ValueError:
            pass
        settings_obj.save()
        backup.cleanup_old_backups()
        messages.success(request, "Backup settings were saved.")
        return redirect("admin_dashboard:ad_backup")

    busy = backup.is_busy()
    settings_obj.refresh_from_db()
    backups = SiteBackup.objects.all()
    last_success = backups.filter(status="success").exclude(kind="uploaded").first()
    storage_label, storage_temporary = backup.storage_description()
    return render(request, "admin_dashboard/super-admin-backup-restore.html", {
        "backups": backups,
        "settings_obj": settings_obj,
        "last_success": last_success,
        "running_backup": backups.filter(status="running").first(),
        "restore_running": settings_obj.restore_status == "running",
        "busy": busy,
        "storage_label": storage_label,
        "storage_temporary": storage_temporary,
        "health": backup.backup_health(),
        "kept_count": backups.filter(status="success", kind__in=["manual", "auto"]).count(),
    })


@super_admin_required
def admin_backup_create(request):
    from . import backup
    if request.method == "POST":
        who = request.user.get_full_name() or request.user.username
        include_files = request.POST.get("include_files") == "on"
        if backup.start_backup("manual", include_files, who):
            messages.success(request, "Backup started" + (" (data and files)" if include_files else " (data only)") +
                             ". It keeps running even if you leave this page.")
        else:
            messages.error(request, "A backup or restore is already running. Please wait for it to finish.")
    return redirect("admin_dashboard:ad_backup")


@super_admin_required
def admin_backup_upload(request):
    from . import backup
    if request.method == "POST":
        f = request.FILES.get("backup_file")
        if not f:
            messages.error(request, "Choose a backup .zip file to upload.")
        elif not f.name.lower().endswith(".zip"):
            messages.error(request, "Backup files are .zip files.")
        else:
            try:
                who = request.user.get_full_name() or request.user.username
                backup.save_uploaded_backup(f, who)
                messages.success(request, f'Backup file "{f.name}" was uploaded and checked. You can restore it from the list.')
            except backup.BackupError as exc:
                messages.error(request, str(exc))
    return redirect("admin_dashboard:ad_backup")


@super_admin_required
def admin_backup_download(request, pk):
    from .backup import get_backup_storage
    from .models import SiteBackup
    record = get_object_or_404(SiteBackup, pk=pk, status="success")
    try:
        fh = get_backup_storage().open(record.filename, "rb")
    except Exception:
        messages.error(request, "That backup file can no longer be found in the backup storage.")
        return redirect("admin_dashboard:ad_backup")
    return FileResponse(fh, as_attachment=True, filename=record.filename.rsplit("/", 1)[-1],
                        content_type="application/zip")


@super_admin_required
def admin_backup_restore(request, pk):
    from . import backup
    from .models import SiteBackup
    record = get_object_or_404(SiteBackup, pk=pk, status="success")
    if request.method != "POST":
        return redirect("admin_dashboard:ad_backup")
    if request.POST.get("confirm_text", "").strip() != "RESTORE":
        messages.error(request, 'Type RESTORE (in capital letters) to confirm.')
    elif not request.user.check_password(request.POST.get("password", "")):
        messages.error(request, "Your password is incorrect. Nothing was restored.")
    else:
        who = request.user.get_full_name() or request.user.username
        if backup.start_restore(record, who):
            messages.success(request, "Restore started. A safety backup of the current site is made first. "
                                      "You may need to log in again when it finishes.")
        else:
            messages.error(request, "A backup or restore is already running. Please wait for it to finish.")
    return redirect("admin_dashboard:ad_backup")


@super_admin_required
def admin_backup_delete(request, pk):
    from . import backup
    from .models import SiteBackup
    record = get_object_or_404(SiteBackup, pk=pk)
    if request.method == "POST":
        if record.status == "running":
            messages.error(request, "That backup is still running.")
        else:
            name = record.filename.rsplit("/", 1)[-1] or f"Backup #{record.pk}"
            backup.delete_backup(record)
            messages.success(request, f'Backup "{name}" was deleted.')
    return redirect("admin_dashboard:ad_backup")


@super_admin_required
def admin_backup_status(request):
    """Polled by the Backup & Restore page while something is running."""
    from . import backup
    from .models import BackupSettings
    s = BackupSettings.get_solo()
    return JsonResponse({"busy": backup.is_busy(), "restore_status": s.restore_status})


@super_admin_required
def admin_system_setting(request):
    email_settings = EmailProviderSettings.get_solo()

    if request.method == "POST":
        email_address = request.POST.get('email_address', '').strip()
        api_key = request.POST.get('api_key', '').strip()

        if not email_address:
            messages.error(request, "Sender email is required.")
        else:
            email_settings.email_address = email_address
            if api_key:
                try:
                    email_settings.set_api_key(api_key)
                except RuntimeError as e:
                    messages.error(request, f"Could not save the API key: {e}")
                    return redirect('admin_dashboard:ad_system_settings')
            email_settings.is_configured = bool(
                email_settings.email_address and email_settings.api_key_encrypted
            )
            email_settings.save()
            messages.success(request, "Email provider settings were saved.")
        return redirect('admin_dashboard:ad_system_settings')

    return render(request, "admin_dashboard/super-admin-system-settings.html", {
        "email_settings": email_settings,
    })

@super_admin_required
def admin_archive(request):
    q = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', 'all')

    items = []
    for a in Announcement.objects.filter(status='archive').select_related('representative__office'):
        items.append({'pk': a.pk, 'title': a.title, 'type': 'Announcement',
                       'office': a.representative.office.name if a.representative.office else '—',
                       'date': a.created_at})
    for n in NewsUpdate.objects.filter(status='archive').select_related('representative__office'):
        items.append({'pk': n.pk, 'title': n.title, 'type': 'News',
                       'office': n.representative.office.name if n.representative.office else '—',
                       'date': n.created_at})
    for e in Event.objects.filter(status='archive').select_related('representative__office'):
        items.append({'pk': e.pk, 'title': e.title, 'type': 'Event',
                       'office': e.representative.office.name if e.representative.office else '—',
                       'date': e.created_at})
    for f in DownloadableForm.objects.filter(status='archive').select_related('office'):
        items.append({'pk': f.pk, 'title': f.title, 'type': 'Form',
                       'office': f.office.name if f.office else '—',
                       'date': f.date_uploaded})
    for p in Photo.objects.filter(status='archive').select_related('representative__office'):
        items.append({'pk': p.pk, 'title': p.title, 'type': 'Gallery',
                       'office': p.representative.office.name if p.representative.office else '—',
                       'date': p.created_at})
    for s in Service.objects.filter(status='archive').select_related('office'):
        items.append({'pk': s.pk, 'title': s.name, 'type': 'Service',
                       'office': s.office.name if s.office else '—',
                       'date': s.published_at})

    type_counts = {}
    for item in items:
        type_counts[item['type']] = type_counts.get(item['type'], 0) + 1

    filtered = items
    if type_filter != 'all':
        filtered = [i for i in filtered if i['type'] == type_filter]
    if q:
        ql = q.lower()
        filtered = [i for i in filtered if ql in i['title'].lower()]

    filtered.sort(key=lambda i: i['date'] or timezone.now(), reverse=True)

    for item in filtered:
        meta = TYPE_META.get(item['type'], {})
        item['tag_class'] = meta.get('tag_class', 'tag-gray')
        item['icon'] = meta.get('icon', 'fa-solid fa-file')
        item['thumb_class'] = meta.get('thumb_class', 'tag-gray')

    paginator = Paginator(filtered, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "admin_dashboard/super-admin-archive.html", {
        "page_obj": page_obj,
        "total_count": len(items),
        "type_counts": type_counts,
        "current_q": q,
        "current_type": type_filter,
    })

@super_admin_required
def admin_archive_restore(request, item_type, pk):
    model = MODEL_MAP.get(item_type)
    if model is None:
        raise Http404("Unknown content type.")
    obj = get_object_or_404(model, pk=pk)

    if request.method == "POST":
        title = getattr(obj, 'title', None) or getattr(obj, 'name', '')
        obj.status = 'published'
        _stamp_published_date(obj)
        obj.save()
        messages.success(request, f'"{title}" was restored and published again.')

    return redirect('admin_dashboard:ad_archive')

@super_admin_required
def admin_archive_delete_permanent(request, item_type, pk):
    model = MODEL_MAP.get(item_type)
    if model is None:
        raise Http404("Unknown content type.")
    obj = get_object_or_404(model, pk=pk)

    if request.method == "POST":
        title = getattr(obj, 'title', None) or getattr(obj, 'name', '')
        image_field = getattr(obj, 'image', None) or getattr(obj, 'poster', None) or getattr(obj, 'file', None)
        if image_field:
            image_field.delete(save=False)
        obj.delete()
        messages.success(request, f'"{title}" was permanently deleted.')

    return redirect('admin_dashboard:ad_archive')


# ---------------------------------------------------------------------------
# Messages: the Super Admin's side of the chat with each Office Representative.
# One conversation per representative; the page lists them and
# static/js/messages.js loads / polls / sends through the JSON endpoints.
# ---------------------------------------------------------------------------
def _message_conversations():
    """Every real office representative with their latest message and the
    number of messages from them the Super Admin hasn't opened yet. Ones with
    a conversation come first (most recent on top), then the rest by office."""
    reps = (
        OfficeRepresentative.objects
        .exclude(office__slug=LGU_SUPER_ADMIN_SLUG)
        .select_related("office", "user")
    )
    rows = []
    for rep in reps:
        last = rep.chat_messages.order_by("-id").first()
        unread = rep.chat_messages.filter(sender=Message.SENDER_REP, read_at__isnull=True).count()
        rows.append({
            "rep": rep,
            "office_name": rep.office.name,
            "person": rep.user.get_full_name() or rep.user.username,
            "last_body": last.body if last else "",
            "last_sender": last.sender if last else "",
            "last_time": timezone.localtime(last.created_at) if last else None,
            "unread": unread,
        })
    rows.sort(key=lambda r: (r["last_time"] is None, -(r["last_time"].timestamp() if r["last_time"] else 0), r["office_name"].lower()))
    return rows


@super_admin_required
def admin_messages(request):
    conversations = _message_conversations()
    selected = None
    rep_id = request.GET.get("rep")
    if rep_id and rep_id.isdigit():
        selected = next((c for c in conversations if c["rep"].id == int(rep_id)), None)
    if selected:
        # Clicking an office marks its messages as read right away, so the
        # red number next to "Messages" in the sidebar is already updated
        # on this page (not only after the next refresh).
        rep = selected["rep"]
        rep.chat_messages.filter(sender=Message.SENDER_REP, read_at__isnull=True).update(read_at=timezone.now())
        AdminNotification.objects.filter(
            user=request.user, is_read=False,
            link_url=reverse("admin_dashboard:ad_messages") + f"?rep={rep.pk}",
        ).update(is_read=True)
        selected["unread"] = 0
    return render(request, "admin_dashboard/super-admin-messages.html", {
        "conversations": conversations,
        "selected": selected,
    })


@super_admin_required
def admin_messages_data(request):
    rep = get_object_or_404(OfficeRepresentative.objects.exclude(office__slug=LGU_SUPER_ADMIN_SLUG), pk=request.GET.get("rep") or 0)
    try:
        after = int(request.GET.get("after", 0))
    except (TypeError, ValueError):
        after = 0

    # Opening a conversation also clears the bell's "New message" notice for it.
    AdminNotification.objects.filter(
        user=request.user, is_read=False,
        link_url=reverse("admin_dashboard:ad_messages") + f"?rep={rep.pk}",
    ).update(is_read=True)

    # Opening a conversation marks that representative's messages as read.
    rep.chat_messages.filter(
        sender=Message.SENDER_REP, read_at__isnull=True
    ).update(read_at=timezone.now())

    items = rep.chat_messages.filter(id__gt=after)
    unread = {str(c["rep"].id): c["unread"] for c in _message_conversations()}
    return JsonResponse({
        "messages": [serialize_chat_message(m) for m in items],
        "unread": unread,
        "unread_total": sum(unread.values()),
    })


@super_admin_required
def admin_messages_send(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required."}, status=405)
    rep = get_object_or_404(OfficeRepresentative.objects.exclude(office__slug=LGU_SUPER_ADMIN_SLUG), pk=request.POST.get("rep") or 0)
    body = request.POST.get("body", "").strip()
    if not body:
        return JsonResponse({"success": False, "error": "Type a message first."}, status=400)
    if len(body) > MESSAGE_MAX_LENGTH:
        return JsonResponse({"success": False, "error": f"Messages are limited to {MESSAGE_MAX_LENGTH} characters."}, status=400)

    msg = Message.objects.create(representative=rep, sender=Message.SENDER_ADMIN, body=body)

    # Let the representative know through their normal notifications too —
    # one unread "new message" notification at a time, so a back-and-forth
    # doesn't pile up dozens of them.
    title = "New message from the Super Admin"
    if not Notification.objects.filter(representative=rep, title=title, is_read=False).exists():
        notify(
            rep, 'messages',
            title=title,
            description=body[:120],
            level="info",
            link_url=reverse("office_dashboard:messages"),
        )
    return JsonResponse({"success": True, "message": serialize_chat_message(msg)})