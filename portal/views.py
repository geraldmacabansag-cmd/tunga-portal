import calendar as cal_module
from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from .models import CitizenProfile
from office_dashboard.models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo
from admin_dashboard.models import SuperAdmin, EmergencyContact, QuickLink
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from .models import CitizenProfile, EmailOTP
from .otp_utils import send_signup_otp
from django.http import JsonResponse
from .otp_utils import send_signup_otp, send_password_reset_otp
from offices.models import Office

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
        .order_by('-created_at')[:8]
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
    news_grid_items = all_news[3:]

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

    # ---- Events tab sidebar: the small month calendar --------------------
    # ?events_month=YYYY-MM lets the "‹ ›" arrows browse other months with a
    # normal page reload (no JS/AJAX needed). Falls back to the current
    # month, and to the current month again if the param is malformed.
    events_month_param = request.GET.get('events_month', '').strip()
    try:
        cal_year, cal_month = [int(part) for part in events_month_param.split('-')]
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

    prev_year, prev_month = (cal_year - 1, 12) if cal_month == 1 else (cal_year, cal_month - 1)
    next_year, next_month = (cal_year + 1, 1) if cal_month == 12 else (cal_year, cal_month + 1)

    return render(request, "portal/announcements.html", {
        "announcements": announcements,
        "news_items": news_items,
        "all_announcements": all_announcements,
        "announcement_categories": announcement_categories,
        "news_main_story": news_main_story,
        "news_side_stories": news_side_stories,
        "news_grid_items": news_grid_items,
        "featured_event": featured_event,
        "upcoming_events": upcoming_events,
        "past_events": past_events,
        "calendar_weeks": calendar_weeks,
        "calendar_month_label": date(cal_year, cal_month, 1).strftime("%B %Y"),
        "calendar_prev_param": f"{prev_year:04d}-{prev_month:02d}",
        "calendar_next_param": f"{next_year:04d}-{next_month:02d}",
        "calendar_only_events": calendar_only_events,
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


def offices(request):
    office_list = (
        Office.objects
        .exclude(slug="lgu-super-admin")
        .filter(is_visible=True)
        .order_by("name")
    )
    for office in office_list:
        icon, color, icon_image = OFFICE_CARD_STYLE.get(office.slug, OFFICE_CARD_DEFAULT)
        office.card_icon = icon
        office.card_color = color
        office.card_image = icon_image

    return render(request, "offices/offices.html", {
        "office_list": office_list,
    })

def about(request):
    return render(request, "portal/about.html")

def history(request):
    return render(request, "portal/history.html")

def contact(request):
    return render(request, "portal/contactus.html")

def signup(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        mobile_number = request.POST.get("mobile_number", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([first_name, last_name, email, password, confirm_password]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, "account/signup.html")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "account/signup.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
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