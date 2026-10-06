import calendar as cal_module
from datetime import date
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import CitizenProfile
from office_dashboard.models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo, Album, Service, DownloadableForm, FormSubmission
from django.db.models import Count, Q
from admin_dashboard.models import SuperAdmin, EmergencyContact, QuickLink
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from .models import CitizenProfile, EmailOTP
from .otp_utils import send_signup_otp
from django.http import JsonResponse
from .otp_utils import send_signup_otp, send_password_reset_otp
from offices.models import Office
from django.core.paginator import Paginator

# ---------------------------------------------------------------------------
# Shared helpers for the Events tab's sidebar "month calendar" — used by both
# the full announcement() page render and the events_calendar_partial() AJAX
# endpoint the "‹ ›" arrows now call, so a month change no longer reloads the
# whole page (which was resetting the scroll position back to the top).
# ---------------------------------------------------------------------------

def _get_featured_event(today):
    """The event the Events tab's calendar should mark as "featured" (red)
    for whichever month it falls in — same selection rule used for the big
    "Featured Event" hero on the main Events tab: an explicitly
    Super-Admin-featured event if there is one, else the soonest upcoming
    published event, else None."""
    dated_upcoming = list(
        Event.objects.filter(status='published', event_date__gte=today)
        .order_by('event_date', 'start_time')
    )
    undated_upcoming = list(
        Event.objects.filter(status='published', event_date__isnull=True)
        .order_by('-created_at')
    )
    upcoming_qs = dated_upcoming + undated_upcoming

    featured_dated = [e for e in dated_upcoming if e.is_featured]
    featured_undated = [e for e in undated_upcoming if e.is_featured]
    featured_candidates = featured_dated + featured_undated

    if featured_candidates:
        return featured_candidates[0]
    if upcoming_qs:
        return upcoming_qs[0]
    return None


def _build_month_calendar(request, today, featured_event, month_param_name='events_month'):
    """Builds one month's worth of calendar cells for the given ?<month_param_name>=YYYY-MM
    (falling back to the current month if missing/malformed), plus the
    prev/next month params for the "‹ ›" arrows."""
    month_param = request.GET.get(month_param_name, '').strip()
    try:
        cal_year, cal_month = [int(part) for part in month_param.split('-')]
        if not (1 <= cal_month <= 12):
            raise ValueError
    except (ValueError, TypeError):
        cal_year, cal_month = today.year, today.month

    month_events = list(
        Event.objects.filter(status='published', event_date__year=cal_year, event_date__month=cal_month)
        .select_related('representative__office')
        .order_by('event_date', 'start_time')
    )
    for e in month_events:
        e.category_label = e.category or "General"

    events_by_day = {}
    for e in month_events:
        events_by_day.setdefault(e.event_date.day, []).append(e)

    featured_day = featured_event.event_date.day if (
        featured_event and featured_event.event_date
        and featured_event.event_date.year == cal_year and featured_event.event_date.month == cal_month
    ) else None

    calendar_weeks = []
    for week in cal_module.Calendar(firstweekday=6).monthdayscalendar(cal_year, cal_month):
        week_cells = []
        for day in week:
            if day == 0:
                week_cells.append(None)
                continue
            day_events = events_by_day.get(day, [])
            cell_date = date(cal_year, cal_month, day)
            week_cells.append({
                "day": day,
                "date_obj": cell_date,
                "events": day_events,
                "is_today": cell_date == today,
                "is_featured": day == featured_day,
            })
        calendar_weeks.append(week_cells)

    prev_year, prev_month = (cal_year - 1, 12) if cal_month == 1 else (cal_year, cal_month - 1)
    next_year, next_month = (cal_year + 1, 1) if cal_month == 12 else (cal_year, cal_month + 1)

    return {
        "cal_year": cal_year,
        "cal_month": cal_month,
        "month_events": month_events,
        "calendar_weeks": calendar_weeks,
        "calendar_month_label": date(cal_year, cal_month, 1).strftime("%B %Y"),
        "calendar_prev_param": f"{prev_year:04d}-{prev_month:02d}",
        "calendar_next_param": f"{next_year:04d}-{next_month:02d}",
    }


def events_calendar_partial(request):
    """AJAX endpoint for the Events tab calendar's "‹ ›" arrows: returns just
    the month header + day grid + event-detail <template>s for the
    requested month, so JS can swap it into the page in place instead of
    doing a full reload — which was resetting the page's scroll position
    back to the top every time a different month was picked."""
    today = timezone.localdate()
    featured_event = _get_featured_event(today)
    calendar_ctx = _build_month_calendar(request, today, featured_event)
    return render(request, "portal/_events_calendar_dynamic.html", calendar_ctx)


