"""Burns a citizen's typed answers directly into a copy of the office's PDF.

Why this exists instead of PDF "FreeText" annotations: an annotation is only a
note that sits on top of the page, and many phone PDF viewers (the built-in
Android/iOS previews, Google Drive's viewer, in-app browsers) don't draw
annotations that lack a pre-rendered appearance — the person saves the file and
finds their answers missing. Here the text is written into the page's own
content stream, exactly like the printed text, so every viewer shows it.

Only pypdf is used (already in requirements) — no new dependency.
"""
import io
from datetime import datetime

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

# Advance widths (1/1000 em) of Helvetica for the Windows-1252 characters
# 32..255, used to shrink long answers so they stay inside their box.
_HELV = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 761,
    556, 556, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 556, 611, 556,
    556, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 556, 500, 667,
    278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333,
    400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
    667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278,
    722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
    556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500,
]


def _encode(text):
    """Text -> Windows-1252 bytes (what a standard Helvetica font shows).
    Characters outside that set (e.g. emoji) become '?' instead of crashing."""
    return text.encode("cp1252", errors="replace")


def _text_width(raw, size):
    return sum(_HELV[b - 32] if b >= 32 else 0 for b in raw) * size / 1000.0


def _display_value(field_type, value):
    value = (value or "").strip()
    if field_type == "date" and value:
        try:
            d = datetime.strptime(value[:10], "%Y-%m-%d")
            return "%s %d, %d" % (d.strftime("%b"), d.day, d.year)
        except ValueError:
            return value
    return value


def _page_geometry(page):
    """Returns (left, bottom, width, height, rotation) of the page exactly as
    a viewer shows it: pdf.js (and every other viewer) uses the CropBox when
    there is one, and the field positions were stored as fractions of that
    visible area — not of the larger MediaBox."""
    box = page.cropbox
    left, bottom = float(box.left), float(box.bottom)
    width, height = float(box.width), float(box.height)
    rotation = int(page.get("/Rotate", 0) or 0) % 360
    return left, bottom, width, height, rotation


def _display_to_page_matrix(left, bottom, width, height, rotation):
    """Matrix that maps 'as displayed' coordinates (origin bottom-left of the
    page as the person sees it, y up) onto the page's own unrotated space, so
    answers land on the right spot even on scanned/rotated forms."""
    if rotation == 90:
        a, b, c, d, e, f = 0, 1, -1, 0, width, 0
    elif rotation == 180:
        a, b, c, d, e, f = -1, 0, 0, -1, width, height
    elif rotation == 270:
        a, b, c, d, e, f = 0, -1, 1, 0, 0, height
    else:
        a, b, c, d, e, f = 1, 0, 0, 1, 0, 0
    return a, b, c, d, e + left, f + bottom


def _rgb(hex_color):
    """'#1d3fa6' -> (r, g, b) as 0..1 floats; anything invalid -> black."""
    try:
        h = (hex_color or "").lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) if len(h) == 6 else (0, 0, 0)
    except ValueError:
        return (0, 0, 0)


def _num(n):
    return ("%.3f" % n).rstrip("0").rstrip(".") or "0"


