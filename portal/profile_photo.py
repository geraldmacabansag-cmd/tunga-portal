"""Profile picture of the signed-in person, shared by the public site and the dashboards.

- Super Admin            -> SuperAdmin.photo           (same photo as the Super Admin dashboard)
- Office Representative  -> OfficeRepresentative.photo (same photo as the Office dashboard)
- Citizen                -> CitizenProfile.photo

So changing the picture on the public site (side panel -> Account) also
changes it on the dashboard, and the other way around.
"""
from django.core.files.images import get_image_dimensions

MAX_PHOTO_MB = 5


def photo_owner(user):
    """The record that holds this person's picture (it has a .photo field)."""
    from admin_dashboard.models import SuperAdmin
    from office_dashboard.models import OfficeRepresentative
    from .models import CitizenProfile

    sa = SuperAdmin.objects.filter(user=user).first()
    if sa:
        return sa
    rep = OfficeRepresentative.objects.filter(user=user).first()
    if rep:
        return rep
    profile, _ = CitizenProfile.objects.get_or_create(user=user)
    return profile


def photo_url(user):
    """Address of the person's picture, or "" when there is none."""
    if not user.is_authenticated:
        return ""
    owner = photo_owner(user)
    try:
        return owner.photo.url if owner.photo else ""
    except Exception:
        return ""


def check_photo(upload):
    """An error message for a bad upload, or None when it's fine."""
    if upload.size > MAX_PHOTO_MB * 1024 * 1024:
        return f"The photo is too big. Please choose one under {MAX_PHOTO_MB} MB."
    try:
        w, h = get_image_dimensions(upload)
    except Exception:
        w = h = None
    upload.seek(0)
    if not w or not h:
        return "That file is not a picture. Please choose a JPG, PNG or WEBP image."
    return None