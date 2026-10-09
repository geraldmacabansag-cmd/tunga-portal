from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo, Album, Service, ProcessStep, Requirement, DownloadableForm, Notification, FormField, ServiceEditSettings, Message

import json
import io
import re
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
from offices.pdf_serve import pdf_response
from .form_fields import fields_json, save_fields
from .notifications import maybe_send_weekly_summary, PREFERENCES as NOTIFY_PREFERENCES
from .announcement_rules import clean_announcement
from .org_chart import build_tree as build_org_tree, descendant_ids as org_descendant_ids, parent_choices as org_parent_choices, next_order as next_org_order
from .org_chart import clean_width as clean_org_width
from .content_photos import save_content_photos
from .org_chart import clean_style as clean_org_style, style_for as org_style_for, DEFAULT_COLORS as ORG_DEFAULT_COLORS, DEFAULT_LINE as ORG_DEFAULT_LINE, STYLE_DEFAULTS as ORG_STYLE_DEFAULTS
from .models import OrgChartNode, OrgChartSettings
from django import forms as dj_forms
from portal.models import EmailOTP
from portal.otp_utils import send_password_reset_otp
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
        if request.method == "GET":
            maybe_send_weekly_summary(rep)  # only if "Weekly summary" is switched on
        return view_func(request, rep, *args, **kwargs)
    return wrapper

@office_rep_required
def rep_announcement(request, rep):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        # Title, category and content are required (office_dashboard/announcement_rules.py).
        errors, data = clean_announcement(request.POST, is_new=True)
        title = data["title"]
        if errors:
            if is_ajax:
                return JsonResponse({"success": False, "error": " ".join(errors), "errors": errors}, status=400)
            for err in errors:
                messages.error(request, err)
        else:
            announcement = Announcement.objects.create(
                representative=rep,
                image=request.FILES.get('image'),
                # date_posted is intentionally left unset here — it's only
                # ever set automatically once the Super Admin approves and
                # publishes this announcement.
                **data,
            )
            for problem in save_content_photos(request, announcement):   # "More photos"
                messages.warning(request, problem)
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
        errors, data = clean_announcement(request.POST, is_new=False, current_expiration=announcement.expiration_date)
        title = data["title"]
        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            for field, value in data.items():
                setattr(announcement, field, value)
            if request.FILES.get('image'):
                announcement.image = request.FILES.get('image')
            # date_posted is intentionally left untouched here — see the note
            # in rep_announcement() above.
            announcement.save()   # last_updated is stamped automatically here
            for problem in save_content_photos(request, announcement):   # "More photos": add / remove
                messages.warning(request, problem)
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
        "services": available_services_for_forms(rep),
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
                # date_published is intentionally left unset here — it's only
                # ever set automatically once the Super Admin approves and
                # publishes this post.
                source=request.POST.get('source', ''),
                tags=request.POST.get('tags', ''),
            )
            for problem in save_content_photos(request, news):   # "More photos"
                messages.warning(request, problem)
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
            # date_published is intentionally left untouched here — see the
            # note in news_update() above.
            news.source = request.POST.get('source', '')
            news.tags = request.POST.get('tags', '')
            news.save()   # last_updated is stamped automatically here
            for problem in save_content_photos(request, news):   # "More photos": add / remove
                messages.warning(request, problem)
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
            for problem in save_content_photos(request, event):   # "More photos"
                messages.warning(request, problem)
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
            for problem in save_content_photos(request, event):   # "More photos": add / remove
                messages.warning(request, problem)
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

def available_services_for_forms(rep):
    """Services of this office a downloadable form can be linked to: every
    service except archived ones, in the same order as the Services page."""
    return list(
        Service.objects.filter(office=rep.office)
        .exclude(status="archive")
        .order_by("order", "name")
    )


