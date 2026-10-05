import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

# A line is a bullet when it starts with one of these markers followed by a space.
_BULLET_RE = re.compile(r'^\s*(?:[-*•●▪◦·–—])\s+')


@register.filter
def charter_html(value):
    """Render office profile text (mission, vision, ...) with real bullets.

    - Lines starting with "-", "*", "•" etc. become <li> items (marker removed).
    - Plain lines mixed in with bullets stay as paragraphs.
    - Text with several lines and no markers is shown as a list (legacy behaviour).
    - A single plain line is shown as a paragraph.
    """
    if not value:
        return ''
    lines = [l.strip() for l in str(value).replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    lines = [l for l in lines if l]
    if not lines:
        return ''

    has_markers = any(_BULLET_RE.match(l) for l in lines)
    if not has_markers:
        if len(lines) == 1:
            return mark_safe('<p>%s</p>' % escape(lines[0]))
        return mark_safe('<ul>%s</ul>' % ''.join('<li>%s</li>' % escape(l) for l in lines))

    out, items = [], []

    def flush():
        if items:
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % escape(i) for i in items))
            items.clear()

    for l in lines:
        if _BULLET_RE.match(l):
            items.append(_BULLET_RE.sub('', l, count=1))
        else:
            flush()
            out.append('<p>%s</p>' % escape(l))
    flush()
    return mark_safe(''.join(out))