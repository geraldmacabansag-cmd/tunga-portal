from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SuperAdmin, SiteContactInfo, EmergencyContact, EmailProviderSettings, QuickLink, AboutPageContent, HistoryMilestone, AboutOfficial, Barangay
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from office_dashboard.models import Announcement, NewsUpdate, Event, DownloadableForm, Photo, Album, Service, OfficeRepresentative, Notification, ServiceEditSettings
from offices.models import Office
from django.http import Http404, FileResponse, HttpResponse
from datetime import timedelta
import io
from office_dashboard.views import FORM_CATEGORY_CHOICES
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
        return view_func(request, *args, **kwargs)
    return wrapper


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

    return render(request, "admin_dashboard/super-admin-dashboard.html", {
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

    if request.method == "POST":
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()

        if not full_name:
            messages.error(request, "Full name is required.")
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
                messages.success(request, "Account details updated.")
        return redirect('admin_dashboard:admin_account')

    return render(request, "admin_dashboard/super-admin-my-account.html", {"super_admin": super_admin})


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
    Gallery, Service) has no such field and is left alone."""
    if isinstance(obj, Announcement):
        obj.date_posted = timezone.localdate()
    elif isinstance(obj, NewsUpdate):
        obj.date_published = timezone.localdate()

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
                Notification.objects.create(
                    representative=notify_rep,
                    link_url=content_link_url,
                    title=f'"{display_name}" was approved',
                    description=f'Your {item_type.lower()} submission is now published on the public website.',
                    level='success',
                )
        elif action == 'return':
            obj.status = 'returned'
            messages.success(request, f'"{display_name}" was returned for revision.')
            if notify_rep:
                Notification.objects.create(
                    representative=notify_rep,
                    link_url=content_link_url,
                    title=f'"{display_name}" was returned for revision',
                    description=note or f'Your {item_type.lower()} submission needs changes before it can be published. Check the admin note for details.',
                    level='warning',
                )
        elif action == 'reject':
            obj.status = 'reject'
            messages.success(request, f'"{display_name}" was rejected.')
            if notify_rep:
                Notification.objects.create(
                    representative=notify_rep,
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

        if not title:
            messages.error(request, "Title is required.")
        elif not rep:
            messages.error(request, "Please select an office with an assigned representative.")
        else:
            Announcement.objects.create(
                representative=rep,
                title=title,
                subtitle=request.POST.get('subtitle', '').strip(),
                category=request.POST.get('category', '').strip(),
                content=request.POST.get('content', '').strip(),
                image=request.FILES.get('image'),
                author=request.POST.get('author', '').strip(),
                # Super Admin publishes this immediately, so "date posted" is
                # simply today — never a manually-entered date.
                date_posted=timezone.localdate(),
                expiration_date=request.POST.get('expiration_date') or None,
                priority=request.POST.get('priority', 'Normal'),
                status='published',
            )
            messages.success(request, f'"{title}" was published.')

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

        if not title:
            messages.error(request, "Title is required.")
        elif not rep:
            messages.error(request, "Please select an office with an assigned representative.")
        else:
            announcement.representative = rep
            announcement.title = title
            announcement.subtitle = request.POST.get('subtitle', '').strip()
            announcement.category = request.POST.get('category', '').strip()
            announcement.content = request.POST.get('content', '').strip()
            if request.FILES.get('image'):
                announcement.image = request.FILES.get('image')
            announcement.author = request.POST.get('author', '').strip()
            # date_posted is intentionally left untouched here — it's only
            # ever set automatically, when the announcement is approved/
            # published (see admin_approval_details / _stamp_published_date).
            announcement.expiration_date = request.POST.get('expiration_date') or None
            announcement.priority = request.POST.get('priority', 'Normal')
            announcement.save()
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
    """Streams a form's PDF through our own server (for the 'View Details'
    modal and the approval-details Attachment link) instead of linking
    straight to the storage backend's public URL. Cloudinary blocks
    unsigned/direct access to PDF and ZIP files by default and returns a
    401 — opening the file through Django's storage API here uses
    authenticated access instead, so it works regardless of that setting.
    No download_count bump here since this is just viewing, not downloading."""
    form = get_object_or_404(DownloadableForm, pk=pk)

    try:
        form.file.open('rb')
        data = form.file.read()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(
            "Could not load the PDF from storage: %s: %s" % (type(e).__name__, e),
            status=500,
            content_type="text/plain",
        )
    finally:
        try:
            form.file.close()
        except Exception:
            pass

    return FileResponse(io.BytesIO(data), content_type="application/pdf")


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

    rows.sort(key=lambda r: r["office"].name)

    return render(request, "admin_dashboard/super-admin-office-overview.html", {
        "rows": rows,
        "total_offices": len(all_offices),
        "active_count": active_count,
        "pending_count": pending_count,
        "inactive_count": inactive_count,
        "current_q": q,
        "current_status": status_filter,
    })

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
    quick_links = QuickLink.objects.all()
    today = timezone.localdate()
 
    return render(request, "admin_dashboard/super-admin-homepage.html", {
        "quick_links": quick_links,
        "quick_links_active_count": quick_links.filter(is_active=True).count(),
        "quick_links_total_count": quick_links.count(),
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
 
        if not label or not url:
            messages.error(request, "Please fill in both the label and the link URL.")
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
def admin_web_setting(request):
    info = SiteContactInfo.get_solo()

    if request.method == "POST":
        section = request.POST.get('section')

        if section == 'appearance':
            if request.FILES.get('logo'):
                info.logo = request.FILES.get('logo')
            if request.FILES.get('hero_banner'):
                info.hero_banner = request.FILES.get('hero_banner')
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
            info.save()
            messages.success(request, "Contact information was updated.")

        return redirect(reverse('admin_dashboard:ad_web_setting') + '#' + (section or 'general'))

    return render(request, "admin_dashboard/super-admin-website-settings.html", {
        "info": info,
    })


@super_admin_required
def admin_analytics(request):
    return render(request, "admin_dashboard/super-admin-analytics.html")

@super_admin_required
def admin_activity_log(request):
    return render(request, "admin_dashboard/super-admin-activity-logs.html")

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