# Create your views here.
def home(request):
    home_announcements = list(
        Announcement.objects.filter(status='published')
        .order_by('-date_posted', '-created_at')[:3]
    )
    for a in home_announcements:
        a.display_date = a.date_posted or a.created_at.date()

    upcoming_event = (
        Event.objects.filter(status='published', event_date__gte=timezone.localdate())
        .order_by('event_date')
        .first()
    )

    latest_news = (
        NewsUpdate.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_published', '-created_at')
        .first()
    )

    gallery_photos = list(
        Photo.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-created_at')[:16]
    )

    return render(request, "portal/home.html", {
        "emergency_contacts": EmergencyContact.objects.all(),
        "home_announcements": home_announcements,
        "upcoming_event": upcoming_event,
        "latest_news": latest_news,
        "gallery_photos": gallery_photos,
        "quick_links": QuickLink.objects.filter(is_active=True),
    })

def announcement(request):
    announcements = list(
        Announcement.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_posted', '-created_at')[:5]
    )
    for a in announcements:
        a.display_date = a.date_posted or a.created_at.date()

    news_items = list(
        NewsUpdate.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_published', '-created_at')[:5]
    )
    for n in news_items:
        n.display_date = n.date_published or n.created_at.date()

    # Full list for the "Announcements" tab — every published announcement,
    # newest first, with the extra display fields the card layout needs.
    all_announcements = list(
        Announcement.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_posted', '-created_at')
    )

    new_cutoff = timezone.now() - timezone.timedelta(days=3)

    # Preferred display order for categories that do have published posts
    # (matches the "Category" dropdown in the office-rep / super-admin
    # announcement forms). Anything not in this list (e.g. "General" for a
    # blank category, or an older/legacy category value) is appended
    # afterwards, alphabetically.
    CATEGORY_ORDER = [
        "Community Engagement",
        "Public Notice",
        "Office Advisory",
        "Government Service",
        "Emergency",
    ]

    category_counts = {}

    for a in all_announcements:
        a.display_date = a.date_posted or a.created_at.date()
        a.is_new = a.created_at >= new_cutoff
        a.category_label = a.category or "General"
        a.category_slug = slugify(a.category_label) or "general"
        category_counts[a.category_label] = category_counts.get(a.category_label, 0) + 1

    # Only categories that actually have at least one published announcement
    # show up as filter pills / in the sidebar — no empty categories.
    known_names = [name for name in CATEGORY_ORDER if name in category_counts]
    extra_names = sorted(name for name in category_counts if name not in CATEGORY_ORDER)
    ordered_names = known_names + extra_names

    announcement_categories = [
        {"name": name, "slug": slugify(name) or "general", "count": category_counts[name]}
        for name in ordered_names
    ]

    # "Pinned Notice" box at the top of the Announcements tab — the Super
    # Admin can pin one announcement (Announcement.is_pinned) to keep it
    # showing there regardless of date. If more than one is pinned, the most
    # recently posted one wins; all_announcements is already newest-first.
    pinned_announcement = next((a for a in all_announcements if a.is_pinned), None)

    # Full list for the "News" tab — every published news post, newest
    # first. The featured row (1 big + 2 small cards) takes the 3 newest;
    # everything else goes in the "Latest News" grid below it. Pagination,
    # the sidebar (Search/Most Read/Topics/Share box) stay hardcoded for now.
    all_news = list(
        NewsUpdate.objects.filter(status='published')
        .select_related('representative__office')
        .order_by('-date_published', '-created_at')
    )

    # Badge colors are only defined (in announcements.css) for these known
    # slugs — anything else (a category typed differently, or left blank)
    # falls back to a plain gray "general" badge rather than an unstyled one.
    KNOWN_NEWS_CATEGORY_SLUGS = {
        "governance", "technology", "sports",
        "environment", "education", "infrastructure",
    }

    for n in all_news:
        n.display_date = n.date_published or n.created_at.date()
        n.category_label = n.category or "General"
        slug = slugify(n.category_label) or "general"
        n.category_slug = slug if slug in KNOWN_NEWS_CATEGORY_SLUGS else "general"

    featured_news = all_news[:3]
    news_main_story = featured_news[0] if len(featured_news) > 0 else None
    news_side_stories = featured_news[1:3]
    news_grid_items_all = all_news[3:]

    # "Latest News" grid pagination — 6 per page (3 rows of the 2-column
    # grid). Uses its own ?news_page= query param (not the Events tab's
    # ?events_month=) plus the #news hash, same pattern as the Events tab's
    # "‹ ›" month links: a normal page reload that lands back on the right
    # tab via the hash-restore script at the bottom of the template.
    news_paginator = Paginator(news_grid_items_all, 6)
    news_page_obj = news_paginator.get_page(request.GET.get('news_page'))
    news_grid_items = news_page_obj.object_list

    # "All Updates" tab: its News rows open the same modal as the News tab.
    # Use the 5 newest (already annotated above) and work out which of them
    # have no <template> yet on the page (the News tab only renders the
    # featured stories + the current grid page), so those get one of their own.
    news_items = all_news[:5]
    _covered_news_ids = {n.id for n in featured_news} | {n.id for n in news_grid_items}
    news_items_extra = [n for n in news_items if n.id not in _covered_news_ids]

    # For the "Events" tab — the Super Admin can mark a specific event as
    # "Featured" (Event.is_featured) so it becomes the big "Featured Event"
    # hero regardless of where it falls in the date order. If none is marked
    # featured, the soonest upcoming published event is used instead, same as
    # before. The next several upcoming events fill the "Upcoming Events"
    # grid, and recently-finished ones show under "Past Events". The
    # calendar widget and "Up Next" list in the sidebar stay hardcoded for
    # now, same as the rest of this page's still-unconfigured panels.
    today = timezone.localdate()

    # event_date is optional on the model, and neither the office-rep nor the
    # Super Admin "Add Event" form requires it — so a published event with no
    # date set would otherwise vanish here entirely: a plain event_date__gte
    # / __lt=today filter excludes NULLs in SQL, matching neither "upcoming"
    # nor "past". Undated published events are treated as upcoming (with a
    # "Date to be announced" fallback in the template) so they're never
    # silently invisible on the public page.
    dated_upcoming = list(
        Event.objects.filter(status='published', event_date__gte=today)
        .select_related('representative__office')
        .order_by('event_date', 'start_time')
    )
    undated_upcoming = list(
        Event.objects.filter(status='published', event_date__isnull=True)
        .select_related('representative__office')
        .order_by('-created_at')
    )
    upcoming_qs = dated_upcoming + undated_upcoming

    past_qs = list(
        Event.objects.filter(status='published', event_date__lt=today)
        .select_related('representative__office')
        .order_by('-event_date', '-start_time')[:3]
    )

    for e in upcoming_qs + past_qs:
        e.category_label = e.category or "General"

    # Prefer an event the Super Admin explicitly marked as featured. Among
    # dated events that's already in soonest-first order, but a
    # featured-and-undated event could otherwise get pushed behind featured
    # dated ones (undated events are appended after dated ones in
    # upcoming_qs) — so pick the soonest-dated featured event first, and only
    # fall back to an undated featured one if that's all there is.
    featured_dated = [e for e in dated_upcoming if e.is_featured]
    featured_undated = [e for e in undated_upcoming if e.is_featured]
    featured_candidates = featured_dated + featured_undated

    if featured_candidates:
        featured_event = featured_candidates[0]
    elif upcoming_qs:
        featured_event = upcoming_qs[0]
    else:
        featured_event = None

    upcoming_events = [e for e in upcoming_qs if e != featured_event][:6]
    past_events = past_qs

    # "Up Next" sidebar panel on the Events tab — a quick-glance list of the
    # 4 soonest dated upcoming events (undated ones have no "OCT 10"-style
    # date to show here, so they're left to the main Upcoming Events grid).
    up_next_events = dated_upcoming[:4]

    # ---- Events tab sidebar: the small month calendar --------------------
    # ?events_month=YYYY-MM lets the "‹ ›" arrows browse other months. The
    # arrows themselves now fetch this via events_calendar_partial() over
    # AJAX (see that view + the Events tab's JS) instead of reloading the
    # whole page, but this same helper builds the calendar for the initial
    # page load too, so both stay in sync.
    calendar_ctx = _build_month_calendar(request, today, featured_event)
    cal_year = calendar_ctx["cal_year"]
    cal_month = calendar_ctx["cal_month"]
    month_events = calendar_ctx["month_events"]
    calendar_weeks = calendar_ctx["calendar_weeks"]

    # Templates for the Announcement/News/Event detail dialogs are rendered
    # once per event on the page; featured_event/upcoming_events/past_events
    # already render one each, so only render extra ones here for a
    # calendar event that isn't already shown as a card above (e.g. a past
    # event no longer in the "Past Events" top-3, or one further out than
    # the "Upcoming Events" top-6).
    already_rendered_ids = {e.id for e in upcoming_events + past_events}
    if featured_event:
        already_rendered_ids.add(featured_event.id)
    calendar_only_events = [e for e in month_events if e.id not in already_rendered_ids]

    # ---- "From Our Offices" sidebar panel (All Updates tab) --------------
    # One row per office that has at least one published announcement, each
    # showing that office's single most recent one — picked by walking every
    # published announcement newest-first and keeping the first (i.e.
    # latest) one seen per office, so the offices with the freshest activity
    # naturally float to the top.
    office_updates = []
    seen_office_ids = set()
    recent_office_anns = (
        Announcement.objects.filter(status='published')
        .filter(representative__office__isnull=False, representative__office__is_visible=True)
        .exclude(representative__office__slug='lgu-super-admin')
        .select_related('representative__office')
        .order_by('-date_posted', '-created_at')
    )
    for a in recent_office_anns:
        office = a.representative.office
        if office.id in seen_office_ids:
            continue
        seen_office_ids.add(office.id)
        icon, color, icon_image = get_office_card_style(office)
        office_url = reverse('offices:office_detail', args=[office.slug])
        office_updates.append({
            "office": office,
            "url": office_url,
            "icon": icon,
            "icon_image": icon_image,
            "color": color,
            "latest_title": a.title,
            "latest_time": a.created_at,
        })
        if len(office_updates) >= 8:
            break

    # ---- "From Our Offices" TAB (full directory) --------------------------
    # Only offices the Super Admin has actually "activated" should appear
    # here. In the Super Admin > Offices dashboard, an office's status is
    # 'active' only when it has an assigned representative AND that rep's
    # account is active (rep is None -> 'pending', rep.user.is_active is
    # False -> 'inactive') — this is a different flag from is_visible
    # (which only controls whether the office is shown/hidden on the public
    # Offices page), so both checks are applied: still hidden if unpublished
    # from the Offices page, and now also hidden until it's been activated.
    office_directory = []
    active_offices = (
        Office.objects.exclude(slug='lgu-super-admin')
        .filter(is_visible=True, representative__isnull=False, representative__user__is_active=True)
        .select_related('representative__user')
        .order_by('display_order', 'name')
    )
    for office in active_offices:
        icon, color, _ = get_office_card_style(office)
        office_url = reverse('offices:office_detail', args=[office.slug])
        office_anns = Announcement.objects.filter(status='published', representative__office=office)
        latest = office_anns.order_by('-date_posted', '-created_at').first()
        office_directory.append({
            "office": office,
            "url": office_url,
            "icon": icon,
            "color": color,
            "latest": latest,
            "latest_display_date": (latest.date_posted or latest.created_at.date()) if latest else None,
            "count": office_anns.count(),
        })

    office_directory.sort(key=lambda item: (
        0 if item["latest"] else 1,
        -item["latest"].created_at.timestamp() if item["latest"] else 0,
        item["office"].name,
    ))

    return render(request, "portal/announcements.html", {
        "announcements": announcements,
        "news_items": news_items,
        "news_items_extra": news_items_extra,
        "all_announcements": all_announcements,
        "announcement_categories": announcement_categories,
        "pinned_announcement": pinned_announcement,
        "news_main_story": news_main_story,
        "news_side_stories": news_side_stories,
        "news_grid_items": news_grid_items,
        "news_page_obj": news_page_obj,
        "featured_event": featured_event,
        "upcoming_events": upcoming_events,
        "past_events": past_events,
        "up_next_events": up_next_events,
        "calendar_weeks": calendar_weeks,
        "calendar_month_label": calendar_ctx["calendar_month_label"],
        "calendar_prev_param": calendar_ctx["calendar_prev_param"],
        "calendar_next_param": calendar_ctx["calendar_next_param"],
        "calendar_only_events": calendar_only_events,
        "office_updates": office_updates,
        "office_directory": office_directory,
        # Same source as the homepage's "Emergency Contact Information"
        # section, so both pages always show the same hotlines.
        "emergency_contacts": EmergencyContact.objects.all(),
    })

