"""{% site_theme %} — the Super Admin's website colors / fonts (Theme & Colors).
Put it in <head> AFTER all the CSS (templates/base.html). Writes nothing when
the theme was never changed, so the website keeps its original look."""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def site_theme():
    try:
        from admin_dashboard.models import SiteTheme
        from admin_dashboard.theme import theme_css
        theme = SiteTheme.objects.filter(pk=1).first()
        css, fonts_url = theme_css(theme)
    except Exception:
        return ""          # e.g. before the migration was run: keep the normal look
    return _tags(css, fonts_url)


@register.simple_tag
def dashboard_theme(which):
    """{% dashboard_theme "super_admin" %} / {% dashboard_theme "office_rep" %}
    in the dashboard base templates: the website theme, only when "Apply to
    ... dashboard" is ticked in Website Settings -> Theme & Colors."""
    try:
        from admin_dashboard.models import SiteTheme
        from admin_dashboard.theme import dashboard_css
        css, fonts_url = dashboard_css(SiteTheme.objects.filter(pk=1).first(), which)
    except Exception:
        return ""
    return _tags(css, fonts_url)


def _tags(css, fonts_url):
    out = ""
    if fonts_url:
        out += format_html('<link rel="preconnect" href="https://fonts.googleapis.com">'
                           '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                           '<link rel="stylesheet" href="{}">', fonts_url)
    if css:
        # css only contains checked #hex colors and fixed font names (theme.py)
        out += mark_safe('<style id="site-theme">' + css + '</style>')
    return mark_safe(out)