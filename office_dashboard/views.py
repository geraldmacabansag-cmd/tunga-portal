from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo, Album, Service, ProcessStep, Requirement, DownloadableForm, Notification, FormField, ServiceEditSettings

import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.utils import timezone

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from datetime import datetime
from django.db.models import Count, F, Sum
from django.http import FileResponse, Http404, JsonResponse, HttpResponse
from django.template.defaultfilters import date as django_date_format

from .models import (
    OfficeRepresentative, Announcement, NewsUpdate, Event, Photo, Album,
    Notification, ActivityLog, log_activity,
)

from itertools import groupby
from datetime import timedelta

from admin_dashboard.models import SuperAdmin


def office_rep_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if SuperAdmin.objects.filter(user=request.user).exists():
            messages.error(request, "Super Admin accounts use the Super Admin dashboard, not the Office Representative dashboard.")
            return redirect("admin_dashboard:admin_dash")

        rep = OfficeRepresentative.objects.filter(user=request.user).first()
        if rep is None:
            messages.error(request, "Your account isn't linked to an Office Representative profile.")
            return redirect("home")
        return view_func(request, rep, *args, **kwargs)
    return wrapper

@office_rep_required
def rep_announcement(request, rep):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        title = request.POST.get('title', '').strip()
        if not title:
            if is_ajax:
                return JsonResponse({"success": False, "error": "Announcement title is required."}, status=400)
            messages.error(request, "Announcement title is required.")
        else:
            announcement = Announcement.objects.create(
                representative=rep,
                title=title,
                subtitle=request.POST.get('subtitle', ''),
                category=request.POST.get('category', ''),
                content=request.POST.get('content', ''),
                image=request.FILES.get('image'),
                author=request.POST.get('author', ''),
                date_posted=request.POST.get('date_posted') or None,
                expiration_date=request.POST.get('expiration_date') or None,
                priority=request.POST.get('priority', 'Normal'),
            )
            log_activity(rep, "Announcement submitted", f'Submitted "{title}" for approval', "content", "fa-solid fa-bullhorn", "var(--blue-600)")
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "title": announcement.title,
                    "created_at": django_date_format(timezone.localtime(announcement.created_at), "F j, Y · g:i A"),
                    "status": announcement.status,
                    "status_display": announcement.get_status_display(),
                })
            messages.success(request, f'"{title}" was created and is pending approval.')
        return redirect('office_dashboard:rep_announce')

    announcements = rep.announcements.all()

    q = request.GET.get('q', '').strip()
    if q:
        announcements = announcements.filter(title__icontains=q)

    status = request.GET.get('status', '')
    if status:
        announcements = announcements.filter(status=status)

    sort = request.GET.get('sort', 'newest')
    announcements = announcements.order_by('created_at' if sort == 'oldest' else '-created_at')
    all_announcements = rep.announcements.all()
    total_count = all_announcements.count()
    published_count = all_announcements.filter(status='published').count()
    pending_count = all_announcements.filter(status='pending').count()
    returned_count = all_announcements.filter(status='returned').count()

    paginator = Paginator(announcements, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "office_dashboard/announcements.html", {
        "rep": rep,
        "page_obj": page_obj,
        "announcements": page_obj.object_list,
        "current_q": q,
        "current_status": status,
        "current_sort": sort,
        "total_count": total_count,
        "published_count": published_count,
        "pending_count": pending_count,
        "returned_count": returned_count,
    })

@office_rep_required
def edit_announcement(request, rep, pk):
    announcement = get_object_or_404(Announcement, pk=pk, representative=rep)

    if announcement.status == 'published':
        messages.error(request, "This announcement is already published and can no longer be edited.")
        return redirect('office_dashboard:rep_announce')


    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Title is required.")
        else:
            announcement.title = title
            announcement.subtitle = request.POST.get('subtitle', '')
            announcement.category = request.POST.get('category', '')
            announcement.content = request.POST.get('content', '')
            if request.FILES.get('image'):
                announcement.image = request.FILES.get('image')
            announcement.author = request.POST.get('author', '')
            announcement.date_posted = request.POST.get('date_posted') or None
            announcement.expiration_date = request.POST.get('expiration_date') or None
            announcement.priority = request.POST.get('priority', 'Normal')
            announcement.save()   # last_updated is stamped automatically here
            messages.success(request, f'"{title}" was updated.')
            log_activity(rep, "Announcement updated", f'Updated "{title}"', "content", "fa-regular fa-pen-to-square", "var(--blue-600)")
        return redirect('office_dashboard:rep_announce')

    return redirect('office_dashboard:rep_announce')


@office_rep_required
def delete_announcement(request, rep, pk):
    announcement = get_object_or_404(Announcement, pk=pk, representative=rep)

    if request.method == "POST":
        title = announcement.title
        announcement.delete()
        messages.success(request, f'"{title}" was deleted.')
        log_activity(rep, "Announcement deleted", f'Deleted "{title}"', "content", "fa-regular fa-trash-can", "var(--red-600)")

    return redirect('office_dashboard:rep_announce')

