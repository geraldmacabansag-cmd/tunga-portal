"""{{ page.content|legal_text }} — turns the simple writing format of the
legal pages (Privacy Policy, Terms of Use, Accessibility Statement) into
safe HTML:

    ## Heading      → <h2>
    - item          → bullet list
    empty line      → new paragraph
    other lines     → text (a single line break stays a line break)

Everything typed is escaped first, so no HTML or scripts can be added.
"""
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def legal_text(value):
    html, para, items = [], [], []

    def flush_para():
        if para:
            html.append("<p>" + "<br>".join(para) + "</p>")
            para.clear()

    def flush_list():
        if items:
            html.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
            items.clear()

    for raw in (value or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            flush_para(); flush_list()
        elif line.startswith("## ") or line.startswith("# "):
            flush_para(); flush_list()
            html.append("<h2>" + escape(line.lstrip("#").strip()) + "</h2>")
        elif line.startswith("- ") or line.startswith("• "):
            flush_para()
            items.append(escape(line[2:].strip()))
        else:
            flush_list()
            para.append(escape(line))
    flush_para(); flush_list()
    return mark_safe("\n".join(html))