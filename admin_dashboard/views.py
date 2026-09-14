from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SuperAdmin
from django.core.paginator import Paginator
from django.utils import timezone
from office_dashboard.models import Announcement, NewsUpdate, Event, DownloadableForm, Photo
from django.http import Http404

def super_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not SuperAdmin.objects.filter(user=request.user).exists():
            messages.error(request, "You don't have access to the Super Admin dashboard.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper


@super_admin_required
def dashboard(request):
    return render(request, "admin_dashboard/super-admin-dashboard.html")

TYPE_META = {
    "Announcement": {"tag_class": "tag-blue", "icon": "fa-solid fa-bullhorn", "thumb_class": "tag-blue"},
    "Form": {"tag_class": "tag-green", "icon": "fa-regular fa-file-lines", "thumb_class": "tag-green"},
    "News": {"tag_class": "tag-purple", "icon": "fa-regular fa-newspaper", "thumb_class": "tag-purple"},
    "Event": {"tag_class": "tag-blue", "icon": "fa-regular fa-calendar", "thumb_class": "tag-blue"},
    "Gallery": {"tag_class": "tag-pink", "icon": "fa-regular fa-image", "thumb_class": "tag-pink"},
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
}

@super_admin_required
def admin_approval_details(request, item_type, pk):
    model = MODEL_MAP.get(item_type)
    if model is None:
        raise Http404("Unknown submission type.")

    if model is DownloadableForm:
        obj = get_object_or_404(model.objects.select_related('office'), pk=pk)
        office = obj.office
        submitted_by_name = obj.uploaded_by or "—"
    else:
        obj = get_object_or_404(model.objects.select_related('representative__office', 'representative__user'), pk=pk)
        office = obj.representative.office
        submitted_by_name = obj.representative.user.get_full_name() or obj.representative.user.username

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'approve':
            obj.status = 'published'
            messages.success(request, f'"{obj.title}" was approved and published.')
        elif action == 'return':
            obj.status = 'returned'
            messages.success(request, f'"{obj.title}" was returned for revision.')
        elif action == 'reject':
            obj.status = 'reject'
            messages.success(request, f'"{obj.title}" was rejected.')
        obj.save()
        return redirect('admin_dashboard:approval_center')

    date_submitted = getattr(obj, 'created_at', None) or getattr(obj, 'date_uploaded', None)

    return render(request, "admin_dashboard/super-admin-approval-details.html", {
        "obj": obj,
        "item_type": item_type,
        "office": office,
        "submitted_by_name": submitted_by_name,
        "date_submitted": date_submitted,
        "tag_class": TYPE_META.get(item_type, {}).get('tag_class', 'tag-gray'),
    })

@super_admin_required
def admin_announcement(request):
    return render(request, "admin_dashboard/super-admin-announcements.html")

@super_admin_required
def admin_news_update(request):
    return render(request, "admin_dashboard/super-admin-news-updates.html")

@super_admin_required
def admin_events(request):
    return render(request, "admin_dashboard/super-admin-events.html")

@super_admin_required
def admin_download_forms(request):
    return render(request, "admin_dashboard/super-admin-downloadable-forms.html")

@super_admin_required
def admin_gallery(request):
    return render(request, "admin_dashboard/super-admin-gallery.html")

@super_admin_required
def admin_offices(request):
    return render(request, "admin_dashboard/super-admin-office-overview.html")

@super_admin_required
def admin_office_rep(request):
    return render(request, "admin_dashboard/super-admin-office-reps.html")

@super_admin_required
def admin_services(request):
    return render(request, "admin_dashboard/super-admin-services.html")

@super_admin_required
def admin_users(request):
    return render(request, "admin_dashboard/super-admin-users.html")

@super_admin_required
def admin_roles(request):
    return render(request, "admin_dashboard/super-admin-roles.html")

@super_admin_required
def admin_homepage(request):
    return render(request, "admin_dashboard/super-admin-homepage.html")

@super_admin_required
def admin_contact_info(request):
    return render(request, "admin_dashboard/super-admin-contact-info.html")

@super_admin_required
def admin_interactive_map(request):
    return render(request, "admin_dashboard/super-admin-interactive-map.html")

@super_admin_required
def admin_emergency_contact(request):
    return render(request, "admin_dashboard/super-admin-emergency-contacts.html")

@super_admin_required
def admin_web_setting(request):
    return render(request, "admin_dashboard/super-admin-website-settings.html")

@super_admin_required
def admin_analytics(request):
    return render(request, "admin_dashboard/super-admin-analytics.html")

@super_admin_required
def admin_activity_log(request):
    return render(request, "admin_dashboard/super-admin-activity-logs.html")

@super_admin_required
def admin_system_setting(request):
    return render(request, "admin_dashboard/super-admin-system-settings.html")