@office_rep_required
def dashboard(request, rep):
    today = timezone.localdate()

    announcements_count = rep.announcements.count()
    news_count = rep.news_updates.count()
    events_count = rep.events.filter(event_date__gte=today).count()
    forms_count = rep.office.downloadable_forms.count()
    photos_count = rep.photos.count()

    recent_announcements = rep.announcements.order_by('-created_at')[:4]
    recent_news = rep.news_updates.order_by('-created_at')[:3]
    upcoming_events = rep.events.filter(event_date__gte=today).order_by('event_date')[:3]

    # ---- Content Overview chart: real "This Month" / "Last Month" scoping ----
    first_of_this_month = today.replace(day=1)
    if first_of_this_month.month == 1:
        first_of_last_month = first_of_this_month.replace(year=first_of_this_month.year - 1, month=12)
    else:
        first_of_last_month = first_of_this_month.replace(month=first_of_this_month.month - 1)

    chart_range = request.GET.get('range', 'month')
    if chart_range == 'last_month':
        range_start, range_end, range_label = first_of_last_month, first_of_this_month, "Last Month"
    else:
        chart_range = 'month'
        range_start, range_end, range_label = first_of_this_month, today + timedelta(days=1), "This Month"

    chart_announcements = rep.announcements.filter(created_at__date__gte=range_start, created_at__date__lt=range_end)
    chart_news = rep.news_updates.filter(created_at__date__gte=range_start, created_at__date__lt=range_end)
    chart_events = rep.events.filter(created_at__date__gte=range_start, created_at__date__lt=range_end)
    chart_forms = rep.office.downloadable_forms.filter(date_uploaded__date__gte=range_start, date_uploaded__date__lt=range_end)
    chart_photos = rep.photos.filter(created_at__date__gte=range_start, created_at__date__lt=range_end)

    counts = {
        "announcements": chart_announcements.count(),
        "news": chart_news.count(),
        "events": chart_events.count(),
        "forms": chart_forms.count(),
        "photos": chart_photos.count(),
    }
    max_count = max(counts.values()) or 1
    bar_heights = {key: round(value / max_count * 100) for key, value in counts.items()}

    total_views = (
        (chart_announcements.aggregate(total=Sum('views'))['total'] or 0)
        + (chart_news.aggregate(total=Sum('views'))['total'] or 0)
    )
    total_downloads = chart_forms.aggregate(total=Sum('download_count'))['total'] or 0

    return render(request, "office_dashboard/dashboard.html", {
        "rep": rep,
        "announcements_count": announcements_count,
        "news_count": news_count,
        "events_count": events_count,
        "forms_count": forms_count,
        "photos_count": photos_count,
        "chart_counts": counts,
        "bar_heights": bar_heights,
        "chart_range": chart_range,
        "range_label": range_label,
        "total_views": total_views,
        "total_downloads": total_downloads,
        "recent_announcements": recent_announcements,
        "recent_news": recent_news,
        "upcoming_events": upcoming_events,
        "all_albums_for_upload": rep.albums.order_by('name'),
        "category_choices": FORM_CATEGORY_CHOICES,
    })

@office_rep_required
def news_update(request, rep):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        title = request.POST.get('title', '').strip()
        if not title:
            if is_ajax:
                return JsonResponse({"success": False, "error": "News headline is required."}, status=400)
            messages.error(request, "News headline is required.")
        else:
            news = NewsUpdate.objects.create(
                representative=rep,
                title=title,
                category=request.POST.get('category', ''),
                summary=request.POST.get('summary', ''),
                content=request.POST.get('content', ''),
                image=request.FILES.get('image'),
                author=request.POST.get('author', ''),
                date_published=request.POST.get('date_published') or None,
                source=request.POST.get('source', ''),
                tags=request.POST.get('tags', ''),
            )
            log_activity(rep, "News published", f'Added "{title}"', "content", "fa-regular fa-newspaper", "#12b3c4")
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "title": news.title,
                    "created_at": django_date_format(timezone.localtime(news.created_at), "F j, Y · g:i A"),
                    "status": news.status,
                    "status_display": news.get_status_display(),
                })
            messages.success(request, f'"{title}" was added.')
        return redirect('office_dashboard:news_update')

    news_items = rep.news_updates.all()

    q = request.GET.get('q', '').strip()
    if q:
        news_items = news_items.filter(title__icontains=q)

    status = request.GET.get('status', '')
    if status:
        news_items = news_items.filter(status=status)

    sort = request.GET.get('sort', 'newest')
    news_items = news_items.order_by('created_at' if sort == 'oldest' else '-created_at')
    all_news = rep.news_updates.all()
    total_count = all_news.count()
    published_count = all_news.filter(status='published').count()
    pending_count = all_news.filter(status='pending').count()
    returned_count = all_news.filter(status='returned').count()

    paginator = Paginator(news_items, 4)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "office_dashboard/news-updates.html", {
        "rep": rep,
        "page_obj": page_obj,
        "news_items": page_obj.object_list,
        "current_q": q,
        "current_status": status,
        "current_sort": sort,
        "total_count": total_count,
        "published_count": published_count,
        "pending_count": pending_count,
        "returned_count": returned_count,
    })

@office_rep_required
def edit_news(request, rep, pk):
    news = get_object_or_404(NewsUpdate, pk=pk, representative=rep)

    if news.status == 'published':
        messages.error(request, "This news post is already published and can no longer be edited.")
        return redirect('office_dashboard:news_update')

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "News headline is required.")
        else:
            news.title = title
            news.category = request.POST.get('category', '')
            news.summary = request.POST.get('summary', '')
            news.content = request.POST.get('content', '')
            if request.FILES.get('image'):
                news.image = request.FILES.get('image')
            news.author = request.POST.get('author', '')
            news.date_published = request.POST.get('date_published') or None
            news.source = request.POST.get('source', '')
            news.tags = request.POST.get('tags', '')
            news.save()   # last_updated is stamped automatically here
            messages.success(request, f'"{title}" was updated.')
            log_activity(rep, "News updated", f'Updated "{title}"', "content", "fa-regular fa-pen-to-square", "#12b3c4")
        return redirect('office_dashboard:news_update')

    return redirect('office_dashboard:news_update')

