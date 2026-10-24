"""The newer About Us sections (Super Admin → About Us Page, one tab each).

TABS            the tab key, its label and icon (in the order of the tabs)
TEXT_FIELDS     the AboutPageContent fields saved by each tab's text form
ITEM_SECTIONS   the list entries (AboutItem) of a tab: which fields the
                Add / Edit window shows and their labels

Every section is optional: on the public About Us page it only shows once it
has content (portal/views.py, about()).
"""

TABS = [
    ("location", "Location", "fa-solid fa-map-pin"),
    ("transparency", "Full Disclosure", "fa-solid fa-file-invoice"),
    ("seal", "Official Seal", "fa-solid fa-certificate"),
    ("fiesta", "Fiesta & Culture", "fa-solid fa-masks-theater"),
    ("places", "Places to Visit", "fa-solid fa-camera-retro"),
    ("agenda", "Development Agenda", "fa-solid fa-bullseye"),
    ("awards", "Awards", "fa-solid fa-trophy"),
    ("hymn", "Hymn", "fa-solid fa-music"),
    ("visit", "Visit Us", "fa-solid fa-door-open"),
]

TEXT_FIELDS = {
    "location": ["location_intro", "location_neighbors", "location_distance", "location_terrain"],
    "transparency": ["disclosure_intro"],
    "seal": ["seal_intro"],
    "fiesta": ["fiesta_title", "fiesta_date", "fiesta_description"],
    "places": ["places_intro"],
    "agenda": ["agenda_intro"],
    "awards": ["awards_intro"],
    "hymn": ["hymn_title", "hymn_composer", "hymn_link", "hymn_lyrics"],
    "visit": ["visit_hours", "visit_directions", "visit_map_link"],
}
URL_FIELDS = {"hymn_link", "visit_map_link"}

PLACE_TYPES = ["Landmark", "Church", "Nature", "Park", "Beach / River", "Food", "Local product", "Festival venue"]
DOCUMENT_NAMES = [
    "Annual Budget", "Statement of Receipts and Expenditures", "Annual Procurement Plan",
    "Bid Results / Awarded Contracts", "20% Development Fund Utilization", "Statement of Debt Service",
    "Trust Fund Utilization", "Annual GAD Accomplishment Report", "Annual Report",
]

ITEM_SECTIONS = {
    "seal": {
        "tab": "seal", "noun": "Symbol", "plural": "Symbols of the Seal",
        "title_label": "Symbol / part of the seal", "title_ph": "e.g. The sun",
        "desc_label": "What it means", "desc_ph": "e.g. The bright future of the town",
        "extra": {"label": "Color (optional)", "type": "color", "help": "The small color dot next to the symbol."},
    },
    "fiesta": {
        "tab": "fiesta", "noun": "Celebration", "plural": "Other Celebrations",
        "title_label": "Name", "title_ph": "e.g. Founding Anniversary",
        "desc_label": "Short description", "desc_ph": "e.g. Marks the creation of the municipality in 1949",
        "extra": {"label": "Date (optional)", "type": "text", "ph": "e.g. September 26"},
    },
    "place": {
        "tab": "places", "noun": "Place", "plural": "Places",
        "title_label": "Name", "title_ph": "e.g. Municipal Plaza",
        "desc_label": "Short description", "desc_ph": "What visitors can see or do there",
        "extra": {"label": "Type", "type": "choice", "choices": PLACE_TYPES},
        "image": True, "image_help": "Landscape photos look best. Without a photo the Municipal Hall photo is used.",
    },
    "goal": {
        "tab": "agenda", "noun": "Goal", "plural": "Goals",
        "title_label": "Goal", "title_ph": "e.g. Good governance & digital services",
        "desc_label": "What is being done", "desc_ph": "e.g. Online requests, transparency and faster service",
        "extra": {"label": "Progress % (optional)", "type": "number", "help": "0 – 100. Leave empty to hide the progress bar."},
    },
    "award": {
        "tab": "awards", "noun": "Award", "plural": "Awards",
        "title_label": "Award", "title_ph": "e.g. Seal of Good Local Governance",
        "desc_label": "Given by", "desc_ph": "e.g. Department of the Interior and Local Government (DILG)", "desc_short": True,
        "year": {"label": "Year", "required": False},
    },
    "document": {
        "tab": "transparency", "noun": "Document", "plural": "Documents",
        "title_label": "Document", "title_ph": "e.g. Annual Budget", "title_list": DOCUMENT_NAMES,
        "no_desc": True,
        "extra": {"label": "Period (optional)", "type": "text", "ph": "e.g. Q3, 1st Semester"},
        "year": {"label": "Fiscal year", "required": True},
        "file": True,
    },
}