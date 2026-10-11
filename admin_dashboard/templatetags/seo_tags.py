"""{% load seo_tags %} — helpers for the <head> of the public pages
(Website Settings → SEO)."""
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


def _absolute(request, url):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    full = request.build_absolute_uri(url)
    # Render / DigitalOcean serve the site over https behind a proxy
    if not settings.DEBUG and full.startswith("http://"):
        full = "https://" + full[len("http://"):]
    return full


@register.simple_tag(takes_context=True)
def seo_image_url(context):
    """The picture shown when a link is shared on Facebook / Messenger:
    the SEO share image, else the homepage banner, else the LGU building."""
    request = context.get("request")
    info = context.get("site_contact")
    url = ""
    for field in ("share_image", "hero_banner"):
        f = getattr(info, field, None) if info else None
        if f:
            try:
                url = f.url
                break
            except Exception:
                pass
    return _absolute(request, url or static("images/lgu_bldg.jpeg")) if request else ""


@register.simple_tag(takes_context=True)
def page_url(context):
    request = context.get("request")
    return _absolute(request, request.path) if request else ""


@register.simple_tag(takes_context=True)
def abs_url(context, name):
    """Full address of a page, e.g. {% abs_url 'sitemap_xml' %} -> https://…/sitemap.xml"""
    from django.urls import reverse
    request = context.get("request")
    return _absolute(request, reverse(name)) if request else reverse(name)