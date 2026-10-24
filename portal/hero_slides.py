"""Home page banner slider (templates/portal/home.html).

Slide 1 is always the welcome banner. The other slides are chosen in
Super Admin → Homepage → "Banner Slider" (SiteContactInfo.hero_slider_*):
  - Automatic: the newest announcements and news & updates that have a
    picture (up to AUTO_MAX).
  - Chosen content: the posts the Super Admin ticked, from every office.
    Only content the public can still see is shown: published, announcements
    not past their expiration date, events not over yet. A ticked post that
    expires later simply drops out of the slider by itself.
A post without a picture uses the default banner photo.
"""
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

AUTO_MAX = 8          # slides in "Automatic"
PICK_MAX = 20         # most posts the Super Admin can tick

KIND_LABELS = {"announcement": "Announcement", "news": "News & Updates", "event": "Event"}


def _picture(obj, field):
    cover = getattr(obj, field, None)
    if cover:
        return cover.url
    for p in obj.extra_photos.all():
        if p.image:
            return p.image.url
    return ""


def eligible_content():
    """Every post the public can see right now, from all offices, newest
    first: [(key, kind, obj), …] with key = "kind:id"."""
    from office_dashboard.models import Announcement, NewsUpdate, Event
    today = timezone.localdate()
    sources = [
        ("announcement", Announcement.public(), "-date_posted"),
        ("news", NewsUpdate.objects.filter(status="published"), "-date_published"),
        ("event", Event.objects.filter(status="published").filter(
            Q(event_date__gte=today) | Q(event_date__isnull=True)), "event_date"),
    ]
    items = []
    for kind, qs, order in sources:
        qs = (qs.select_related("representative__office").prefetch_related("extra_photos")
                .order_by(order, "-last_updated", "-created_at"))
        for obj in qs:
            items.append((f"{kind}:{obj.pk}", kind, obj))
    return items


def slide_for(kind, obj):
    """The details one slide needs."""
    if kind == "announcement":
        day, text, image, param, tab = obj.date_posted, obj.subtitle, _picture(obj, "image"), "open_announcement", "announcements"
    elif kind == "news":
        day, text, image, param, tab = obj.date_published, obj.summary, _picture(obj, "image"), "open_news", "news"
    else:
        day, text, image, param, tab = obj.event_date, obj.description, _picture(obj, "poster"), "open_event", "events"
    rep = obj.representative
    return {
        "key": f"{kind}:{obj.pk}",
        "kind": kind,
        "kind_label": KIND_LABELS[kind],
        "title": obj.title,
        "text": (text or "")[:220],
        "category": obj.category or "General",
        "office": rep.office.name if rep and rep.office_id else "LGU Tunga",
        "image": image,                       # "" = use the default banner photo
        # an event without a date yet: None ("Date to be announced")
        "date": day if (day or kind == "event") else obj.created_at.date(),
        "url": f"{reverse('announcement')}?{param}={obj.pk}#{tab}",
    }


def hero_slides(info):
    """The post slides for the public home page (after the welcome slide)."""
    if getattr(info, "hero_slider_mode", "auto") == "pick":
        chosen = [k for k in (info.hero_slider_items or []) if isinstance(k, str)]
        if not chosen:
            return []
        by_key = {key: (kind, obj) for key, kind, obj in eligible_content()}
        # in the order the Super Admin arranged them; expired / unpublished ones are skipped
        return [slide_for(*by_key[k]) for k in chosen if k in by_key]
    slides = []
    for key, kind, obj in eligible_content():
        if kind == "event":
            continue
        s = slide_for(kind, obj)
        if s["image"]:
            slides.append(s)
    slides.sort(key=lambda s: s["date"], reverse=True)
    return slides[:AUTO_MAX]