from django import template
from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.http import urlencode

from ..models import Place
from ..views import can_edit

register = template.Library()


@register.inclusion_tag("tungamap/_map.html", takes_context=True)
def tunga_map(context, height="78vh", show_signin=False, public=False, compact=False, hall=False, start=""):
    """Drop the interactive map into any template:

        {% load tungamap %}
        {% tunga_map %}
        {% tunga_map height="600px" show_signin=True %}
        {% tunga_map public=True compact=True hall=True start="hall" %}   (Contact Us)

    public=True   view only, for citizens: no editing (even for staff), only
                  places the municipality published, no OpenStreetMap extras
    compact=True  for small boxes: the list opens as a drawer over the map
    hall=True     show the Municipal Hall pin (Website Settings → Map location)
    start="hall"  open the map on the Municipal Hall
    """
    request = context["request"]
    user = request.user
    hall_info = None
    if hall:
        try:
            from admin_dashboard.models import SiteContactInfo
            info = SiteContactInfo.get_solo()
            hall_info = {
                "lat": f"{info.map_lat:.6f}", "lng": f"{info.map_lng:.6f}",
                "name": info.map_place_name or "Municipal Hall of Tunga",
                "address": info.address or "Tunga, Leyte",
            }
        except Exception:
            hall_info = None
    return {
        "height": height,
        "public": public,
        "compact": compact,
        "hall": hall_info,
        "start": start,
        "api_url": reverse("tungamap:places"),
        "csrf_token": get_token(request),
        "can_edit": (not public) and can_edit(user),
        "signed_in": user.is_authenticated,
        "show_signin": show_signin and not user.is_authenticated,
        "login_url": resolve_url(settings.LOGIN_URL) + "?" + urlencode({"next": request.get_full_path()}),
        "categories": Place.CATEGORY_CHOICES,
        "barangays": [b for b, _ in Place.BARANGAY_CHOICES],
    }