@office_rep_required
def delete_news(request, rep, pk):
    news = get_object_or_404(NewsUpdate, pk=pk, representative=rep)

    if request.method == "POST":
        title = news.title
        news.delete()
        messages.success(request, f'"{title}" was deleted.')
        log_activity(rep, "News deleted", f'Deleted "{title}"', "content", "fa-regular fa-trash-can", "var(--red-600)")

    return redirect('office_dashboard:news_update')

@office_rep_required
def events(request, rep):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        title = request.POST.get('title', '').strip()
        if not title:
            if is_ajax:
                return JsonResponse({"success": False, "error": "Event title is required."}, status=400)
            messages.error(request, "Event title is required.")
        else:
            def parse_date(value):
                try:
                    return datetime.strptime(value, '%Y-%m-%d').date() if value else None
                except ValueError:
                    return None

            def parse_time(value):
                try:
                    return datetime.strptime(value, '%H:%M').time() if value else None
                except ValueError:
                    return None

            event_date = parse_date(request.POST.get('event_date'))
            start_time = parse_time(request.POST.get('start_time'))
            end_time = parse_time(request.POST.get('end_time'))

            event = Event.objects.create(
                representative=rep,
                title=title,
                category=request.POST.get('category', ''),
                description=request.POST.get('description', ''),
                event_date=event_date,
                start_time=start_time,
                end_time=end_time,
                location=request.POST.get('location', ''),
                organizer=request.POST.get('organizer', ''),
                contact_person=request.POST.get('contact_person', ''),
                contact_info=request.POST.get('contact_info', ''),
                poster=request.FILES.get('poster'),
            )
            log_activity(rep, "Event submitted", f'Submitted "{title}" for approval', "content", "fa-solid fa-calendar-days", "#7c4fe0")
            if is_ajax:
                return JsonResponse({
                    "success": True,
                    "title": event.title,
                    "event_date": django_date_format(event_date, "F j, Y") if event_date else "",
                    "event_mon": django_date_format(event_date, "M").upper() if event_date else "",
                    "event_day": django_date_format(event_date, "d") if event_date else "",
                    "start_time": django_date_format(start_time, "g:i A") if start_time else "",
                    "location": event.location,
                })
            messages.success(request, f'"{title}" was added and is pending approval.')
        return redirect('office_dashboard:event')

    events_qs = rep.events.all()

    q = request.GET.get('q', '').strip()
    if q:
        events_qs = events_qs.filter(title__icontains=q)

    status = request.GET.get('status', '')
    if status:
        events_qs = events_qs.filter(status=status)

    when = request.GET.get('when', 'all')
    today = timezone.localdate()
    if when == 'upcoming':
        events_qs = events_qs.filter(event_date__gte=today)
    elif when == 'past':
        events_qs = events_qs.filter(event_date__lt=today)
    # when == 'all' -> no date filter

    events_qs = events_qs.order_by('event_date', 'start_time')

    paginator = Paginator(events_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    upcoming_count = rep.events.filter(status="published", event_date__gte=today).count()
    completed_this_year_count = rep.events.filter(status="completed", event_date__year=today.year).count()
    pending_count = rep.events.filter(status="pending").count()

    return render(request, "office_dashboard/events.html", {
        "rep": rep,
        "page_obj": page_obj,
        "events": page_obj.object_list,
        "current_q": q,
        "current_status": status,
        "current_when": when,
        "upcoming_count": upcoming_count,
        "completed_this_year_count": completed_this_year_count,
        "pending_count": pending_count,
    })

@office_rep_required
def edit_event(request, rep, pk):
    event = get_object_or_404(Event, pk=pk, representative=rep)

    if event.status == 'published':
        messages.error(request, "This event is already published and can no longer be edited.")
        return redirect('office_dashboard:event')

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Event title is required.")
        else:
            event.title = title
            event.category = request.POST.get('category', '')
            event.description = request.POST.get('description', '')
            event.event_date = request.POST.get('event_date') or None
            event.start_time = request.POST.get('start_time') or None
            event.end_time = request.POST.get('end_time') or None
            event.location = request.POST.get('location', '')
            event.organizer = request.POST.get('organizer', '')
            event.contact_person = request.POST.get('contact_person', '')
            event.contact_info = request.POST.get('contact_info', '')
            if request.FILES.get('poster'):
                event.poster = request.FILES.get('poster')
            event.save()   # last_updated is stamped automatically here
            messages.success(request, f'"{title}" was updated.')
            log_activity(rep, "Event updated", f'Updated "{title}"', "content", "fa-regular fa-pen-to-square", "#7c4fe0")
        return redirect('office_dashboard:event')

    return redirect('office_dashboard:event')

@office_rep_required
def delete_event(request, rep, pk):
    event = get_object_or_404(Event, pk=pk, representative=rep)

    if request.method == "POST":
        title = event.title
        event.delete()
        messages.success(request, f'"{title}" was deleted.')
        log_activity(rep, "Event deleted", f'Deleted "{title}"', "content", "fa-regular fa-trash-can", "var(--red-600)")

    return redirect('office_dashboard:event')

@office_rep_required
def services(request, rep):
    all_services = rep.office.services.all()

    total_count = all_services.count()
    published_count = all_services.filter(status='published').count()
    pending_count = all_services.filter(status='pending').count()
    returned_count = all_services.filter(status='returned').count()

    services_qs = all_services

    q = request.GET.get('q', '').strip()
    if q:
        services_qs = services_qs.filter(name__icontains=q)

    status = request.GET.get('status', '')
    if status:
        services_qs = services_qs.filter(status=status)

    services_qs = list(services_qs)
    for service in services_qs:
        service.steps_json = json.dumps([
            {
                "step_number": str(step.order),
                "title": step.title,
                "agency_action": step.agency_action,
                "fee": step.fee,
                "processing_time": step.processing_time,
                "person_responsible": step.person_responsible,
            }
            for step in service.steps.all()
        ])
        service.requirements_json = json.dumps([
            {
                "title": r.title,
                "where_to_secure": r.where_to_secure,
                "transaction_type": r.transaction_type,
            }
            for r in service.requirements.all()
        ])

    return render(request, "office_dashboard/office-rep-service-details.html", {
        "rep": rep,
        "services": services_qs,
        "category_choices": Service.CATEGORY_CHOICES,
        "icon_choices": Service.ICON_CHOICES,
        "total_count": total_count,
        "published_count": published_count,
        "pending_count": pending_count,
        "returned_count": returned_count,
        "current_q": q,
        "current_status": status,
        "category_choices_forms": FORM_CATEGORY_CHOICES,
        "editing_globally_enabled": ServiceEditSettings.get_solo().editing_enabled,
    })

@office_rep_required
def delete_service_form(request, rep, service_pk, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office, service_id=service_pk)

    if request.method == "POST":
        title = form.title
        form.file.delete(save=False)
        form.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect(f"{reverse('office_dashboard:services')}?service={service_pk}")

@office_rep_required
def save_process_steps(request, rep, service_pk):
    service = get_object_or_404(Service, pk=service_pk, office=rep.office)

    if request.method == "POST":
        if service.status == 'published':
            return HttpResponse("This service is already published and can no longer be edited.", status=403)


    if request.method == "POST":
        step_numbers = request.POST.getlist('step_number[]')
        titles = request.POST.getlist('title[]')
        agency_actions = request.POST.getlist('agency[]')
        fees = request.POST.getlist('fee[]')
        processing_times = request.POST.getlist('processing_time[]')
        persons = request.POST.getlist('person[]')

        service.steps.all().delete()

        fallback_order = 1
        created_any = False
        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue
            step_number_raw = step_numbers[i].strip() if i < len(step_numbers) else ""
            try:
                order = Decimal(step_number_raw) if step_number_raw else Decimal(fallback_order)
            except InvalidOperation:
                order = Decimal(fallback_order)
            agency_action = agency_actions[i].strip() if i < len(agency_actions) else ""
            fee = fees[i].strip() if i < len(fees) else ""
            processing_time = processing_times[i].strip() if i < len(processing_times) else ""
            person = persons[i].strip() if i < len(persons) else ""

            ProcessStep.objects.create(
                service=service,
                order=order,
                title=title,
                agency_action=agency_action,
                fee=fee,
                processing_time=processing_time,
                person_responsible=person,
            )
            fallback_order += 1
            created_any = True

        if not created_any:
            messages.error(request, "Add at least one step with a name.")
        else:
            messages.success(request, "Client steps updated.")

    return redirect(f"{reverse('office_dashboard:services')}?service={service.pk}")

@office_rep_required
def save_reminders(request, rep, service_pk):
    service = get_object_or_404(Service, pk=service_pk, office=rep.office)

    if request.method == "POST":
        if service.status == 'published':
            return HttpResponse("This service is already published and can no longer be edited.", status=403)


    if request.method == "POST":
        items_raw = request.POST.get('items', '')
        lines = [line.strip() for line in items_raw.splitlines() if line.strip()]
        service.reminders = "\n".join(lines)
        service.save()

    return redirect('office_dashboard:services')

@office_rep_required
def save_requirements(request, rep, service_pk):
    service = get_object_or_404(Service, pk=service_pk, office=rep.office)

    if request.method == "POST":
        if service.status == 'published':
            return HttpResponse("This service is already published and can no longer be edited.", status=403)

    if request.method == "POST":
        titles = request.POST.getlist('title[]')
        wheres = request.POST.getlist('where[]')
        txns = request.POST.getlist('txn[]')

        service.requirements.all().delete()

        order = 1
        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue
            where = wheres[i].strip() if i < len(wheres) else ""
            transaction_type = txns[i].strip() if i < len(txns) else ""
            Requirement.objects.create(
                service=service,
                order=order,
                title=title,
                where_to_secure=where,
                transaction_type=transaction_type,
            )
            order += 1

        if order == 1:
            messages.error(request, "Add at least one requirement with a name.")
        else:
            messages.success(request, "Requirements updated.")

    return redirect(f"{reverse('office_dashboard:services')}?service={service.pk}")

@office_rep_required
def save_legal_basis(request, rep, service_pk):
    service = get_object_or_404(Service, pk=service_pk, office=rep.office)

    if request.method == "POST":
        if service.status == 'published':
            return HttpResponse("This service is already published and can no longer be edited.", status=403)


    if request.method == "POST":
        service.legal_basis = request.POST.get('legal_basis', '').strip()
        service.save()

    return redirect('office_dashboard:services')

@office_rep_required
def save_schedule_of_service(request, rep, service_pk):
    service = get_object_or_404(Service, pk=service_pk, office=rep.office)

    if request.method == "POST":
        if service.status == 'published':
            return HttpResponse("This service is already published and can no longer be edited.", status=403)


    if request.method == "POST":
        service.schedule_of_service = request.POST.get('schedule_of_service', '').strip()
        service.save()

    return redirect('office_dashboard:services')

FORM_CATEGORY_CHOICES = ["Permits", "Clearance", "Health", "Assistance"]

@office_rep_required
def downloadable_forms(request, rep):
    return render(request, "office_dashboard/downloadable-forms.html", {
        "rep": rep,
        "forms": rep.office.downloadable_forms.all(),
        "category_choices": FORM_CATEGORY_CHOICES,
    })

@office_rep_required
def upload_form(request, rep):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', '').strip()
        uploaded_file = request.FILES.get('file')
        service_id = request.POST.get('service')

        error = None
        if not title:
            error = "Form name is required."
        elif not uploaded_file:
            error = "Please attach a PDF file."
        elif not uploaded_file.name.lower().endswith('.pdf'):
            error = "Only PDF files are allowed."

        if error:
            if is_ajax:
                return JsonResponse({"success": False, "error": error}, status=400)
            messages.error(request, error)
        else:
            service = Service.objects.filter(pk=service_id, office=rep.office).first() if service_id else None
            DownloadableForm.objects.create(
                office=rep.office,
                service=service,
                title=title,
                description=description,
                category=category,
                file=uploaded_file,
                uploaded_by=rep.office.name,
                download_count=0,
            )
            if is_ajax:
                return JsonResponse({"success": True, "title": title})
            messages.success(request, f'"{title}" was uploaded.')
            if service_id:
                return redirect(f"{reverse('office_dashboard:services')}?service={service_id}&tab=forms")

    return redirect('office_dashboard:downloadable_form')

@office_rep_required
def delete_form(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)

    if request.method == "POST":
        if form.service:
            messages.error(request, f'"{form.title}" was uploaded from {form.service.name} and can only be deleted from that service\'s page.')
            return redirect('office_dashboard:downloadable_form')

        title = form.title
        form.file.delete(save=False)
        form.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect('office_dashboard:downloadable_form')

@office_rep_required
def download_form(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)

    DownloadableForm.objects.filter(pk=pk).update(download_count=F('download_count') + 1)

    try:
        filename = form.file.name.rsplit('/', 1)[-1]
        return FileResponse(form.file.open('rb'), as_attachment=True, filename=filename)
    except FileNotFoundError:
        raise Http404("File not found.")


@office_rep_required
def form_fields_builder(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)
    fields = list(form.fields.all().values(
        'id', 'label', 'field_type', 'required', 'page_number', 'x', 'y', 'width', 'height', 'order'
    ))
    return render(request, "office_dashboard/form-fields-builder.html", {
        "rep": rep,
        "form_obj": form,
        "fields_json": json.dumps(fields),
    })


@office_rep_required
def save_form_fields(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

    try:
        payload = json.loads(request.body)
        incoming_fields = payload.get('fields', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "error": "Invalid data."}, status=400)

    # Simplest correct approach: replace the whole field set each save,
    # rather than trying to diff individual adds/edits/deletes.
    form.fields.all().delete()

    for i, f in enumerate(incoming_fields):
        label = (f.get('label') or '').strip()
        if not label:
            continue
        FormField.objects.create(
            form=form,
            label=label,
            field_type=f.get('field_type', 'text'),
            required=bool(f.get('required', True)),
            page_number=int(f.get('page_number', 1)),
            x=float(f.get('x', 0)),
            y=float(f.get('y', 0)),
            width=float(f.get('width', 0.2)),
            height=float(f.get('height', 0.03)),
            order=i,
        )

    messages.success(request, f'"{form.title}" is now fillable — fields were saved.' if incoming_fields else f'All fields were removed from "{form.title}".')
    return JsonResponse({"success": True})

@office_rep_required
def edit_form(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)

    if form.service:
        messages.error(request, f'"{form.title}" was uploaded from {form.service.name} and can only be managed from that service\'s page.')
        return redirect('office_dashboard:downloadable_form')

    if form.status == 'published':
        messages.error(request, "This form is already published and can no longer be edited.")
        return redirect('office_dashboard:downloadable_form')

    if request.method == "POST":
        title = request.POST.get('title', '').strip()

        if not title:
            messages.error(request, "Form name is required.")
        else:
            new_file = request.FILES.get('file')
            if new_file and not new_file.name.lower().endswith('.pdf'):
                messages.error(request, "Only PDF files are allowed.")
                return redirect('office_dashboard:downloadable_form')

            form.title = title
            form.description = request.POST.get('description', '')
            form.category = request.POST.get('category', '')
            if new_file:
                form.file.delete(save=False)  # remove the old file before attaching the new one
                form.file = new_file
            form.save()
            messages.success(request, f'"{title}" was updated.')
            log_activity(rep, "Form updated", f'Updated "{title}"', "content", "fa-regular fa-pen-to-square", "var(--blue-600)")

    return redirect('office_dashboard:downloadable_form')

@office_rep_required
def gallery(request, rep):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        title = request.POST.get('title', '').strip()
        image = request.FILES.get('image')
        album_id = request.POST.get('album') or None
        new_album_name = request.POST.get('new_album_name', '').strip()

        error = None
        if not title:
            error = "Caption / title is required."
        elif not image:
            error = "Please choose a photo to upload."

        if error:
            if is_ajax:
                return JsonResponse({"success": False, "error": error}, status=400)
            messages.error(request, error)
        else:
            if album_id == '__new__' and new_album_name:
                album, _ = Album.objects.get_or_create(representative=rep, name=new_album_name)
            elif album_id and album_id != '__new__':
                album = Album.objects.filter(pk=album_id, representative=rep).first()
            else:
                album = None

            Photo.objects.create(
                representative=rep,
                title=title,
                image=image,
                album=album,
                # status not set -> defaults to "pending"
            )

            log_activity(rep, "Photo uploaded", f'Uploaded "{title}" for approval', "content", "fa-regular fa-image", "#12b3c4")
            if is_ajax:
                return JsonResponse({"success": True, "title": title})
            messages.success(request, f'"{title}" was uploaded and is pending approval.')
        return redirect('office_dashboard:gallery')

    album_param = request.GET.get('album', '').strip()
    q = request.GET.get('q', '').strip()

    total_photo_count = Photo.objects.filter(representative=rep).count()
    total_album_count = Album.objects.filter(representative=rep).count()
    pending_count = Photo.objects.filter(representative=rep, status='pending').count()
    uncategorized_count = Photo.objects.filter(representative=rep, album__isnull=True).count()

    all_albums_for_upload = Album.objects.filter(representative=rep).order_by('name')

    announcements_image_count = Announcement.objects.filter(representative=rep).exclude(image='').count()
    news_image_count = NewsUpdate.objects.filter(representative=rep).exclude(image='').count()
    events_image_count = Event.objects.filter(representative=rep).exclude(poster='').count()

    announcements_cover = Announcement.objects.filter(representative=rep).exclude(image='').order_by('created_at').first()
    news_cover = NewsUpdate.objects.filter(representative=rep).exclude(image='').order_by('created_at').first()
    events_cover = Event.objects.filter(representative=rep).exclude(poster='').order_by('created_at').first()

    VIRTUAL_ALBUMS = {
        'announcements': 'Announcements',
        'news': 'News & Updates',
        'events': 'Events',
    }

    in_album_view = bool(album_param)
    selected_album = None
    selected_album_name = ''
    viewing_virtual_album = album_param in VIRTUAL_ALBUMS

    if in_album_view:
        if album_param == 'none':
            selected_album_name = 'Uncategorized'
            photos = Photo.objects.filter(representative=rep, album__isnull=True)
        elif album_param in VIRTUAL_ALBUMS:
            selected_album_name = VIRTUAL_ALBUMS[album_param]
            if album_param == 'announcements':
                photos = list(Announcement.objects.filter(representative=rep).exclude(image='').order_by('-created_at'))
            elif album_param == 'news':
                photos = list(NewsUpdate.objects.filter(representative=rep).exclude(image='').order_by('-created_at'))
            else:
                photos = list(Event.objects.filter(representative=rep).exclude(poster='').order_by('-created_at'))
                for item in photos:
                    item.image = item.poster  # normalize so the template can use {{ p.image.url }} uniformly
            if q:
                photos = [p for p in photos if q.lower() in p.title.lower()]
        else:
            selected_album = get_object_or_404(Album, pk=album_param, representative=rep)
            selected_album_name = selected_album.name
            photos = Photo.objects.filter(representative=rep, album=selected_album)

        if q and not viewing_virtual_album:
            photos = photos.filter(title__icontains=q)
        if not viewing_virtual_album:
            photos = photos.order_by('-created_at')

        paginator = Paginator(photos, 12)
        page_obj = paginator.get_page(request.GET.get('page'))
    else:
        albums = Album.objects.filter(representative=rep).annotate(photo_count=Count('photos'))
        if q:
            albums = albums.filter(name__icontains=q)
        albums = albums.order_by('name')

        paginator = Paginator(albums, 12)
        page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "office_dashboard/gallery.html", {
        "rep": rep,
        "page_obj": page_obj,
        "in_album_view": in_album_view,
        "album_param": album_param,
        "selected_album": selected_album,
        "selected_album_name": selected_album_name,
        "viewing_virtual_album": viewing_virtual_album,
        "current_q": q,
        "total_photo_count": total_photo_count,
        "total_album_count": total_album_count,
        "pending_count": pending_count,
        "uncategorized_count": uncategorized_count,
        "all_albums_for_upload": all_albums_for_upload,
        "announcements_image_count": announcements_image_count,
        "news_image_count": news_image_count,
        "events_image_count": events_image_count,
        "announcements_cover": announcements_cover,
        "news_cover": news_cover,
        "events_cover": events_cover,
    })

