"""Helpers for the office's Organizational Chart (OrgChartNode)."""
from .models import OrgChartNode


def build_tree(office):
    """All boxes of the office's chart, arranged as a tree.
    Returns (roots, nodes): roots are the top boxes; every node gets .kids."""
    nodes = list(OrgChartNode.objects.filter(office=office).order_by("order", "id"))
    by_id = {n.id: n for n in nodes}
    for n in nodes:
        n.kids = []
    roots = []
    for n in nodes:
        parent = by_id.get(n.parent_id)
        (parent.kids if parent else roots).append(n)
    return roots, nodes


def descendant_ids(node, nodes):
    """Ids of every box under `node` (children, grandchildren…)."""
    kids_of = {}
    for n in nodes:
        kids_of.setdefault(n.parent_id, []).append(n.id)
    found, stack = set(), [node.id]
    while stack:
        for kid in kids_of.get(stack.pop(), []):
            if kid not in found:
                found.add(kid)
                stack.append(kid)
    return found


def parent_choices(nodes, exclude=None):
    """(id, label) for the "Reports to" dropdown, indented by level. A box
    can't report to itself or to anyone under it."""
    blocked = set()
    if exclude is not None:
        blocked = {exclude.id} | descendant_ids(exclude, nodes)
    roots = [n for n in nodes if n.parent_id is None or n.parent_id not in {m.id for m in nodes}]
    kids_of = {}
    for n in nodes:
        kids_of.setdefault(n.parent_id, []).append(n)
    out = []

    def walk(n, depth):
        if n.id in blocked:
            return
        label = n.name + (f" — {n.position}" if n.position else "")
        if n.kind == OrgChartNode.KIND_SECTION:
            label = f"[Section] {n.name}"
        out.append((n.id, " " * depth + label))
        for kid in kids_of.get(n.id, []):
            walk(kid, depth + 1)

    for r in roots:
        walk(r, 0)
    return out


def next_order(office, parent_id):
    last = (OrgChartNode.objects.filter(office=office, parent_id=parent_id)
            .order_by("-order").values_list("order", flat=True).first())
    return (last or 0) + 1


# ---------------------------------------------------------------------------
# Box style (colors, photo shape, size…) — set in the editor
# ---------------------------------------------------------------------------
import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_LINE = "#9aa5b8"
DEFAULT_COLORS = {
    OrgChartNode.KIND_PERSON:  {"border": "#1f2a44", "fill": "#1f2a44", "text": "#ffffff"},
    OrgChartNode.KIND_SECTION: {"border": "#1f2a44", "fill": "#ffffff", "text": "#1f2a44"},
}
STYLE_CHOICES = {
    "shape": {"circle", "rounded", "square", "none"},
    "line_style": {"solid", "dashed", "dotted"},
    "case": {"upper", "normal"},
}
STYLE_DEFAULTS = {"shape": "circle", "line_style": "solid", "case": "upper"}
# box width in pixels, set by dragging the box's corner on the chart
WIDTH_MIN, WIDTH_MAX = 80, 420
# keys that make sense on a box of the other kind (person <-> section)
SHARED_KEYS = {"border", "line", "line_style", "case"}


def clean_style(post, kind):
    """The style chosen in the editor, keeping only values that differ from
    the default look (so an untouched box keeps following the defaults)."""
    style = {}
    for key, default in DEFAULT_COLORS[kind].items():
        value = (post.get(f"style_{key}") or "").strip().lower()
        if HEX.match(value) and value != default:
            style[key] = value
    line = (post.get("style_line") or "").strip().lower()
    if HEX.match(line) and line != DEFAULT_LINE:
        style["line"] = line
    for key, allowed in STYLE_CHOICES.items():
        value = post.get(f"style_{key}")
        if value in allowed and value != STYLE_DEFAULTS[key]:
            style[key] = value
    w = clean_width(post.get("style_w"))
    if w:
        style["w"] = w
    if kind == OrgChartNode.KIND_SECTION:
        style.pop("shape", None)
    return style


def clean_width(value):
    """A box width from the resize handle, kept within sensible limits (None if empty/bad)."""
    try:
        return max(WIDTH_MIN, min(WIDTH_MAX, int(float(value))))
    except (TypeError, ValueError):
        return None


def style_for(target, style, kind):
    """The style to copy onto another box (used by "apply to everyone under
    it / whole chart"). Fill and text colors only go to boxes of the same kind,
    so sections don't turn dark when people's name boxes are dark."""
    if target.kind == kind:
        return dict(style)
    return {k: v for k, v in style.items() if k in SHARED_KEYS}