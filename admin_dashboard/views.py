from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SuperAdmin, SiteContactInfo, EmergencyContact
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from django.utils import timezone
from office_dashboard.models import Announcement, NewsUpdate, Event, DownloadableForm, Photo, Album, Service, OfficeRepresentative
from offices.models import Office
from django.http import Http404
from datetime import timedelta


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

@super_admin_required
def admin_approval_details(request, item_type, pk):
    model = MODEL_MAP.get(item_type)
    if model is None:
        raise Http404("Unknown submission type.")

    if model is DownloadableForm:
        obj = get_object_or_404(model.objects.select_related('office'), pk=pk)
        office = obj.office
        submitted_by_name = obj.uploaded_by or "—"
    elif model is Service:
        obj = get_object_or_404(model.objects.select_related('office'), pk=pk)
        office = obj.office
        rep = getattr(office, 'representative', None)
        submitted_by_name = (rep.user.get_full_name() or rep.user.username) if rep else "—"
    else:
        obj = get_object_or_404(model.objects.select_related('representative__office', 'representative__user'), pk=pk)
        office = obj.representative.office
        submitted_by_name = obj.representative.user.get_full_name() or obj.representative.user.username

    obj_label = getattr(obj, 'title', None) or getattr(obj, 'name', '')

    if request.method == "POST":
        action = request.POST.get('action')
        note = request.POST.get('note', '').strip()

        if note:
            obj.admin_note = note

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

    date_submitted = getattr(obj, 'created_at', None) or getattr(obj, 'date_uploaded', None) or getattr(obj, 'published_at', None)

    return render(request, "admin_dashboard/super-admin-approval-details.html", {
        "obj": obj,
        "obj_label": obj_label,
        "item_type": item_type,
        "office": office,
        "submitted_by_name": submitted_by_name,
        "date_submitted": date_submitted,
        "tag_class": TYPE_META.get(item_type, {}).get('tag_class', 'tag-gray'),
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
    qs = (Announcement.objects
          .select_related('representative__office')
          .filter(status='published')
          .order_by('-date_posted', '-created_at'))

    total_count = qs.count()
    total_views = qs.aggregate(total=Sum('views'))['total'] or 0

    announcements = list(qs)
    for a in announcements:
        a.badge_class = ANNOUNCEMENT_STATUS_BADGE.get(a.status, 'badge-gray')

    return render(request, "admin_dashboard/super-admin-announcements.html", {
        "announcements": announcements,
        "total_count": total_count,
        "total_views": total_views,
    })
NEWS_STATUS_BADGE = {
    "pending": "badge-amber",
    "published": "badge-green",
    "returned": "badge-red",
    "reject": "badge-red",
    "archive": "badge-gray",
}

@super_admin_required
def admin_news_update(request):
    qs = (NewsUpdate.objects
          .select_related('representative__office')
          .filter(status='published')
          .order_by('-date_published', '-created_at'))

    total_count = qs.count()
    total_views = qs.aggregate(total=Sum('views'))['total'] or 0

    news_items = list(qs)
    for n in news_items:
        n.badge_class = NEWS_STATUS_BADGE.get(n.status, 'badge-gray')

    return render(request, "admin_dashboard/super-admin-news-updates.html", {
        "news_items": news_items,
        "total_count": total_count,
        "total_views": total_views,
    })

@super_admin_required
def admin_news_save(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard:ad_news_update')

    title = request.POST.get('title', '').strip()
    rep_id = request.POST.get('representative')
    representative = OfficeRepresentative.objects.filter(pk=rep_id).first() if rep_id else None

    if not title or not representative:
        messages.error(request, "Headline and posting office are required.")
        return redirect('admin_dashboard:ad_news_update')

    if pk:
        n = get_object_or_404(NewsUpdate, pk=pk)
    else:
        n = NewsUpdate()

    n.representative = representative
    n.title = title
    n.category = request.POST.get('category', '').strip()
    n.summary = request.POST.get('summary', '').strip()
    n.content = request.POST.get('content', '').strip()
    n.date_published = request.POST.get('date_published') or None
    n.status = request.POST.get('status', 'pending')

    image = request.FILES.get('image')
    if image:
        n.image = image

    n.save()
    messages.success(request, f'"{title}" was saved.')
    return redirect('admin_dashboard:ad_news_update')

@super_admin_required
def admin_news_delete(request, pk):
    n = get_object_or_404(NewsUpdate, pk=pk)
    if request.method == "POST":
        title = n.title
        n.delete()
        messages.success(request, f'"{title}" was deleted.')
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
    qs = Event.objects.filter(status='published').select_related('representative__office').order_by('-event_date', '-created_at')

    today = timezone.localdate()
    total_count = qs.count()
    upcoming_count = qs.filter(event_date__gte=today).count()
    past_count = qs.filter(event_date__lt=today).count()

    events = list(qs)
    for e in events:
        e.badge_class = EVENT_STATUS_BADGE.get(e.status, 'badge-gray')

    office_reps = OfficeRepresentative.objects.select_related('office', 'user').order_by('office__name')

    return render(request, "admin_dashboard/super-admin-events.html", {
        "events": events,
        "total_count": total_count,
        "upcoming_count": upcoming_count,
        "past_count": past_count,
        "office_reps": office_reps,
    })

@super_admin_required
def admin_event_save(request, pk):
    if request.method != "POST":
        return redirect('admin_dashboard:ad_events')

    title = request.POST.get('title', '').strip()
    rep_id = request.POST.get('representative')
    representative = OfficeRepresentative.objects.filter(pk=rep_id).first() if rep_id else None

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
    e.status = request.POST.get('status', 'pending')

    poster = request.FILES.get('poster')
    if poster:
        e.poster = poster

    e.save()
    messages.success(request, f'"{title}" was saved.')
    return redirect('admin_dashboard:ad_events')

@super_admin_required
def admin_event_delete(request, pk):
    e = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        title = e.title
        e.delete()
        messages.success(request, f'"{title}" was deleted.')
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
    })

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
        a.cover = a.photos.filter(status='published').order_by('-created_at').first()

    published_photos = Photo.objects.filter(status='published')
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return render(request, "admin_dashboard/super-admin-gallery.html", {
        "albums": albums,
        "total_albums": len(albums),
        "total_photos": published_photos.count(),
        "archived_photos": Photo.objects.filter(status='archive').count(),
        "recent_photos": published_photos.filter(created_at__gte=month_start).count(),
        "current_q": q,
        "current_sort": sort,
    })


@super_admin_required
def admin_album_detail(request, pk):
    album = get_object_or_404(Album.objects.select_related('representative__office'), pk=pk)
    photos = album.photos.filter(status__in=['published', 'archive']).order_by('-created_at')

    tab = request.GET.get('tab', 'all')
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
    })


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
    album_id = photo.album_id
    if request.method == "POST":
        title = photo.title
        photo.delete()
        messages.success(request, f'"{title}" was deleted.')
    return redirect('admin_dashboard:ad_album_detail', pk=album_id)