OFFICE_CARD_STYLE = {
    "office-of-the-mayor": ("fa-solid fa-user-tie", "navy", "icons/mayors_office.jpg"),
    "sangguniang-bayan-sb": ("fa-solid fa-gavel", "purple", "icons/sangguniangbayan.png"),
    "municipal-treasurer's-office": ("fa-solid fa-coins", "red", "icons/mun._treasurers_office.jpg"),
    "municipal-assessor's-office": ("fa-regular fa-clipboard", "purple", "icons/mun._assessors_office.jpg"),
    "municipal-accounting-office": ("fa-solid fa-calculator", "navy", "icons/oma.png"),
    "municipal-budget-office": ("fa-solid fa-chart-pie", "green2", "icons/budgetoffice.png"),
    "municipal-planning-and-development-coordinator": ("fa-solid fa-map", "green", "icons/MPDC.jpg"),
    "municipal-civil-registrar's-office": ("fa-solid fa-file-signature", "navy", "icons/omcr.jpg"),
    "municipal-health-office": ("fa-solid fa-house-medical", "green", "icons/mun._health_office.jpg"),
    "municipal-social-welfare-and-development-office-mswdo": ("fa-solid fa-hand-holding-heart", "red", "icons/mun._social_welfare_dev._office.jpg"),
    "municipal-engineering-office": ("fa-solid fa-hard-hat", "navy", "icons/mun._engineering_office.jpg"),
    "municipal-agriculture-office": ("fa-solid fa-seedling", "orange", "icons/mun._agri._office.jpg"),
    "business-permits-and-licensing-office-bplo": ("fa-solid fa-briefcase", "gold", "icons/bplo.png"),
    "human-resource-management-office-hrmo": ("fa-solid fa-users", "purple", "icons/humanresource.png"),
    "municipal-disaster-risk-reduction-management": ("fa-solid fa-triangle-exclamation", "navy", "icons/MDRRMO.jpg"),
    "municipal-environment-and-natural-resources-office": ("fa-regular fa-building", "green2", "icons/mun._environment_office.jpg"),
    "local-youth-development-office": ("fa-solid fa-people-group", "gold", "icons/lydo.png"),
    "municipal-tourism-office": ("fa-solid fa-compass", "gold", "icons/mto.png"),
    "office-of-the-bac-and-the-bac-secretariat": ("fa-solid fa-file-contract", "purple", "icons/oBAC.png"),
    "office-of-the-general-services": ("fa-solid fa-briefcase", "navy", "icons/officeofthegeneralservices.png"),
}
OFFICE_CARD_DEFAULT = ("fa-solid fa-landmark", "navy", None)


