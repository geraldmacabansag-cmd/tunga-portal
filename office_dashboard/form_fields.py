"""Shared by the Office Representative and Super Admin "Make Fillable"
builders, and by the public fill-out page, so all of them read and save
form fields (position + text style) the same way."""
import json
import re

from .models import FormField

STYLE_DEFAULTS = {
    "text_align": "left",
    "v_align": "bottom",
    "font_size": 0,          # 0 = auto (fits the box)
    "bold": False,
    "text_color": "#000000",
    "uppercase": False,
    "placeholder": "",
}

FIELD_KEYS = ["id", "label", "field_type", "required", "page_number",
              "x", "y", "width", "height", "order"] + list(STYLE_DEFAULTS)


def field_to_dict(f):
    return {key: getattr(f, key) for key in FIELD_KEYS}


def to_json(data):
    """JSON that is safe to put inside a <script> tag (a label containing
    "</script>" can't break the page)."""
    return json.dumps(data).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def fields_json(form):
    """JSON list of a form's fields, for the builder and the fill-out page."""
    return to_json([field_to_dict(f) for f in form.fields.all().order_by("page_number", "order", "id")])


def _choice(value, allowed, default):
    return value if value in allowed else default


def _clamp(value, low, high, default):
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def save_fields(form, incoming):
    """Saves the builder's field list. Fields that already exist are updated
    (not deleted and re-created), so answers people already submitted for
    them are kept. Returns how many fields were saved."""
    existing = {f.id: f for f in form.fields.all()}
    keep_ids = set()
    order = 0

    for data in incoming:
        label = (data.get("label") or "").strip()[:150]
        if not label:
            continue

        field = existing.get(data.get("id")) if isinstance(data.get("id"), int) else None
        if field is None:
            field = FormField(form=form)

        field.label = label
        field.field_type = _choice(data.get("field_type"), {"text", "date", "number", "checkbox"}, "text")
        field.required = bool(data.get("required", True))
        field.page_number = max(1, int(_clamp(data.get("page_number"), 1, 9999, 1)))
        field.x = _clamp(data.get("x"), 0, 1, 0)
        field.y = _clamp(data.get("y"), 0, 1, 0)
        field.width = _clamp(data.get("width"), 0.005, 1, 0.2)
        field.height = _clamp(data.get("height"), 0.005, 1, 0.03)
        field.order = order

        field.text_align = _choice(data.get("text_align"), {"left", "center", "right"}, "left")
        field.v_align = _choice(data.get("v_align"), {"bottom", "middle", "top"}, "bottom")
        field.font_size = int(_clamp(data.get("font_size"), 0, 72, 0))
        field.bold = bool(data.get("bold"))
        color = str(data.get("text_color") or "")
        field.text_color = color if re.fullmatch(r"#[0-9a-fA-F]{6}", color) else "#000000"
        field.uppercase = bool(data.get("uppercase"))
        field.placeholder = (data.get("placeholder") or "").strip()[:100]

        field.save()
        keep_ids.add(field.id)
        order += 1

    # Fields the user removed in the builder.
    form.fields.exclude(id__in=keep_ids).delete()
    return order