import json

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Place, PlaceImage

MAX_IMAGES = getattr(settings, "TUNGAMAP_MAX_IMAGES", 6)
MAX_IMAGE_MB = getattr(settings, "TUNGAMAP_MAX_IMAGE_MB", 8)
# Loose box around Leyte so a mis-click in the ocean or another province is caught
LAT_RANGE = (9.8, 12.6)
LNG_RANGE = (124.0, 125.9)


def is_site_super_admin(user):
    """The portal's Super Admin account (admin_dashboard.SuperAdmin)."""
    try:
        from admin_dashboard.models import SuperAdmin
    except ImportError:
        return False
    return SuperAdmin.objects.filter(user=user).exists()


def can_edit(user, action="add"):
    """The portal's Super Admin, or staff with the map permissions
    (or Django superusers), can manage the map."""
    if not user.is_authenticated:
        return False
    return user.has_perm(f"tungamap.{action}_place") or is_site_super_admin(user)


# ---------------------------------------------------------------- pages
def map_page(request):
    """A full page showing the map. Most sites can instead drop {% tunga_map %} into any template."""
    return render(request, "tungamap/map_page.html", {
        "base_template": getattr(settings, "TUNGAMAP_BASE_TEMPLATE", "tungamap/standalone.html"),
    })


# ---------------------------------------------------------------- helpers
def serialize(place, request):
    return {
        "id": place.id,
        "name": place.name,
        "category": place.category,
        "barangay": place.barangay,
        "description": place.description,
        "contact": place.contact,
        "lat": place.latitude,
        "lng": place.longitude,
        "published": place.is_published,
        "images": [{"id": im.id, "url": request.build_absolute_uri(im.image.url)} for im in place.images.all()],
    }


def error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def editor_required(view):
    def wrapped(request, *args, **kwargs):
        if request.method != "GET":
            if not request.user.is_authenticated:
                return error("Please sign in to edit the map.", 401)
            if not can_edit(request.user):
                return error("Your account isn't allowed to edit the map. Ask an administrator for access.", 403)
        return view(request, *args, **kwargs)
    return wrapped


def clean_fields(data):
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("Name is required.")
    category = data.get("category") or "other"
    if category not in dict(Place.CATEGORY_CHOICES):
        raise ValidationError("Choose a valid type.")
    barangay = data.get("barangay") or ""
    if barangay and barangay not in dict(Place.BARANGAY_CHOICES):
        raise ValidationError("Choose a valid barangay.")
    try:
        lat, lng = float(data.get("lat")), float(data.get("lng"))
    except (TypeError, ValueError):
        raise ValidationError("Pick a location on the map.")
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LNG_RANGE[0] <= lng <= LNG_RANGE[1]):
        raise ValidationError("That spot is outside Leyte. Move the pin into Tunga.")
    return {
        "name": name[:120],
        "category": category,
        "barangay": barangay,
        "description": (data.get("description") or "").strip()[:4000],
        "contact": (data.get("contact") or "").strip()[:120],
        "latitude": lat,
        "longitude": lng,
        "is_published": data.get("published", "true") != "false",
    }


def clean_images(files, already):
    files = list(files)
    if already + len(files) > MAX_IMAGES:
        raise ValidationError(f"A place can have at most {MAX_IMAGES} photos.")
    field = forms.ImageField()
    for f in files:
        if f.size > MAX_IMAGE_MB * 1024 * 1024:
            raise ValidationError(f"“{f.name}” is larger than {MAX_IMAGE_MB} MB.")
        try:
            field.clean(f)  # Pillow checks it's a real image
        except ValidationError:
            raise ValidationError(f"“{f.name}” isn't a valid image (use JPG, PNG or WEBP).")
    return files


def visible_places(request):
    qs = Place.objects.prefetch_related("images")
    return qs if can_edit(request.user) else qs.filter(is_published=True)


# ---------------------------------------------------------------- API
@editor_required
@require_http_methods(["GET", "POST"])
def places(request):
    if request.method == "GET":
        qs = visible_places(request)
        if cat := request.GET.get("category"):
            qs = qs.filter(category=cat)
        if q := (request.GET.get("q") or "").strip():
            for word in q.split():
                qs = qs.filter(Q(name__icontains=word) | Q(barangay__icontains=word) | Q(description__icontains=word))
        return JsonResponse({"places": [serialize(p, request) for p in qs], "canEdit": can_edit(request.user)})

    # POST: create
    try:
        fields = clean_fields(request.POST)
        files = clean_images(request.FILES.getlist("images"), 0)
    except ValidationError as e:
        return error(e.messages[0])
    with transaction.atomic():
        place = Place.objects.create(created_by=request.user, **fields)
        for i, f in enumerate(files):
            PlaceImage.objects.create(place=place, image=f, order=i)
    return JsonResponse(serialize(place, request), status=201)


@editor_required
@require_http_methods(["GET", "POST", "DELETE"])
def place_detail(request, pk):
    place = get_object_or_404(visible_places(request), pk=pk)

    if request.method == "GET":
        return JsonResponse(serialize(place, request))

    if request.method == "DELETE":
        if not can_edit(request.user, "delete"):
            return error("Your account isn't allowed to delete places.", 403)
        place.delete()
        return JsonResponse({"ok": True})

    # POST: update (multipart, so POST rather than PUT)
    if not can_edit(request.user, "change"):
        return error("Your account isn't allowed to change places.", 403)
    try:
        keep = set(int(i) for i in json.loads(request.POST.get("keepImages") or "[]"))
    except (ValueError, TypeError):
        return error("Invalid photo list.")
    try:
        fields = clean_fields(request.POST)
        kept = [im for im in place.images.all() if im.id in keep]
        files = clean_images(request.FILES.getlist("images"), len(kept))
    except ValidationError as e:
        return error(e.messages[0])
    with transaction.atomic():
        for k, v in fields.items():
            setattr(place, k, v)
        place.save()
        for im in place.images.all():
            if im.id not in keep:
                im.delete()  # signal removes the file
        start = len(kept)
        for i, f in enumerate(files):
            PlaceImage.objects.create(place=place, image=f, order=start + i)
    place = Place.objects.prefetch_related("images").get(pk=place.pk)
    return JsonResponse(serialize(place, request))