# Extra entry for the Vice Mayor's office (no uploaded seal image yet, so it
# gets a Font Awesome icon only).
OFFICE_CARD_STYLE.setdefault(
    "office-of-the-vice-mayor", ("fa-solid fa-user-tie", "green", None)
)

# When an office's slug isn't an exact key above (it was created or renamed
# on the live site under a slightly different name — "MPDO" instead of
# "Municipal Planning and Development Coordinator", "SB Office", "Office of
# the Vice Mayor", ...), fall back to matching words in its name/slug. First
# rule that matches wins, so the more specific ones come first.
_OFFICE_STYLE_RULES = [
    (("vice mayor", "vice-mayor", "vice-mayor's"), "office-of-the-vice-mayor"),
    (("sangguniang", "sb office", "sb-office", "sb office"), "sangguniang-bayan-sb"),
    (("planning", "mpdo", "mpdc"), "municipal-planning-and-development-coordinator"),
    (("treasur",), "municipal-treasurer's-office"),
    (("assessor",), "municipal-assessor's-office"),
    (("account",), "municipal-accounting-office"),
    (("budget",), "municipal-budget-office"),
    (("civil registrar", "civil-registrar", "mcr"), "municipal-civil-registrar's-office"),
    (("health", "mho"), "municipal-health-office"),
    (("social welfare", "social-welfare", "mswdo"), "municipal-social-welfare-and-development-office-mswdo"),
    (("engineer", "building official"), "municipal-engineering-office"),
    (("agricultur", "mao"), "municipal-agriculture-office"),
    (("permit", "bplo"), "business-permits-and-licensing-office-bplo"),
    (("human resource", "human-resource", "hrmo"), "human-resource-management-office-hrmo"),
    (("disaster", "mdrrmo", "drrm"), "municipal-disaster-risk-reduction-management"),
    (("environment", "menro"), "municipal-environment-and-natural-resources-office"),
    (("youth", "lydo"), "local-youth-development-office"),
    (("tourism",), "municipal-tourism-office"),
    (("bac",), "office-of-the-bac-and-the-bac-secretariat"),
    (("general services", "general-services"), "office-of-the-general-services"),
    (("mayor",), "office-of-the-mayor"),
]


