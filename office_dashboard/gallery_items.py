"""Images shown in the public galleries (the Gallery page and each office's
Gallery section): gallery photos plus the pictures attached to published
announcements, news and events (posters).

Every item is a dict, so templates treat all of them the same way:
  kind ("photo" / "announcement" / "news" / "event"), id (of the photo or of
  the announcement / news / event it belongs to), kind_label, url,
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
        yield {"kind": "photo", "id": p.pk, "kind_label": "", "url": p.image.url, "title": p.title,
               "office": office_name(p.representative), "category": p.category,
               "created": p.created_at, "modified": p.last_updated}


def content_items(representative=None, only_kind=""):
    """Images of published announcements, news and events — all offices, or
    just one office's (representative=...). only_kind limits it to one kind.
    Includes each item's main image / poster AND its extra photos ("More
    photos"), so every photo uploaded with the content shows in the gallery."""
    for kind, label, model, field in CONTENT_SOURCES:
        if only_kind and only_kind != kind:
            continue
        base = model.public() if model is Announcement else model.objects.filter(status="published")
        qs = base.select_related("representative__office").prefetch_related("extra_photos")
        if representative is not None:
            qs = qs.filter(representative=representative)
        for obj in qs:
            common = {"kind": kind, "id": obj.pk, "kind_label": label, "title": obj.title,
                      "office": office_name(obj.representative), "category": label,
                      "modified": obj.last_updated}
            cover = getattr(obj, field)
            if cover:
                yield {**common, "url": cover.url, "created": obj.created_at}
            for p in obj.extra_photos.all():
                if p.image:
                    yield {**common, "url": p.image.url, "created": p.created_at}