@office_rep_required
def create_album(request, rep):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, "Album name is required.")
        else:
            Album.objects.create(representative=rep, name=name, description=description)
            messages.success(request, f'Album "{name}" was created.')

    return redirect('office_dashboard:gallery')

@office_rep_required
def delete_photo(request, rep, pk):
    photo = get_object_or_404(Photo, pk=pk, representative=rep)

    if request.method == "POST":
        title = photo.title
        photo.delete()
        messages.success(request, f'"{title}" was deleted.')
        log_activity(rep, "Photo deleted", f'Deleted "{title}"', "content", "fa-regular fa-trash-can", "var(--red-600)")

    return redirect('office_dashboard:gallery')

@office_rep_required
def rename_album(request, rep, pk):
    album = get_object_or_404(Album, pk=pk, representative=rep)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Album name is required.")
        else:
            album.name = name
            album.save()
            messages.success(request, f'Album renamed to "{name}".')

    return redirect('office_dashboard:gallery')

@office_rep_required
def delete_album(request, rep, pk):
    album = get_object_or_404(Album, pk=pk, representative=rep)

    if request.method == "POST":
        name = album.name
        photo_count = album.photos.count()
        album.photos.all().delete()  # deleting the album now also deletes its photos
        album.delete()
        messages.success(
            request,
            f'Album "{name}" and its {photo_count} photo{"s" if photo_count != 1 else ""} were deleted.'
        )

    return redirect('office_dashboard:gallery')

