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
def tunga_map(context, height="78vh", show_signin=False):
    """Drop the interactive map into any template:

        {% load tungamap %}
        {% tunga_map %}
        {% tunga_map height="600px" show_signin=True %}
    """
    request = context["request"]
    user = request.user
    return {
        "height": height,
        "api_url": reverse("tungamap:places"),
        "csrf_token": get_token(request),
        "can_edit": can_edit(user),
        "signed_in": user.is_authenticated,
        "show_signin": show_signin and not user.is_authenticated,
        "login_url": resolve_url(settings.LOGIN_URL) + "?" + urlencode({"next": request.get_full_path()}),
        "categories": Place.CATEGORY_CHOICES,
        "barangays": [b for b, _ in Place.BARANGAY_CHOICES],
    }