def get_office_card_style(office):
    """(icon_class, color, static_image_or_None) for an office card."""
    style = OFFICE_CARD_STYLE.get(office.slug)
    if style:
        return style
    haystack = f"{office.name} {office.slug}".lower().replace("’", "'")
    for words, key in _OFFICE_STYLE_RULES:
        if any(w in haystack for w in words):
            return OFFICE_CARD_STYLE[key]
    return OFFICE_CARD_DEFAULT


def gallery(request):
    # Every published photo regardless of who posted it — an office
    # representative or the Super Admin (who posts through the same
    # Photo/representative FK via a synthetic "LGU Super Admin" office/
    # representative row) — so nothing needs excluding here, unlike the
    # office directory queries that deliberately hide that internal record.
    photos_qs = (
        Photo.objects.filter(status='published')
        .select_related('representative__office', 'album')
        .order_by('-created_at')
    )

    total_photos = photos_qs.count()

    current_category = request.GET.get('category', '').strip()
    if current_category:
        photos_qs = photos_qs.filter(category__iexact=current_category)

    current_album = request.GET.get('album', '').strip()
    if current_album:
        photos_qs = photos_qs.filter(album_id=current_album)

    # Sort order: by date created or date modified, newest or oldest first.
    # "-id"/"id" is a tie-breaker so the order (and pagination) stays stable.
    SORT_OPTIONS = {
        "created_desc": ("Date created (newest first)", ("-created_at", "-id")),
        "created_asc": ("Date created (oldest first)", ("created_at", "id")),
        "modified_desc": ("Date modified (latest first)", ("-last_updated", "-id")),
        "modified_asc": ("Date modified (oldest first)", ("last_updated", "id")),
    }
    current_sort = request.GET.get('sort', '').strip()
    if current_sort not in SORT_OPTIONS:
        current_sort = "created_desc"
    photos_qs = photos_qs.order_by(*SORT_OPTIONS[current_sort][1])
    sort_qs = "" if current_sort == "created_desc" else f"&sort={current_sort}"

    paginator = Paginator(photos_qs, 16)
    page_obj = paginator.get_page(request.GET.get('page'))

    # "Featured Albums" — set by the Super Admin (Album.is_featured), capped
    # at 4 to match the row's card slots. Only counts published photos, so
    # an album emptied out by moderation doesn't show a stale photo count.
    featured_albums = list(
        Album.objects
        .filter(is_featured=True)
        .annotate(published_count=Count('photos', filter=Q(photos__status='published')))
        .select_related('representative__office')
        .order_by('-created_at')[:4]
    )
    for a in featured_albums:
        a.cover_photo = a.photos.filter(status='published').order_by('-created_at').first()

    return render(request, "portal/gallery.html", {
        "page_obj": page_obj,
        "total_photos": total_photos,
        "category_choices": Photo.CATEGORY_CHOICES,
        "current_category": current_category,
        "current_album": current_album,
        "featured_albums": featured_albums,
        "sort_options": [(k, v[0]) for k, v in SORT_OPTIONS.items()],
        "current_sort": current_sort,
        "sort_qs": sort_qs,
    })


