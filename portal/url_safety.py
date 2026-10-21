"""Checks links that people type in (office social media, footer social
media, Quick Links) before they are saved or shown on the website.

Only real web addresses are allowed: https://..., http://..., or (where
`allow_relative` is on) an address on this site such as /offices/. Anything
else — for example "javascript:..." — could run code when a visitor clicks
the link, so it is refused.
"""
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

_validate = URLValidator(schemes=["http", "https"])


def clean_link(value, allow_relative=False):
    """(cleaned link, error message or None). An empty box is fine ("")."""
    value = (value or "").strip()
    if not value:
        return "", None
    if allow_relative and value.startswith("/") and not value.startswith("//"):
        return value, None
    if "://" not in value and not value.lower().startswith(("javascript:", "data:", "vbscript:")):
        value = "https://" + value          # "facebook.com/tunga" -> https://facebook.com/tunga
    try:
        _validate(value)
    except ValidationError:
        return "", f'"{value[:80]}" is not a valid web address. Use a link that starts with https://'
    return value, None


def is_safe_link(value, allow_relative=False):
    """True for links that may be put in an <a href> on the website."""
    value = (value or "").strip()
    if allow_relative and value.startswith("/") and not value.startswith("//"):
        return True
    return value.lower().startswith(("https://", "http://"))