"""Images shown in the public galleries (the Gallery page and each office's
Gallery section): gallery photos plus the pictures attached to published
announcements, news and events (posters).

Every item is a dict, so templates treat all of them the same way:
  kind ("photo" / "announcement" / "news" / "event"), kind_label, url,
  title, office, category, created, modified
"""
from .models import Announcement, Event, NewsUpdate

# (kind, label shown on the tile, model, image field)
CONTENT_SOURCES = [
    ("announcement", "Announcement", Announcement, "image"),
    ("news", "News", NewsUpdate, "image"),
    ("event", "Event", Event, "poster"),
]


def office_name(rep):
    return rep.office.name if rep and rep.office_id else "LGU Super Admin"


def photo_items(photos):
    """Published gallery photos (pass a Photo queryset that's already filtered)."""
    for p in photos.select_related("representative__office"):
        yield {"kind": "photo", "kind_label": "", "url": p.image.url, "title": p.title,
               "office": office_name(p.representative), "category": p.category,
               "created": p.created_at, "modified": p.last_updated}


def content_items(representative=None, only_kind=""):
    """Images of published announcements, news and events — all offices, or
    just one office's (representative=...). only_kind limits it to one kind."""
    for kind, label, model, field in CONTENT_SOURCES:
        if only_kind and only_kind != kind:
            continue
        base = model.public() if model is Announcement else model.objects.filter(status="published")
        qs = (base
              .exclude(**{field: ""}).exclude(**{f"{field}__isnull": True})
              .select_related("representative__office"))
        if representative is not None:
            qs = qs.filter(representative=representative)
        for obj in qs:
            yield {"kind": kind, "kind_label": label, "url": getattr(obj, field).url, "title": obj.title,
                   "office": office_name(obj.representative), "category": label,
                   "created": obj.created_at, "modified": obj.last_updated}