def offices(request):
    office_list = (
        Office.objects
        .exclude(slug="lgu-super-admin")
        .filter(is_visible=True)
        .order_by("display_order", "name")
    )
    for office in office_list:
        icon, color, icon_image = get_office_card_style(office)
        office.card_icon = icon
        office.card_color = color
        office.card_image = icon_image

    return render(request, "offices/offices.html", {
        "office_list": office_list,
    })

def about(request):
    from admin_dashboard.models import AboutPageContent, HistoryMilestone, AboutOfficial, Barangay

    about_content = AboutPageContent.get_solo()
    barangays_poblacion = list(Barangay.objects.filter(group="poblacion"))
    barangays_rural = list(Barangay.objects.filter(group="rural"))

    return render(request, "portal/about.html", {
        "about_content": about_content,
        "core_values": about_content.core_values_list(),
        "history_paragraphs": about_content.history_intro_paragraphs(),
        "milestones": HistoryMilestone.objects.all(),
        "about_officials": AboutOfficial.objects.all(),
        "barangays_poblacion": barangays_poblacion,
        "barangays_rural": barangays_rural,
        "barangays_total": len(barangays_poblacion) + len(barangays_rural),
    })

def history(request):
    return render(request, "portal/history.html")

def contact(request):
    # Populates the "Send Us a Message" office dropdown — only offices that
    # are publicly visible and actually have a contact email on file, since
    # that email is where the form's Gmail redirect needs to send to.
    offices_for_contact = (
        Office.objects.exclude(slug="lgu-super-admin")
        .filter(is_visible=True)
        .exclude(email="")
        .order_by("display_order", "name")
    )
    # Office Directory panel: real data from each office's profile. Only
    # offices that actually filled in a phone number and/or email are listed.
    directory_offices = list(
        Office.objects.exclude(slug="lgu-super-admin")
        .filter(is_visible=True)
        .filter(Q(email__gt="") | Q(telephone__gt=""))
        .order_by("display_order", "name")
    )
    for office in directory_offices:
        icon, color, icon_image = get_office_card_style(office)
        office.card_icon = icon
        office.card_color = color
        office.card_image = icon_image

    return render(request, "portal/contactus.html", {
        "offices_for_contact": offices_for_contact,
        "directory_offices": directory_offices,
    })

def signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        mobile_number = request.POST.get("mobile_number", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        otp_code = request.POST.get("otp_code", "").strip()

        if not all([first_name, last_name, email, password, confirm_password]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, "account/signup.html")

        if not otp_code:
            messages.error(request, "Please enter the verification code sent to your email.")
            return render(request, "account/signup.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "account/signup.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, "account/signup.html")

        # The form only ever collects the code — this is the one place that
        # actually checks it against what was emailed (right email, right
        # code, not expired, not already used). Without this call the form
        # accepted whatever digits were typed, since nothing server-side
        # was ever comparing them to the real EmailOTP record.
        if not EmailOTP.verify(email, otp_code):
            messages.error(request, "That verification code is invalid or has expired. Please request a new one.")
            return render(request, "account/signup.html")

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        CitizenProfile.objects.create(user=user, mobile_number=mobile_number)

        messages.success(request, "Account created successfully. Please log in.")
        return redirect("login")

    prefill = request.session.pop("google_prefill", None) or {}
    return render(request, "account/signup.html", {"prefill": prefill})

def send_signup_otp_ajax(request):
    if request.method != "POST" or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

    email = request.POST.get("email", "").strip().lower()
    if not email:
        return JsonResponse({"success": False, "error": "Please enter an email address first."}, status=400)

    if User.objects.filter(email=email).exists():
        return JsonResponse({"success": False, "error": "An account with this email already exists."}, status=400)

    success, error = send_signup_otp(email)
    if success:
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": error or "Could not send the code. Please try again."}, status=500)

def login(request):
    next_url = request.POST.get("next") or request.GET.get("next") or "home"

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            if SuperAdmin.objects.filter(user=user).exists():
                return redirect("admin_dashboard:admin_dash")
            if OfficeRepresentative.objects.filter(user=user).exists():
                return redirect("office_dashboard:dashboard")
            return redirect(next_url or "home")

        messages.error(request, "Invalid email or password.")
        return render(request, "account/login.html", {"next": next_url})

    return render(request, "account/login.html", {"next": next_url})

def logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")

def google_login_start(request):
    request.session['google_intent'] = 'login'
    return redirect('google_login')


def google_signup_start(request):
    request.session['google_intent'] = 'signup'
    return redirect('google_login')

def forgot_password(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        otp_code = request.POST.get("otp_code", "").strip()
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        user = (User.objects.filter(email__iexact=identifier).first()
                or User.objects.filter(username__iexact=identifier).first())

        if not user:
            messages.error(request, "No account found with that email or username.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if not otp_code:
            messages.error(request, "Please enter the verification code sent to your email.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if not EmailOTP.verify(user.email, otp_code):
            messages.error(request, "That verification code is incorrect or has expired. Please request a new one.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if not new_password or not confirm_password:
            messages.error(request, "Please enter and confirm your new password.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "account/forgot_password.html", {"identifier": identifier})

        user.set_password(new_password)
        user.save()

        messages.success(request, "Your password has been reset. Please log in with your new password.")
        return redirect("login")

    return render(request, "account/forgot_password.html")


def send_reset_otp_ajax(request):
    if request.method != "POST" or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({"success": False, "error": "Invalid request."}, status=400)

    identifier = request.POST.get("identifier", "").strip()
    if not identifier:
        return JsonResponse({"success": False, "error": "Please enter your email or username first."}, status=400)

    user = (User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username__iexact=identifier).first())
    if not user:
        return JsonResponse({"success": False, "error": "No account found with that email or username."}, status=400)

    success, error = send_password_reset_otp(user.email)
    if success:
        return JsonResponse({"success": True})
    return JsonResponse({"success": False, "error": error or "Could not send the code. Please try again."}, status=500)


# ---------------------------------------------------------------------------
# Public navbar search — a short list of JSON suggestions for whatever the
# visitor has typed so far, each one pointing straight at the page/section
# it belongs to. Announcements/News/Events are opened through their existing
# modal on the Announcements page (it already knows how to read these query
# params — see the deep-link block at the bottom of announcements.html);
# everything else links straight to a real page, anchor or "#svc-<id>" /
# "#forms-panel" section that already exists on that page.
# ---------------------------------------------------------------------------
def site_search(request):
    query = (request.GET.get('q') or '').strip()
    results = []

    if len(query) < 2:
        return JsonResponse({"results": results})

    MAX_PER_TYPE = 4
    MAX_TOTAL = 10
    q_lower = query.lower()

    static_pages = [
        {"label": "Home", "url": reverse('home'), "keywords": ["home", "homepage", "main"]},
        {"label": "Announcements", "url": reverse('announcement') + "#announcements", "keywords": ["announcement", "notice", "advisory"]},
        {"label": "News & Updates", "url": reverse('announcement') + "#news", "keywords": ["news", "update"]},
        {"label": "Events", "url": reverse('announcement') + "#events", "keywords": ["event", "calendar", "activity"]},
        {"label": "Photo Gallery", "url": reverse('gallery'), "keywords": ["gallery", "photo", "picture", "album"]},
        {"label": "Offices Directory", "url": reverse('offices'), "keywords": ["office", "offices", "department"]},
        {"label": "About Us", "url": reverse('about'), "keywords": ["about", "mission", "vision"]},
        {"label": "History", "url": reverse('history'), "keywords": ["history", "founding", "heritage"]},
        {"label": "Municipal Officials", "url": reverse('about') + "#officials", "keywords": ["official", "mayor", "councilor", "officials"]},
        {"label": "Barangays", "url": reverse('about') + "#barangays", "keywords": ["barangay", "barangays"]},
        {"label": "Contact Us", "url": reverse('contact'), "keywords": ["contact", "phone", "email", "address", "hotline"]},
        {"label": "Citizen Login", "url": reverse('login'), "keywords": ["login", "sign in"]},
        {"label": "Create Account", "url": reverse('signup'), "keywords": ["signup", "register", "create account"]},
    ]
    for p in static_pages:
        haystack = (p["label"] + " " + " ".join(p["keywords"])).lower()
        if q_lower in haystack:
            results.append({"label": p["label"], "type": "Page", "meta": "", "url": p["url"]})

    offices = Office.objects.filter(name__icontains=query).exclude(slug='lgu-super-admin').order_by('name')[:MAX_PER_TYPE]
    for o in offices:
        results.append({"label": o.name, "type": "Office", "meta": "Office", "url": reverse('offices:office_detail', args=[o.slug])})

    services = (Service.objects.filter(name__icontains=query, status='published')
                .select_related('office').order_by('name')[:MAX_PER_TYPE])
    for s in services:
        if not s.office:
            continue
        results.append({
            "label": s.name,
            "type": "Service",
            "meta": s.office.name,
            "url": f"{reverse('offices:office_detail', args=[s.office.slug])}#svc-{s.id}",
        })

    anns = (Announcement.objects.filter(title__icontains=query, status='published')
            .order_by('-date_posted', '-created_at')[:MAX_PER_TYPE])
    for a in anns:
        results.append({
            "label": a.title,
            "type": "Announcement",
            "meta": "Announcement",
            "url": f"{reverse('announcement')}?open_announcement={a.id}#announcements",
        })

    news_items = (NewsUpdate.objects.filter(title__icontains=query, status='published')
                  .order_by('-date_published', '-created_at')[:MAX_PER_TYPE])
    for n in news_items:
        results.append({
            "label": n.title,
            "type": "News",
            "meta": "News & Updates",
            "url": f"{reverse('announcement')}?open_news={n.id}#news",
        })

    events = (Event.objects.filter(title__icontains=query, status='published')
              .order_by('-event_date')[:MAX_PER_TYPE])
    for e in events:
        results.append({
            "label": e.title,
            "type": "Event",
            "meta": "Event",
            "url": f"{reverse('announcement')}?open_event={e.id}#events",
        })

    forms = (DownloadableForm.objects.filter(title__icontains=query, status='published')
             .select_related('office').order_by('title')[:MAX_PER_TYPE])
    for frm in forms:
        if not frm.office:
            continue
        results.append({
            "label": frm.title,
            "type": "Form",
            "meta": frm.office.name,
            "url": f"{reverse('offices:office_detail', args=[frm.office.slug])}#forms-panel",
        })

    photos = (Photo.objects.filter(title__icontains=query, status='published')
              .order_by('-created_at')[:MAX_PER_TYPE])
    for ph in photos:
        photo_url = reverse('gallery')
        if ph.album_id:
            photo_url += f"?album={ph.album_id}"
        results.append({"label": ph.title, "type": "Photo", "meta": "Gallery", "url": photo_url})

    return JsonResponse({"results": results[:MAX_TOTAL]})


# ---------------------------------------------------------------------------
# Citizen "My Account" / "Settings" popups — opened from the side panel on
# every public page (see base.html). Both are plain POSTs that redirect
# back to whatever page the citizen was on ("next"), same pattern as the
# Office Rep / Super Admin "My Account" pages, just scoped down to what a
# citizen actually has: their own User fields + CitizenProfile.mobile_number,
# a password change, and a read-only list of forms they've submitted online.
# ---------------------------------------------------------------------------
@login_required
def account_update(request):
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('home')

    if request.method == "POST":
        full_name = request.POST.get('full_name', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()

        if not full_name:
            messages.error(request, "Full name is required.")
        else:
            name_parts = full_name.split(' ', 1)
            request.user.first_name = name_parts[0]
            request.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            request.user.save()

            profile, _ = CitizenProfile.objects.get_or_create(user=request.user)
            profile.mobile_number = mobile_number
            profile.save()

            messages.success(request, "Account details updated.")

    return redirect(next_url)


@login_required
def account_change_password(request):
    next_url = request.POST.get('next') or request.GET.get('next') or reverse('home')

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

    return redirect(next_url)


@login_required
def account_submissions_partial(request):
    """Lazy-loaded fragment for the My Account popup's "My Form Submissions"
    list — fetched only when the popup is actually opened, so base.html
    doesn't have to run this query on every single page load."""
    submissions = list(
        FormSubmission.objects
        .filter(user=request.user)
        .select_related('form', 'form__office')
        .order_by('-submitted_at')[:20]
    )
    return render(request, "portal/_account_submissions.html", {"submissions": submissions})