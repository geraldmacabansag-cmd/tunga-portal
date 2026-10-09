"""Extra photos of announcements, news posts and events (ContentPhoto).

Every add / edit form for these (Office Representative and Super Admin) has a
"More photos" field: <input type="file" name="photos" multiple>, and on edit a
"remove" toggle per existing photo (remove_photos = photo id). Call
save_content_photos(request, obj) right after the item itself is saved.
"""
from django import forms
from django.core.exceptions import ValidationError

from .models import Announcement, ContentPhoto, Event, NewsUpdate

MAX_PHOTOS = 30          # extra photos per item (the main image is separate)
MAX_MB = 5               # per photo


def _link(obj):
    if isinstance(obj, Announcement):
        return {"announcement": obj}
    if isinstance(obj, NewsUpdate):
        return {"news": obj}
    if isinstance(obj, Event):
        return {"event": obj}
    raise TypeError("Photos can only be added to announcements, news and events.")


def save_content_photos(request, obj):
    """Removes the photos ticked for removal and adds the newly chosen ones.
    Returns a list of problems (e.g. a file that isn't an image) to show the
    user; good photos are saved even when some others are rejected."""
    problems = []
    link = _link(obj)

    remove_ids = [i for i in request.POST.getlist("remove_photos") if str(i).isdigit()]
    if remove_ids:
        for p in ContentPhoto.objects.filter(pk__in=remove_ids, **link):
            if p.image:
                p.image.delete(save=False)
            p.delete()

    files = request.FILES.getlist("photos")
    if not files:
        return problems

    existing = ContentPhoto.objects.filter(**link)
    room = MAX_PHOTOS - existing.count()
    next_order = (existing.order_by("-order").values_list("order", flat=True).first() or 0) + 1
    checker = forms.ImageField()
    for f in files:
        if room <= 0:
            problems.append(f"Only {MAX_PHOTOS} extra photos can be added; the rest were skipped.")
            break
        if f.size > MAX_MB * 1024 * 1024:
            problems.append(f'"{f.name}" is larger than {MAX_MB} MB and was skipped.')
            continue
        try:
            checker.clean(f)
        except ValidationError:
            problems.append(f'"{f.name}" is not a picture (JPG, PNG or WEBP) and was skipped.')
            continue
        ContentPhoto.objects.create(image=f, order=next_order, **link)
        next_order += 1
        room -= 1
    return problems