# These are the only six fields this view is allowed to touch — the URL's
# <str:field> segment is checked against this dict before anything is
# written, so a representative can never edit an arbitrary Office column
# through this endpoint. Each one gets its own small modal/textarea on the
# Office Profile page rather than sharing the big Office Information form.
OFFICE_CHARTER_FIELDS = {
    "service-pledge": ("service_pledge", "Service Pledge"),
    "mandate": ("mandate", "Mandate"),
    "vision": ("vision", "Vision"),
    "mission": ("mission", "Mission"),
    "goal": ("goal", "Goal"),
    "objective": ("objective", "Objective"),
}


@office_rep_required
def edit_office_charter_field(request, rep, field):
    meta = OFFICE_CHARTER_FIELDS.get(field)
    if not meta:
        raise Http404("Unknown office profile field.")
    attr, label = meta
    office = rep.office

    if request.method == "POST":
        setattr(office, attr, request.POST.get('value', '').strip())
        office.save(update_fields=[attr])
        messages.success(request, f"{label} updated.")
        log_activity(
            rep,
            f"{label} updated",
            f"Updated the office's {label.lower()}",
            "account",
            "fa-solid fa-building",
            "var(--blue-600)",
        )

    return redirect('office_dashboard:profile')

@office_rep_required
def office_profile(request, rep):
    office = rep.office

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Office name is required.")
        else:
            office.name = name
            office.about = request.POST.get('about', '')
            office.description = request.POST.get('description', '')
            office.head_name = request.POST.get('head_name', '')
            office.position_title = request.POST.get('position_title', '')
            office.office_hours = request.POST.get('office_hours', '')
            office.location = request.POST.get('location', '')
            office.email = request.POST.get('email', '')
            office.telephone = request.POST.get('telephone', '')
            if request.FILES.get('logo'):
                office.logo = request.FILES.get('logo')
            office.save()
            messages.success(request, "Office profile updated.")
            log_activity(rep, "Office profile updated", "Updated office information", "account", "fa-solid fa-building", "var(--blue-600)")
        return redirect('office_dashboard:profile')

    return render(request, "office_dashboard/office-profile.html", {
        "rep": rep,
        "office": office,
        "services": office.services.all(),
        "category_choices": Service.CATEGORY_CHOICES,
        "icon_choices": Service.ICON_CHOICES,
    })