@office_rep_required
def downloadable_forms(request, rep):
    return render(request, "office_dashboard/downloadable-forms.html", {
        "rep": rep,
        "forms": rep.office.downloadable_forms.select_related("service").all(),
        "category_choices": FORM_CATEGORY_CHOICES,
        "services": available_services_for_forms(rep),
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

        # Every form must belong to one of this office's (non-archived) services.
        service = None
        if service_id and str(service_id).isdigit():
            service = Service.objects.filter(pk=service_id, office=rep.office).exclude(status="archive").first()

        error = None
        if not title:
            error = "Form name is required."
        elif not uploaded_file:
            error = "Please attach a PDF file."
        elif not uploaded_file.name.lower().endswith('.pdf'):
            error = "Only PDF files are allowed."
        elif service is None:
            error = "Please choose the service this form belongs to."

        if error:
            if is_ajax:
                return JsonResponse({"success": False, "error": error}, status=400)
            messages.error(request, error)
        else:
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
            messages.success(request, f'"{title}" was uploaded and linked to {service.name}.')
            # From a service's own page the form belongs on that service's Forms tab.
            if request.POST.get('return_to') == 'service':
                return redirect(f"{reverse('office_dashboard:services')}?service={service.pk}&tab=forms")

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
def preview_form_pdf(request, rep, pk):
    """PDF for the office rep's field builder preview."""
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)
    return pdf_response(request, form.file, filename="form.pdf")


@office_rep_required
def form_fields_builder(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)
    return render(request, "office_dashboard/form-fields-builder.html", {
        "rep": rep,
        "form_obj": form,
        "fields_json": fields_json(form),
    })


@office_rep_required
def save_form_fields(request, rep, pk):
    form = get_object_or_404(DownloadableForm, pk=pk, office=rep.office)
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)
    try:
        incoming = json.loads(request.body).get("fields", [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "error": "Invalid data."}, status=400)

    count = save_fields(form, incoming)
    messages.success(request, f'"{form.title}" is now fillable — fields were saved.' if count else f'All fields were removed from "{form.title}".')
    return JsonResponse({"success": True, "fields": json.loads(fields_json(form))})

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

            service_id = request.POST.get('service')
            service = None
            if service_id and str(service_id).isdigit():
                service = Service.objects.filter(pk=service_id, office=rep.office).exclude(status="archive").first()
            if service is None:
                messages.error(request, "Please choose the service this form belongs to.")
                return redirect('office_dashboard:downloadable_form')

            form.title = title
            form.service = service
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
        category = request.POST.get('category', '').strip()
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
                category=category,
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
        "photo_category_choices": Photo.CATEGORY_CHOICES,
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
        if request.POST.get('form_name') == 'social_media':
            for field in SOCIAL_LINK_FIELDS:
                setattr(office, field, request.POST.get(field, '').strip())
            office.save(update_fields=SOCIAL_LINK_FIELDS)
            messages.success(request, "Social media links updated.")
            log_activity(
                rep,
                "Social media links updated",
                "Updated the office's social media links shown on its public page",
                "account",
                "fa-solid fa-share-nodes",
                "var(--blue-600)",
            )
            return redirect('office_dashboard:profile')

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
            elif request.POST.get('reset_logo') == '1' and office.logo:
                # Back to the office's default icon: drop the uploaded logo.
                try:
                    office.logo.delete(save=False)
                except Exception:
                    pass
                office.logo = None
            office.save()
            messages.success(request, "Office profile updated.")
            log_activity(rep, "Office profile updated", "Updated office information", "account", "fa-solid fa-building", "var(--blue-600)")
        return redirect('office_dashboard:profile')

    # The office's built-in icon (same one used on the public Offices page),
    # shown whenever no logo has been uploaded.
    from portal.views import get_office_card_style
    default_icon_class, _color, default_icon_image = get_office_card_style(office)

    return render(request, "office_dashboard/office-profile.html", {
        "rep": rep,
        "office": office,
        "default_icon_class": default_icon_class,
        "default_icon_image": default_icon_image,
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
            service = Service.objects.create(
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
            messages.success(request, f'"{name}" was added. Add its requirements, process steps, fees and other details below.')

            next_page = request.POST.get('next') or request.GET.get('next')
            if next_page == 'services':
                # Straight into that service's own detail view instead of
                # the bare list — the Services page reads this "service"
                # query param on load and opens the matching detail panel.
                return redirect(f"{reverse('office_dashboard:services')}?service={service.pk}")
            return redirect('office_dashboard:profile')

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
def office_location(request, rep):
    return render(request, "office_dashboard/office-location.html", {"rep": rep})

SOCIAL_LINK_FIELDS = ["facebook_url", "twitter_url", "instagram_url", "youtube_url"]
 
 
@office_rep_required
def office_page_settings(request, rep):
    """Lets the office representative manage everything shown on their
    office's public page from one place: the banner image, visibility,
    and (via the separate office_reorder_services
    endpoint) the order their services are listed in."""
    office = rep.office
 
    if request.method == "POST":
        form_name = request.POST.get('form_name')
 
        if form_name == 'hero_image':
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

        if not full_name:
            messages.error(request, "Full name is required.")
        else:
            name_parts = full_name.split(' ', 1)
            rep.user.first_name = name_parts[0]
            rep.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
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
def save_notification_prefs(request, rep):
    """Saves one switch from My Account -> Notification Preferences.
    POST: pref=<approvals|messages|weekly_summary|announcements>, enabled=<1|0>"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)
    field = NOTIFY_PREFERENCES.get(request.POST.get("pref", ""))
    if field is None:
        return JsonResponse({"success": False, "error": "Unknown preference."}, status=400)
    enabled = request.POST.get("enabled") == "1"
    setattr(rep, field, enabled)
    update = [field]
    if field == "notify_weekly_summary":
        # Start counting the week from now (first summary arrives in 7 days).
        rep.last_weekly_summary_at = timezone.now() if enabled else None
        update.append("last_weekly_summary_at")
    rep.save(update_fields=update)
    return JsonResponse({"success": True, "pref": request.POST.get("pref"), "enabled": enabled})

# Same rules as the "Password Requirements" list on the Change Password page
# (checked live in the browser, and here again on the server).
PASSWORD_RULES = [
    (lambda p: len(p) >= 8, "Password must be at least 8 characters."),
    (lambda p: re.search(r"[A-Z]", p), "Password must contain at least one uppercase letter."),
    (lambda p: re.search(r"[0-9]", p), "Password must contain at least one number."),
    (lambda p: re.search(r"[^A-Za-z0-9]", p), "Password must contain at least one special character (e.g. ! @ # $ %)."),
]


def password_problems(password, user):
    """All the reasons a new password can't be used (empty list = OK)."""
    problems = [msg for rule, msg in PASSWORD_RULES if not rule(password)]
    try:
        validate_password(password, user=user)   # Django's own checks (too common, too similar to your name…)
    except ValidationError as e:
        problems += [m for m in e.messages if m not in problems]
    return problems


def mask_email(email):
    """juan.delacruz@gmail.com -> ju********@gmail.com"""
    if not email or "@" not in email:
        return ""
    name, domain = email.split("@", 1)
    return name[:2] + "*" * max(len(name) - 2, 3) + "@" + domain


@office_rep_required
def change_pass(request, rep):
    """Change password with the current password, or — "Forgot your current
    password?" — with a 6-digit code sent to the account's email."""
    if request.method == "POST":
        mode = request.POST.get('mode', 'current')
        current_password = request.POST.get('current_password', '')
        otp_code = request.POST.get('otp_code', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        email = request.user.email

        if mode == 'otp' and not email:
            messages.error(request, "Your account has no email address. Ask the Super Admin to add one, then try again.")
        elif mode != 'otp' and not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirmation do not match.")
        elif mode != 'otp' and new_password == current_password:
            messages.error(request, "Your new password must be different from your current password.")
        elif password_problems(new_password, request.user):
            for err in password_problems(new_password, request.user):
                messages.error(request, err)
        # The code is checked last, so a typo in the new password doesn't use it up.
        elif mode == 'otp' and not EmailOTP.verify(email, otp_code):
            messages.error(request, "That verification code is incorrect or has expired. Please request a new one.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # keeps them logged in here, signs out other devices
            messages.success(request, "Password updated successfully.")
            how = "using an email verification code" if mode == 'otp' else "using the current password"
            log_activity(rep, "Password changed", f"Account password was changed {how}", "security", "fa-solid fa-lock", "var(--amber-600)")

        return redirect('office_dashboard:change_pass')

    return render(request, "office_dashboard/change-password.html", {
        "rep": rep,
        "masked_email": mask_email(request.user.email),
    })


@office_rep_required
def send_password_otp(request, rep):
    """Emails a 6-digit code to the logged-in representative (Forgot password)."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)
    email = request.user.email
    if not email:
        return JsonResponse({"success": False, "error": "Your account has no email address. Ask the Super Admin to add one."}, status=400)

    # One code per minute, so the button can't be used to flood the inbox.
    recent = EmailOTP.objects.filter(email=email, created_at__gte=timezone.now() - timedelta(seconds=60)).order_by('-created_at').first()
    if recent:
        wait = 60 - int((timezone.now() - recent.created_at).total_seconds())
        return JsonResponse({"success": False, "error": f"Please wait {max(wait, 1)} seconds before requesting a new code.", "wait": max(wait, 1)}, status=429)

    ok, error = send_password_reset_otp(email)
    if not ok:
        return JsonResponse({"success": False, "error": error or "Could not send the code. Please try again."}, status=500)
    return JsonResponse({"success": True, "email": mask_email(email)})

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


# ---------------------------------------------------------------------------
# Messages: chat between this office representative and the Super Admin.
# The page is a plain skeleton; static/js/messages.js loads and polls the
# conversation through rep_messages_data and posts through rep_messages_send.
# ---------------------------------------------------------------------------
MESSAGE_MAX_LENGTH = 2000


def serialize_chat_message(m):
    return {
        "id": m.id,
        "sender": m.sender,
        "body": m.body,
        "time": timezone.localtime(m.created_at).strftime("%b %d, %Y · %I:%M %p").replace(" 0", " "),
    }


@office_rep_required
def rep_messages(request, rep):
    return render(request, "office_dashboard/messages.html", {"rep": rep})


@office_rep_required
def rep_messages_data(request, rep):
    try:
        after = int(request.GET.get("after", 0))
    except (TypeError, ValueError):
        after = 0

    # Opening the conversation marks the Super Admin's messages as read.
    rep.chat_messages.filter(
        sender=Message.SENDER_ADMIN, read_at__isnull=True
    ).update(read_at=timezone.now())

    items = rep.chat_messages.filter(id__gt=after)
    return JsonResponse({"messages": [serialize_chat_message(m) for m in items]})


@office_rep_required
def rep_messages_send(request, rep):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required."}, status=405)
    body = request.POST.get("body", "").strip()
    if not body:
        return JsonResponse({"success": False, "error": "Type a message first."}, status=400)
    if len(body) > MESSAGE_MAX_LENGTH:
        return JsonResponse({"success": False, "error": f"Messages are limited to {MESSAGE_MAX_LENGTH} characters."}, status=400)

    msg = Message.objects.create(representative=rep, sender=Message.SENDER_REP, body=body)
    return JsonResponse({"success": True, "message": serialize_chat_message(msg)})


# ---------------------------------------------------------------------------
# Organizational Chart: people and sections in a tree, built by the office rep
# ---------------------------------------------------------------------------
ORG_PHOTO_MAX_MB = 5


@office_rep_required
def org_chart(request, rep):
    view_url = reverse("offices:office_detail", args=[rep.office.slug]) + "#org-chart" if rep.office.slug else ""
    return org_chart_page(request, rep, "office_dashboard/org-chart.html", can_publish=True,
                          extra={"publish_place": "your office page", "publish_view_url": view_url})


def org_chart_page(request, rep, template, can_publish=False, extra=None, office=None):
    """The Organizational Chart builder. Shared by the Office Representative
    dashboard and the Super Admin dashboard (admin_dashboard.views.admin_org_chart).
    rep    = who is working on it (activity log); office = whose chart it is
             (default: the rep's own office; the Super Admin can open any office's).
    extra  = more template context; extra["publish_place"] is how the public
             page is named in messages (e.g. "your office page").
    Every redirect goes back to the page it was opened from (request.path)."""
    office = office or rep.office
    here = request.path
    extra = extra or {}
    place = extra.get("publish_place", "your office page")
    # when the Super Admin edits an office's chart, the log says which office
    where = "" if office.pk == rep.office_id else f" of {office.name}"

    if request.method == "POST":
        action = request.POST.get("action")
        node = None
        if request.POST.get("id"):
            node = OrgChartNode.objects.filter(pk=request.POST.get("id"), office=office).first()
            if node is None:
                messages.error(request, "That box no longer exists.")
                return redirect(here)

        if action == "delete" and node:
            # People under the deleted box move up to its own parent, so
            # nobody disappears from the chart by accident.
            OrgChartNode.objects.filter(office=office, parent=node).update(parent=node.parent)
            name = node.name
            if node.photo:
                node.photo.delete(save=False)
            node.delete()
            messages.success(request, f'"{name}" was removed from the chart.')
            log_activity(rep, "Org chart updated", f'Removed "{name}" from the organizational chart{where}', "content", "fa-solid fa-sitemap", "var(--red-600)")
            return redirect(here)

        if action == "position" and node:
            # A box was dragged to a new spot on the chart (saved in the
            # background, the page doesn't reload).
            try:
                x = max(-20000, min(20000, int(float(request.POST.get("x")))))
                y = max(-20000, min(20000, int(float(request.POST.get("y")))))
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": "Bad position."}, status=400)
            OrgChartNode.objects.filter(pk=node.pk).update(pos_x=x, pos_y=y)
            return JsonResponse({"ok": True})

        if action == "resize" and node:
            # The box's corner was dragged on the chart (saved in the background).
            w = clean_org_width(request.POST.get("w"))
            if not w:
                return JsonResponse({"ok": False, "error": "Bad size."}, status=400)
            node.style = {**(node.style or {}), "w": w}
            node.style.pop("size", None)
            node.save(update_fields=["style", "updated_at"])
            return JsonResponse({"ok": True, "w": w})

        if action == "publish" and can_publish:
            # "Show on office page" button: display the chart at the bottom of
            # the office's public page (or take it off again).
            settings_obj = OrgChartSettings.for_office(office)
            settings_obj.show_on_office_page = request.POST.get("show") == "1"
            settings_obj.save()
            if settings_obj.show_on_office_page:
                messages.success(request, f"The organizational chart is now shown on {place}.")
                log_activity(rep, "Org chart published", f"Showed the organizational chart{where} on {place}", "content", "fa-solid fa-sitemap", "var(--green-600)")
            else:
                messages.success(request, f"The organizational chart is no longer shown on {place}.")
                log_activity(rep, "Org chart hidden", f"Removed the organizational chart{where} from {place}", "content", "fa-solid fa-sitemap", "var(--gray-500)")
            back = request.POST.get("back") or ""
            return redirect(here + (back if back.startswith("?") else ""))

        if action == "auto_layout":
            OrgChartNode.objects.filter(office=office).update(pos_x=None, pos_y=None)
            messages.success(request, "Every box was put back in its automatic place.")
            log_activity(rep, "Org chart updated", f"Auto-arranged the organizational chart{where}", "content", "fa-solid fa-sitemap", "var(--blue-600)")
            return redirect(here)

        if action == "save":
            kind = request.POST.get("kind")
            kind = kind if kind in dict(OrgChartNode.KIND_CHOICES) else OrgChartNode.KIND_PERSON
            name = request.POST.get("name", "").strip()[:150]
            position = request.POST.get("position", "").strip()[:200]
            photo = request.FILES.get("photo")

            parent = None
            parent_id = request.POST.get("parent") or ""
            if parent_id:
                parent = OrgChartNode.objects.filter(pk=parent_id, office=office).first()

            errors = []
            if not name:
                errors.append("Name is required." if kind == OrgChartNode.KIND_PERSON else "Section title is required.")
            if parent_id and parent is None:
                errors.append("The box it reports to no longer exists.")
            if node and parent:
                _, all_nodes = build_org_tree(office)
                if parent.pk == node.pk or parent.pk in org_descendant_ids(node, all_nodes):
                    errors.append("A box can't report to itself or to someone under it.")
            if photo:
                if photo.size > ORG_PHOTO_MAX_MB * 1024 * 1024:
                    errors.append(f"The photo is larger than {ORG_PHOTO_MAX_MB} MB.")
                else:
                    try:
                        dj_forms.ImageField().clean(photo)
                    except ValidationError:
                        errors.append("The photo must be a JPG, PNG or WEBP image.")

            if errors:
                for err in errors:
                    messages.error(request, err)
                back = f"?edit={node.pk}" if node else (f"?add_under={parent_id}" if parent_id else "")
                return redirect(here + back)

            is_new = node is None
            if is_new:
                node = OrgChartNode(office=office, order=next_org_order(office, parent.pk if parent else None))
            elif node.parent_id != (parent.pk if parent else None):
                node.order = next_org_order(office, parent.pk if parent else None)   # moved: goes to the end of its new row
                node.pos_x = node.pos_y = None                                       # and takes its automatic place under the new box
            node.kind, node.name, node.parent = kind, name, parent
            node.style = clean_org_style(request.POST, kind)
            node.position = position if kind == OrgChartNode.KIND_PERSON else ""
            if kind == OrgChartNode.KIND_SECTION or request.POST.get("remove_photo") == "1":
                if node.photo:
                    node.photo.delete(save=False)
                node.photo = None
            if photo and kind == OrgChartNode.KIND_PERSON:
                if node.photo:
                    node.photo.delete(save=False)
                node.photo = photo
            node.save()

            # "Apply this style to…": everyone under this box, or the whole chart
            scope = request.POST.get("style_scope")
            if scope in ("below", "all"):
                _, all_nodes = build_org_tree(office)
                if scope == "below":
                    ids = org_descendant_ids(node, all_nodes)
                    targets = [n for n in all_nodes if n.pk in ids]
                else:
                    targets = [n for n in all_nodes if n.pk != node.pk]
                for other in targets:
                    OrgChartNode.objects.filter(pk=other.pk).update(style=org_style_for(other, node.style, kind))

            messages.success(request, f'"{name}" was {"added to" if is_new else "updated on"} the chart.'
                             + (" The style was also applied to everyone under it." if scope == "below" else "")
                             + (" The style was also applied to the whole chart." if scope == "all" else ""))
            log_activity(rep, "Org chart updated", f'{"Added" if is_new else "Updated"} "{name}" on the organizational chart{where}', "content", "fa-solid fa-sitemap", "var(--blue-600)")
            return redirect(here + f"?edit={node.pk}")

        return redirect(here)

    roots, nodes = build_org_tree(office)
    by_id = {n.id: n for n in nodes}
    editing = by_id.get(_int_or_none(request.GET.get("edit")))
    add_under = by_id.get(_int_or_none(request.GET.get("add_under")))
    return render(request, template, {
        **extra,
        "publish_place": place,
        "rep": rep,
        "can_publish": can_publish,
        "nodes": nodes,
        "org_settings": OrgChartSettings.for_office(office),
        "node_count": len(nodes),
        "editing": editing,
        "add_under": add_under,
        "parent_choices": org_parent_choices(nodes, exclude=editing),
        "form_kind": editing.kind if editing else ("section" if request.GET.get("kind") == "section" else "person"),
        "style_defaults": {"colors": ORG_DEFAULT_COLORS, "line": ORG_DEFAULT_LINE, **ORG_STYLE_DEFAULTS},
    })


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None