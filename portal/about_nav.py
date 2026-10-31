"""Which sections the public About Us page shows, in page order. Used by the
page itself (about view) and by the "About" dropdown of the navbar, so the
optional sections (Awards & Recognition, Places to Visit, …) appear in the
menu as soon as the Super Admin adds content to them."""


def about_flags():
    from admin_dashboard.models import AboutPageContent, AboutItem
    c = AboutPageContent.get_solo()
    sections = set(AboutItem.objects.order_by().values_list("section", flat=True).distinct())
    has_docs = AboutItem.objects.filter(section="document").exclude(file="").exists()
    return {
        "location": bool(c.location_intro or c.location_neighbors or c.location_distance or c.location_terrain),
        "transparency": has_docs,
        "seal": bool(c.seal_intro or "seal" in sections),
        "fiesta": bool(c.fiesta_title or "fiesta" in sections),
        "places": "place" in sections,
        "agenda": "goal" in sections,
        "awards": "award" in sections,
        "hymn": bool(c.hymn_title),
        "visit": bool(c.visit_hours.strip() or c.visit_directions.strip()),
    }


# (anchor, menu label, flag key — None = always in the menu), in page order
ABOUT_MENU = [
    ("", "About Us", None),
    ("location", "Location", "location"),
    ("history", "History", None),
    ("seal", "The Official Seal", "seal"),
    ("fiesta", "Fiesta & Culture", "fiesta"),
    ("places", "Places to Visit", "places"),
    ("officials", "Municipal Officials", None),
    ("agenda", "Development Agenda", "agenda"),
    ("awards", "Awards & Recognition", "awards"),
    ("hymn", "Municipal Hymn", "hymn"),
    ("transparency", "Full Disclosure", "transparency"),
    ("barangays", "Barangays", None),
    ("visit", "Visit Us", "visit"),
]


def about_menu():
    """[(anchor, label)] for the navbar dropdown."""
    try:
        flags = about_flags()
    except Exception:          # e.g. tables not created yet
        flags = {}
    return [(a, label) for a, label, key in ABOUT_MENU if key is None or flags.get(key)]