@super_admin_required
def admin_offices(request):
    all_offices = list(Office.objects.select_related('representative__user'))

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
def admin_office_rep(request):
    reps = list(OfficeRepresentative.objects.select_related('user', 'office'))

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

    total_offices = Office.objects.count()
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
        "offices": Office.objects.order_by('name'),
        "total_reps": len(reps),
        "total_offices": total_offices,
        "active_count": active_count,
        "pending_count": pending_count,
        "inactive_count": inactive_count,
        "offices_without_rep": offices_without_rep,
        "current_q": q,
        "current_office": office_id,
        "current_status": status_filter,
    })


@super_admin_required
def admin_rep_toggle_active(request, pk):
    rep = get_object_or_404(OfficeRepresentative, pk=pk)
    if request.method == "POST":
        rep.user.is_active = not rep.user.is_active
        rep.user.save()
        label = rep.user.get_full_name() or rep.user.username
        messages.success(request, f'{label} was {"activated" if rep.user.is_active else "deactivated"}.')
    return redirect('admin_dashboard:ad_office_rep')

@super_admin_required
def admin_services(request):
    q = request.GET.get('q', '').strip()

    services = (Service.objects
                .filter(status='published')
                .select_related('office')
                .order_by('name'))

    if q:
        services = services.filter(Q(name__icontains=q) | Q(office__name__icontains=q))

    total_count = Service.objects.filter(status='published').count()

    paginator = Paginator(services, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "admin_dashboard/super-admin-services.html", {
        "page_obj": page_obj,
        "total_count": total_count,
        "current_q": q,
    })


@super_admin_required
def admin_service_detail(request, pk):
    service = get_object_or_404(Service.objects.select_related('office'), pk=pk, status='published')
    return render(request, "admin_dashboard/super-admin-service-detail.html", {
        "service": service,
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
    return render(request, "admin_dashboard/super-admin-homepage.html")

@super_admin_required
def admin_contact_info(request):
    info = SiteContactInfo.get_solo()

    if request.method == "POST":
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
        return redirect('admin_dashboard:ad_contact_info')

    return render(request, "admin_dashboard/super-admin-contact-info.html", {
        "info": info,
    })

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