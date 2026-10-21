"""{{ link|safe_href }} — the link itself when it is a real web address
(https://…, http://… or an address on this site like /offices/), otherwise
"#". Used for links typed in by the Super Admin (footer social media, Quick
Links) so an unsafe "javascript:" link can never reach a visitor.
See portal/url_safety.py."""
from django import template

from portal.url_safety import is_safe_link

register = template.Library()


@register.filter
def safe_href(value):
    return value if is_safe_link(value, allow_relative=True) else "#"