@office_rep_required
def add_service(request, rep):
    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon') or 'fa-solid fa-file-signature'

        division = request.POST.get('division', '').strip() or rep.office.name
        classification = request.POST.get('classification', '').strip()
        transaction_types = request.POST.getlist('transaction_type')
        transaction_type = ",".join(transaction_types)
        who_may_avail = request.POST.get('who_may_avail', '').strip()
        service_scope = request.POST.get('service_scope', '').strip()
        if service_scope not in ('internal', 'external'):
            service_scope = ''

        if not name:
            messages.error(request, "Service name is required.")
        else:
            Service.objects.create(
                office=rep.office,
                name=name,
                description=description,
                icon=icon,
                division=division,
                classification=classification,
                transaction_type=transaction_type,
                who_may_avail=who_may_avail,
                service_scope=service_scope,
            )
            messages.success(request, f'"{name}" was added to your services.')

    next_page = request.POST.get('next') or request.GET.get('next')
    if next_page == 'services':
        return redirect('office_dashboard:services')
    return redirect('office_dashboard:profile')

@office_rep_required
def delete_service(request, rep, pk):
    service = get_object_or_404(Service, pk=pk, office=rep.office)

    if request.method == "POST":
        name = service.name
        service.delete()
        messages.success(request, f'"{name}" was deleted.')

    return redirect('office_dashboard:services')