def _build_page_stream(fields, values_by_field, left, bottom, width, height, rotation):
    disp_w, disp_h = (height, width) if rotation in (90, 270) else (width, height)
    ops = []
    for f in fields:
        value = values_by_field.get(f.id, "")
        x0 = f.x * disp_w
        box_w = max(f.width * disp_w, 4)
        box_h = max(f.height * disp_h, 4)
        y0 = disp_h - (f.y * disp_h) - box_h  # bottom edge, y up

        if f.field_type == "checkbox":
            if not value:
                continue
            inset = min(box_w, box_h) * 0.18
            line = max(0.8, min(box_w, box_h) * 0.12)
            ops.append("q 0 0 0 RG %s w 1 J" % _num(line))
            ops.append("%s %s m %s %s l S" % (
                _num(x0 + inset), _num(y0 + inset), _num(x0 + box_w - inset), _num(y0 + box_h - inset)))
            ops.append("%s %s m %s %s l S Q" % (
                _num(x0 + inset), _num(y0 + box_h - inset), _num(x0 + box_w - inset), _num(y0 + inset)))
            continue

        text = _display_value(f.field_type, value)
        if not text:
            continue
        if getattr(f, "uppercase", False):
            text = text.upper()
        raw = _encode(text.replace("\r", " ").replace("\n", " "))

        pad = min(2.0, box_w * 0.05)
        avail = max(box_w - 2 * pad, 2)
        chosen = getattr(f, "font_size", 0) or 0
        # Chosen size, or "auto" = fit the box height (max 14pt) — same rule
        # the builder preview and the fill-out page use.
        size = float(chosen) if chosen else max(5.0, min(14.0, box_h * 0.72))
        # Shrink (down to a floor) so the whole answer fits on its line.
        width_at_size = _text_width(raw, size)
        if width_at_size > avail:
            size = max(4.0, size * avail / width_at_size)
        text_w = _text_width(raw, size)

        align = getattr(f, "text_align", "left")
        if align == "center":
            tx = x0 + (box_w - text_w) / 2.0
        elif align == "right":
            tx = x0 + box_w - pad - text_w
        else:
            tx = x0 + pad

        v_align = getattr(f, "v_align", "bottom")
        if v_align == "top":
            baseline = y0 + box_h - pad - size * 0.75
        elif v_align == "middle":
            baseline = y0 + (box_h - size * 0.72) / 2.0
        else:  # bottom: sits just above the box's bottom edge (the printed line)
            baseline = y0 + max(size * 0.22, 1.0)

        r, g, b = _rgb(getattr(f, "text_color", "#000000"))
        color = "%s %s %s" % (_num(r), _num(g), _num(b))
        # Bold = fill + thin outline in the same color (keeps Helvetica's
        # widths, so centering/right-align stay exact).
        # (Tr is always set: it carries over to the next field otherwise.)
        style = ("2 Tr %s w %s RG " % (_num(size * 0.035), color)) if getattr(f, "bold", False) else "0 Tr "
        ops.append("BT /TungaHelv %s Tf %s rg %s%s %s Td <%s> Tj ET" % (
            _num(size), color, style, _num(tx), _num(baseline), raw.hex()))

    if not ops:
        return None
    a, b, c, d, e, f = _display_to_page_matrix(left, bottom, width, height, rotation)
    matrix = " ".join(_num(n) for n in (a, b, c, d, e, f))
    return "q %s cm\n%s\nQ" % (matrix, "\n".join(ops))


def stamp_pdf(source_bytes, fields, values_by_field):
    """Returns the PDF bytes of the original form with every answer written
    onto it. `fields` need .id/.page_number/.field_type/.x/.y/.width/.height."""
    reader = PdfReader(io.BytesIO(source_bytes))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass

    writer = PdfWriter()
    writer.append(reader)

    by_page = {}
    for f in fields:
        by_page.setdefault(f.page_number, []).append(f)

    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    })

    for page_number, page_fields in by_page.items():
        index = page_number - 1
        if index < 0 or index >= len(writer.pages):
            continue
        page = writer.pages[index]
        left, bottom, width, height, rotation = _page_geometry(page)
        stream_text = _build_page_stream(page_fields, values_by_field, left, bottom, width, height, rotation)
        if not stream_text:
            continue

        overlay = PageObject.create_blank_page(width=max(width, 1), height=max(height, 1))
        stream = DecodedStreamObject()
        stream.set_data(stream_text.encode("latin-1"))
        overlay[NameObject("/Contents")] = writer._add_object(stream)
        overlay[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/TungaHelv"): writer._add_object(font)}),
        })
        # merge_page wraps the original content in q/Q first, so a source
        # page that leaves its graphics state changed can't distort the text.
        page.merge_page(overlay)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()