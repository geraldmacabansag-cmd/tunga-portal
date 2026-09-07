from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo

from functools import wraps
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError



def office_rep_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        rep = OfficeRepresentative.objects.filter(user=request.user).first()
        if rep is None:
            messages.error(request, "Your account isn't linked to an Office Representative profile.")
            return redirect("home")
        return view_func(request, rep, *args, **kwargs)
    return wrapper

@office_rep_required
def rep_announcement(request, rep):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Announcement title is required.")
        else:
            Announcement.objects.create(
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

    paginator = Paginator(announcements, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "office_dashboard/announcements.html", {
        "rep": rep,
        "page_obj": page_obj,
        "announcements": page_obj.object_list,
        "current_q": q,
        "current_status": status,
        "current_sort": sort,
    })

@office_rep_required
def edit_announcement(request, rep, pk):
    announcement = get_object_or_404(Announcement, pk=pk, representative=rep)

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
        return redirect('office_dashboard:rep_announce')

    return redirect('office_dashboard:rep_announce')


@office_rep_required
def delete_announcement(request, rep, pk):
    announcement = get_object_or_404(Announcement, pk=pk, representative=rep)

    if request.method == "POST":
        title = announcement.title
        announcement.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect('office_dashboard:rep_announce')

@office_rep_required
def dashboard(request, rep):
    return render(request, "office_dashboard/dashboard.html", {"rep": rep})

@office_rep_required
def news_update(request, rep):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "News headline is required.")
        else:
            NewsUpdate.objects.create(
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

    paginator = Paginator(news_items, 4)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "office_dashboard/news-updates.html", {
        "rep": rep,
        "page_obj": page_obj,
        "news_items": page_obj.object_list,
        "current_q": q,
        "current_status": status,
        "current_sort": sort,
    })

@office_rep_required
def edit_news(request, rep, pk):
    news = get_object_or_404(NewsUpdate, pk=pk, representative=rep)

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
        return redirect('office_dashboard:news_update')

    return redirect('office_dashboard:news_update')

@office_rep_required
def delete_news(request, rep, pk):
    news = get_object_or_404(NewsUpdate, pk=pk, representative=rep)

    if request.method == "POST":
        title = news.title
        news.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect('office_dashboard:news_update')

@office_rep_required
def events(request, rep):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Event title is required.")
        else:
            Event.objects.create(
                representative=rep,
                title=title,
                category=request.POST.get('category', ''),
                description=request.POST.get('description', ''),
                event_date=request.POST.get('event_date') or None,
                start_time=request.POST.get('start_time') or None,
                end_time=request.POST.get('end_time') or None,
                location=request.POST.get('location', ''),
                organizer=request.POST.get('organizer', ''),
                contact_person=request.POST.get('contact_person', ''),
                contact_info=request.POST.get('contact_info', ''),
                poster=request.FILES.get('poster'),
            )
            messages.success(request, f'"{title}" was added and is pending approval.')
        return redirect('office_dashboard:event')

    events_qs = rep.events.all()

    q = request.GET.get('q', '').strip()
    if q:
        events_qs = events_qs.filter(title__icontains=q)

    status = request.GET.get('status', '')
    if status:
        events_qs = events_qs.filter(status=status)

    when = request.GET.get('when', 'upcoming')
    today = timezone.localdate()
    if when == 'upcoming':
        events_qs = events_qs.filter(event_date__gte=today)
    elif when == 'past':
        events_qs = events_qs.filter(event_date__lt=today)
    # when == 'all' -> no date filter

    events_qs = events_qs.order_by('event_date', 'start_time')

    paginator = Paginator(events_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "office_dashboard/events.html", {
        "rep": rep,
        "page_obj": page_obj,
        "events": page_obj.object_list,
        "current_q": q,
        "current_status": status,
        "current_when": when,
    })

@office_rep_required
def edit_event(request, rep, pk):
    event = get_object_or_404(Event, pk=pk, representative=rep)

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
        return redirect('office_dashboard:event')

    return redirect('office_dashboard:event')

@office_rep_required
def delete_event(request, rep, pk):
    event = get_object_or_404(Event, pk=pk, representative=rep)

    if request.method == "POST":
        title = event.title
        event.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect('office_dashboard:event')

@office_rep_required
def services(request, rep):
    return render(request, "office_dashboard/office-rep-service-details.html", {"rep": rep})

@office_rep_required
def downloadable_forms(request, rep):
    return render(request, "office_dashboard/downloadable-forms.html", {"rep": rep})

@office_rep_required
def gallery(request, rep):
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        image = request.FILES.get('image')

        if not title:
            messages.error(request, "Caption / title is required.")
        elif not image:
            messages.error(request, "Please choose a photo to upload.")
        else:
            Photo.objects.create(
                representative=rep,
                title=title,
                image=image,
                # status not set -> defaults to "pending"
            )
            messages.success(request, f'"{title}" was uploaded and is pending approval.')
        return redirect('office_dashboard:gallery')

    return render(request, "office_dashboard/gallery.html", {
        "rep": rep,
        "photos": rep.photos.order_by('-created_at'),
    })

@office_rep_required
def delete_photo(request, rep, pk):
    photo = get_object_or_404(Photo, pk=pk, representative=rep)

    if request.method == "POST":
        title = photo.title
        photo.delete()
        messages.success(request, f'"{title}" was deleted.')

    return redirect('office_dashboard:gallery')

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
        return redirect('office_dashboard:profile')

    return render(request, "office_dashboard/office-profile.html", {
        "rep": rep,
        "office": office,
    })

@office_rep_required
def office_directory(request, rep):
    return render(request, "office_dashboard/office-directory.html", {"rep": rep})

@office_rep_required
def office_location(request, rep):
    return render(request, "office_dashboard/office-location.html", {"rep": rep})

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

        return redirect('office_dashboard:change_pass')

    return render(request, "office_dashboard/change-password.html", {"rep": rep})

@office_rep_required
def notification(request, rep):
    return render(request, "office_dashboard/notification.html", {"rep": rep})

@office_rep_required
def activity_log(request, rep):
    return render(request, "office_dashboard/activity-logs.html", {"rep": rep})