@office_rep_required
def edit_service(request, rep, pk):
    service = get_object_or_404(Service, pk=pk, office=rep.office)

    if request.method == "POST":
        if not ServiceEditSettings.get_solo().editing_enabled:
            messages.error(request, "The Super Admin has turned off editing of services for all offices.")
            return redirect(f"{reverse('office_dashboard:services')}?service={service.pk}")

        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon') or service.icon

        division = request.POST.get('division', '').strip() or rep.office.name
        classification = request.POST.get('classification', '').strip()
        transaction_types = request.POST.getlist('transaction_type')
        transaction_type = ",".join(transaction_types)
        who_may_avail = request.POST.get('who_may_avail', '').strip()
        service_scope = request.POST.get('service_scope', '').strip()
        if service_scope not in ('internal', 'external'):
            service_scope = ''

        if not name:
            messages.error(request, "Service name is required.")
        else:
            service.name = name
            service.description = description
            service.icon = icon
            service.division = division
            service.classification = classification
            service.transaction_type = transaction_type
            service.who_may_avail = who_may_avail
            service.service_scope = service_scope
            service.save()
            messages.success(request, f'"{name}" was updated.')

    return redirect(f"{reverse('office_dashboard:services')}?service={service.pk}")

@office_rep_required
def office_directory(request, rep):
    return render(request, "office_dashboard/office-directory.html", {"rep": rep})

@office_rep_required
def office_location(request, rep):
    return render(request, "office_dashboard/office-location.html", {"rep": rep})

@office_rep_required
def office_page_settings(request, rep):
    """Lets the office representative replace the banner image shown at the
    top of their office's public page (offices/office_detail.html's
    .page-hero section), toggle public visibility, and reorder how their
    services are listed on that same page."""
    office = rep.office
 
    if request.method == "POST":
        if request.POST.get('action') == 'reset':
            if office.hero_image:
                office.hero_image.delete(save=False)
            office.hero_image = None
            office.save(update_fields=['hero_image'])
            messages.success(request, "Page hero image reset to the default.")
        elif request.FILES.get('hero_image'):
            if office.hero_image:
                office.hero_image.delete(save=False)
            office.hero_image = request.FILES['hero_image']
            office.save(update_fields=['hero_image'])
            messages.success(request, "Page hero image updated.")
            log_activity(
                rep,
                "Page hero image updated",
                "Changed the banner image on the office's public page",
                "account",
                "fa-solid fa-image",
                "var(--blue-600)",
            )
        else:
            messages.error(request, "Please choose an image to upload.")
        return redirect('office_dashboard:page_settings')
 
    services = list(
        Service.objects.filter(office=office).order_by('order', 'name', 'id')
    )
 
    return render(request, "office_dashboard/office-settings.html", {
        "rep": rep,
        "office": office,
        "services": services,
    })
 
 
