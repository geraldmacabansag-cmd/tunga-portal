from .models import SiteContactInfo, SuperAdmin


def site_contact_info(request):
    return {"site_contact": SiteContactInfo.get_solo()}

def is_super_admin(request):
    if not request.user.is_authenticated:
        return {"is_super_admin": False, "user_photo_url": ""}
    from portal.profile_photo import photo_url
    return {
        "is_super_admin": SuperAdmin.objects.filter(user=request.user).exists(),
        # the person's profile picture (same as their dashboard picture for
        # office reps and the Super Admin) — shown in the public site header
        # and side panel; "" = show their initial instead
        "user_photo_url": photo_url(request.user),
    }

def nav_offices(request):
    # Powers the "Offices" dropdown in the public site's navbar (base.html)
    # on every page, so it has to live in a context processor rather than
    # being passed in from each view individually. "Active" here matches
    # the same rule used for the "From Our Offices" tab on the Announcements
    # page: visible to the public AND currently has a representative whose
    # account is active — a visible office with no one assigned yet, or
    # whose rep account is disabled, doesn't show up here either.
    from django.urls import reverse
    from offices.models import Office

    offices_list = list(
        Office.objects
        .exclude(slug="lgu-super-admin")
        .filter(is_visible=True, representative__isnull=False, representative__user__is_active=True)
        .order_by("display_order", "name")
    )
    for o in offices_list:
        o.nav_url = reverse('offices:office_detail', args=[o.slug])
    return {"nav_offices": offices_list}


def public_notifications(request):
    """Feeds the "Notifications" list in the public site's side panel
    (base.html) for signed-in citizens: the newest published announcements,
    news and events from the last 30 days, merged newest-first. Which ones a
    person has already seen is remembered in their browser (localStorage),
    so nothing here needs a database table."""
    if not request.user.is_authenticated:
        return {"public_notifications": []}

    from django.urls import reverse
    from django.utils import timezone
    from office_dashboard.models import Announcement, Event, NewsUpdate

    cutoff = timezone.now() - timezone.timedelta(days=30)
    page = reverse('announcement')
    items = []

    def office_name(obj):
        try:
            return obj.representative.office.name
        except Exception:
            return ""

    for a in (Announcement.public().filter(created_at__gte=cutoff)
              .select_related('representative__office').order_by('-created_at')[:10]):
        items.append({
            "key": f"a{a.pk}", "kind": "announcement", "label": "Announcement",
            "icon": "fa-solid fa-bullhorn", "title": a.title, "office": office_name(a),
            "when": a.created_at, "url": f"{page}?open_announcement={a.pk}#announcements",
            "urgent": a.priority in ("High", "Urgent"),
        })

    for n in (NewsUpdate.objects.filter(status='published', created_at__gte=cutoff)
              .select_related('representative__office').order_by('-created_at')[:10]):
        items.append({
            "key": f"n{n.pk}", "kind": "news", "label": "News",
            "icon": "fa-regular fa-newspaper", "title": n.title, "office": office_name(n),
            "when": n.created_at, "url": f"{page}?open_news={n.pk}#news", "urgent": False,
        })

    for e in (Event.objects.filter(status='published', created_at__gte=cutoff)
              .select_related('representative__office').order_by('-created_at')[:10]):
        items.append({
            "key": f"e{e.pk}", "kind": "event", "label": "Event",
            "icon": "fa-regular fa-calendar", "title": e.title, "office": office_name(e),
            "when": e.created_at, "url": f"{page}?open_event={e.pk}#events", "urgent": False,
            "event_date": e.event_date,
        })

    # The office updated the status of a form this person sent online
    # (office_dashboard/submissions.py). A new status = a new notification.
    from office_dashboard.models import FormSubmission
    from office_dashboard.submissions import STATUS_INFO
    for s in (FormSubmission.objects.filter(user=request.user, status_updated_at__gte=cutoff)
              .exclude(status="submitted").select_related('form__office').order_by('-status_updated_at')[:10]):
        info = STATUS_INFO.get(s.status, STATUS_INFO["submitted"])
        items.append({
            "key": f"s{s.pk}-{s.status}-{int(s.status_updated_at.timestamp())}",
            "kind": "submission-declined" if s.status == "declined" else "submission",
            "label": "Your form: " + info["label"],
            "icon": info["icon"], "title": s.form.title,
            "office": s.form.office.name if s.form.office else "",
            "when": s.status_updated_at, "url": "#my-submissions",
            "urgent": False,
        })

    items.sort(key=lambda i: i["when"], reverse=True)
    return {"public_notifications": items[:15]}