# 3) ADD this new view right below it — the AJAX endpoint the "Save Order"
#    button in the Service Order panel calls. It only ever touches
#    services that belong to the requesting rep's own office (the
#    len(services) != len(service_ids) check below rejects any service id
#    that isn't theirs, the same whitelist pattern used elsewhere in this
#    file for OFFICE_CHARTER_FIELDS):
 
@office_rep_required
def office_reorder_services(request, rep):
    """AJAX endpoint used by the Page Settings -> Service Order panel.
    Expects a JSON body: {"order": [3, 7, 1, ...]} — a list of Service
    primary keys in the order they should appear on the office's public
    page. Saves each service's new `order` value."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
 
    try:
        payload = json.loads(request.body.decode("utf-8"))
        service_ids = [int(pk) for pk in payload.get("order", [])]
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid payload"}, status=400)
 
    services = {
        s.pk: s for s in Service.objects.filter(office=rep.office, pk__in=service_ids)
    }
 
    if len(services) != len(service_ids):
        return JsonResponse(
            {"ok": False, "error": "One or more services do not belong to your office"},
            status=403,
        )
 
    for position, pk in enumerate(service_ids):
        service = services[pk]
        if service.order != position:
            service.order = position
            service.save(update_fields=["order"])
 
    log_activity(
        rep,
        "Service order updated",
        "Rearranged the order services appear in on the office's public page",
        "account",
        "fa-solid fa-arrow-down-short-wide",
        "var(--blue-600)",
    )
    return JsonResponse({"ok": True})

@office_rep_required
def office_toggle_visibility(request, rep):
    """Lets the office representative show/hide their own office page on
    the public website (Page Settings → Visibility panel)."""
    office = rep.office
    if request.method == "POST":
        office.is_visible = not office.is_visible
        office.save(update_fields=['is_visible'])
        if office.is_visible:
            messages.success(request, "Your office page is now visible to residents on the public website.")
        else:
            messages.success(request, "Your office page is now hidden from the public website.")
        log_activity(
            rep,
            "Office visibility changed",
            f"Office page {'shown on' if office.is_visible else 'hidden from'} the public website",
            "account",
            "fa-regular fa-eye",
            "var(--blue-600)",
        )
    return redirect('office_dashboard:page_settings')

@office_rep_required
def my_account(request, rep):
    if request.method == "POST":
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()

        if not full_name:
            messages.error(request, "Full name is required.")
        else:
            name_parts = full_name.split(' ', 1)
            rep.user.first_name = name_parts[0]
            rep.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            rep.user.email = email
            rep.user.save()

            rep.position = request.POST.get('position', '')
            rep.mobile_number = request.POST.get('mobile_number', '')
            if request.FILES.get('photo'):
                rep.photo = request.FILES.get('photo')
            rep.save()

            messages.success(request, "Account details updated.")
            log_activity(rep, "Account details updated", "Updated personal account information", "account", "fa-solid fa-user", "var(--gray-500)")
        return redirect('office_dashboard:account')

    return render(request, "office_dashboard/my-account.html", {"rep": rep})

@office_rep_required
def change_pass(request, rep):
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
                log_activity(rep, "Password changed", "Account password was changed", "security", "fa-solid fa-lock", "var(--amber-600)")

        return redirect('office_dashboard:change_pass')

    return render(request, "office_dashboard/change-password.html", {"rep": rep})

@office_rep_required
def notification(request, rep):
    notifications = rep.notifications.all()
    unread_count = notifications.filter(is_read=False).count()

    return render(request, "office_dashboard/notification.html", {
        "rep": rep,
        "notifications": notifications,
        "unread_count": unread_count,
    })


@office_rep_required
def mark_notification_read(request, rep, pk):
    notif = get_object_or_404(Notification, pk=pk, representative=rep)
    if not notif.is_read:
        notif.is_read = True
        notif.save()
    if notif.link_url:
        return redirect(notif.link_url)
    return redirect('office_dashboard:notification')

@office_rep_required
def delete_notification(request, rep, pk):
    notif = get_object_or_404(Notification, pk=pk, representative=rep)
    if request.method == "POST":
        notif.delete()
        messages.success(request, "Notification deleted.")
    return redirect('office_dashboard:notification')

@office_rep_required
def mark_all_notifications_read(request, rep):
    if request.method == "POST":
        rep.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect('office_dashboard:notification')



@office_rep_required
def activity_log(request, rep):
    logs = rep.activity_logs.all()

    q = request.GET.get('q', '').strip()
    if q:
        logs = logs.filter(title__icontains=q)

    category = request.GET.get('category', '')
    if category:
        logs = logs.filter(category=category)

    range_ = request.GET.get('range', '7')
    if range_ != 'all':
        since = timezone.now() - timedelta(days=int(range_))
        logs = logs.filter(created_at__gte=since)

    paginator = Paginator(logs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    grouped = []
    for log_date, items in groupby(page_obj.object_list, key=lambda l: timezone.localtime(l.created_at).date()):
        items = list(items)
        if log_date == today:
            label = f"Today · {log_date.strftime('%B %d, %Y')}"
        elif log_date == yesterday:
            label = f"Yesterday · {log_date.strftime('%B %d, %Y')}"
        else:
            label = log_date.strftime('%B %d, %Y')
        grouped.append({"label": label, "items": items})

    return render(request, "office_dashboard/activity-logs.html", {
        "rep": rep,
        "page_obj": page_obj,
        "grouped_logs": grouped,
        "current_q": q,
        "current_category": category,
        "current_range": range_,
    })