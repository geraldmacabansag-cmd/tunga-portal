"""Website theme: colors, fonts and text size of the PUBLIC website, set by
the Super Admin in Website Settings -> Theme & Colors tab (admin_dashboard/views.py
admin_theme, templates/admin_dashboard/_theme_settings.html).

How it works
- The public CSS (static/css/base.css :root) already uses color variables
  such as --navy and --gold. The defaults below are exactly those colors, so
  with nothing changed the website looks the same as before.
- Only what the Super Admin changed is saved (SiteTheme). On every public
  page {% site_theme %} (templatetags/theme_tags.py, loaded in base.html
  after all the CSS) writes a small <style> that replaces just those values.
- "Reset to default" deletes the saved changes.
"""
import re

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# key, CSS variable, label, default, help, follows (another key: when not
# changed, this color simply follows that one, like it does now)
COLORS = [
    # --- main colors (used all over the website) ---
    ("navy", "--navy", "Main color", "#0d3a86", "Links, titles, icons, active menu, the TUNGA name", ""),
    ("navy_deep", "--navy-deep", "Dark main color", "#0a2f6e", "Announcement bar, footer, dark backgrounds", ""),
    ("navy_light", "--navy-light", "Light main color", "#1450b8", "Button hover, color blends", ""),
    ("blue_accent", "--blue-accent", "Accent color", "#1a56c4", "Header tagline and small highlights", ""),
    ("gold", "--gold", "Highlight color", "#f4c531", "Active menu underline, highlights, keyboard focus ring", ""),
    ("gold_dark", "--gold-dark", "Highlight hover", "#e0af1a", "Highlight color when hovered", ""),
    # --- text ---
    ("text_dark", "--text-dark", "Headings & main text", "#1c2733", "Titles and the main text", ""),
    ("text_body", "--text-body", "Paragraph text", "#4a5568", "Longer text such as descriptions", ""),
    ("text_muted", "--text-muted", "Small gray text", "#6b7684", "Dates, labels, notes", ""),
    # --- backgrounds ---
    ("bg_white", "--bg-white", "Page background", "#ffffff", "Background of every page", ""),
    ("bg_light", "--bg-light", "Soft background", "#f3f5f8", "Light boxes, sections and hovers", ""),
    ("border_light", "--border-light", "Borders & lines", "#e2e6ed", "Card borders and divider lines", ""),
    # --- labels ---
    ("green_badge", "--green-badge", "Green labels", "#3fae4a", "\"Announcement\" tag, NEW / open labels", ""),
    ("red_badge", "--red-badge", "Red labels", "#e0332f", "Urgent / important labels", ""),
    # --- parts of the page ---
    ("top_bar_bg", "", "Top bar background", "#0a2f6e", "The thin bar at the very top (Login / account)", "navy_deep"),
    ("top_bar_text", "", "Top bar text", "#ffffff", "Text and links in the top bar", ""),
    ("header_bg", "", "Header & menu background", "#ffffff", "The logo and menu bar", ""),
    ("header_text", "", "Menu text", "#1c2733", "Home, Offices, About Us…", "text_dark"),
    ("btn_bg", "", "Buttons", "#0d3a86", "Main buttons (Submit, Read more…)", "navy"),
    ("btn_hover", "", "Buttons on hover", "#1450b8", "Main buttons when hovered", "navy_light"),
    ("btn_text", "", "Button text", "#ffffff", "Text on the main buttons", ""),
    ("footer_bg", "", "Footer background", "#0a2f6e", "The bottom part of every page", "navy_deep"),
    ("footer_text", "", "Footer text", "#cdd9f2", "Text and links in the footer", ""),
    # --- maintenance message (Website Settings → Maintenance) ---
    ("maint_bg", "", "Maintenance bar background", "#7a3e00", "The top bar while maintenance mode is on", ""),
    ("maint_text", "", "Maintenance message text", "#fff3dc", "The maintenance message in the top bar", ""),
    ("maint_tag", "", "Maintenance label", "#f4c531", "The MAINTENANCE tag and the \"Expected back\" time", "gold"),
    # --- About Us page (the newer sections) ---
    ("about_icon_bg", "", "Icon boxes", "#e7eefb", "Small icon boxes, year labels and document buttons", ""),
    ("about_fiesta", "", "Town Fiesta card", "#e0332f", "The big card in Fiesta & Culture", "red_badge"),
    ("about_hymn", "", "Hymn banner", "#0a2f6e", "The Municipal Hymn banner", "navy_deep"),
    ("about_medal", "", "Award medals", "#f4c531", "The gold medals in Awards & Recognition", "gold"),
    ("about_goal_num", "", "Agenda numbers", "#e0af1a", "The 01, 02, 03… of the Development Agenda", "gold_dark"),
]

GROUPS = [
    ("Main colors", ["navy", "navy_deep", "navy_light", "blue_accent", "gold", "gold_dark"]),
    ("Text", ["text_dark", "text_body", "text_muted"]),
    ("Backgrounds", ["bg_white", "bg_light", "border_light"]),
    ("Labels", ["green_badge", "red_badge"]),
    ("Parts of the page", ["top_bar_bg", "top_bar_text", "header_bg", "header_text",
                           "btn_bg", "btn_hover", "btn_text", "footer_bg", "footer_text"]),
    ("Maintenance message", ["maint_bg", "maint_text", "maint_tag"]),
    ("About Us page", ["about_icon_bg", "about_fiesta", "about_hymn", "about_medal", "about_goal_num"]),
]

DEFAULTS = {k: d for k, _v, _l, d, _h, _f in COLORS}
FOLLOWS = {k: f for k, _v, _l, _d, _h, f in COLORS if f}
VARS = {k: v for k, v, _l, _d, _h, _f in COLORS if v}

# Fonts: "" = the current font (no change). Google Fonts are loaded only
# when chosen. key: (label, Google Fonts family or "", CSS font stack)
FONTS = {
    "": ("Default (current)", "", ""),
    "poppins": ("Poppins", "Poppins:wght@400;500;600;700;800", "'Poppins', 'Segoe UI', sans-serif"),
    "inter": ("Inter", "Inter:wght@400;500;600;700;800", "'Inter', 'Segoe UI', sans-serif"),
    "roboto": ("Roboto", "Roboto:wght@400;500;700;900", "'Roboto', 'Segoe UI', sans-serif"),
    "open-sans": ("Open Sans", "Open+Sans:wght@400;500;600;700;800", "'Open Sans', 'Segoe UI', sans-serif"),
    "lato": ("Lato", "Lato:wght@400;700;900", "'Lato', 'Segoe UI', sans-serif"),
    "montserrat": ("Montserrat", "Montserrat:wght@400;500;600;700;800", "'Montserrat', 'Segoe UI', sans-serif"),
    "nunito": ("Nunito", "Nunito:wght@400;600;700;800", "'Nunito', 'Segoe UI', sans-serif"),
    "source-sans": ("Source Sans 3", "Source+Sans+3:wght@400;600;700;800", "'Source Sans 3', 'Segoe UI', sans-serif"),
    "noto-sans": ("Noto Sans", "Noto+Sans:wght@400;500;600;700;800", "'Noto Sans', 'Segoe UI', sans-serif"),
    "merriweather": ("Merriweather (serif)", "Merriweather:wght@400;700;900", "'Merriweather', Georgia, serif"),
    "playfair": ("Playfair Display (serif)", "Playfair+Display:wght@500;600;700;800", "'Playfair Display', Georgia, serif"),
    "arial": ("Arial (no download)", "", "Arial, Helvetica, sans-serif"),
    "georgia": ("Georgia (no download)", "", "Georgia, 'Times New Roman', serif"),
}

# "" = default (no change)
TEXT_SIZES = {"": ("Default", ""), "small": ("Small", "15px"), "large": ("Large", "17px"), "xlarge": ("Extra large", "18px")}

# Ready-made color sets (only fill the boxes; nothing is saved until "Save")
PRESETS = {
    "Tunga Blue (default)": {},
    "Forest Green": {"navy": "#1f6b3a", "navy_deep": "#164d2a", "navy_light": "#2e8b4e", "blue_accent": "#2e8b4e",
                     "gold": "#f4c531", "gold_dark": "#e0af1a", "footer_text": "#d4e9db"},
    "Maroon": {"navy": "#7a1f2b", "navy_deep": "#5c1520", "navy_light": "#9c2d3b", "blue_accent": "#9c2d3b",
               "gold": "#f2b632", "gold_dark": "#d99b16", "footer_text": "#f1d6da"},
    "Ocean Teal": {"navy": "#0f6e7a", "navy_deep": "#0b4f58", "navy_light": "#14909e", "blue_accent": "#14909e",
                   "gold": "#f7c948", "gold_dark": "#e3b12a", "footer_text": "#cfecef"},
    "Royal Purple": {"navy": "#4b2d8f", "navy_deep": "#35206a", "navy_light": "#6441b8", "blue_accent": "#6441b8",
                     "gold": "#f4c531", "gold_dark": "#e0af1a", "footer_text": "#ddd3f3"},
    "Charcoal": {"navy": "#2b3440", "navy_deep": "#1c232c", "navy_light": "#3e4a5a", "blue_accent": "#3e6ea8",
                 "gold": "#f59e0b", "gold_dark": "#d97706", "footer_text": "#d5dae1"},
}


def clean_color(value):
    value = (value or "").strip()
    if re.match(r"^#[0-9a-fA-F]{3}$", value):
        value = "#" + "".join(c * 2 for c in value[1:])
    return value.lower() if HEX.match(value) else ""


def effective(colors):
    """Every color as it really shows: saved ones, else what it follows,
    else the default."""
    out = {}
    for k, _v, _l, d, _h, f in COLORS:
        out[k] = colors.get(k) or (out.get(f) if f else None) or d
    return out


def changed_only(posted):
    """From the form: keep only the colors that differ from what they would
    be anyway (their default, or the color they follow)."""
    saved = {}
    for k, _v, _l, d, _h, f in COLORS:
        c = clean_color(posted.get(k))
        if not c:
            continue
        base = effective(saved)[f] if f else d
        if c != base:
            saved[k] = c
    return saved


def theme_css(theme):
    """The <style> text for the public pages ("" when nothing was changed)."""
    if theme is None:
        return "", ""
    colors = {k: v for k, v in (theme.colors or {}).items() if k in DEFAULTS and HEX.match(v or "")}
    root, rules = [], []
    for k, var in VARS.items():
        if k in colors:
            root.append(f"{var}:{colors[k]}")

    c = colors.get
    if c("top_bar_bg"):
        rules.append(f".top-bar{{background:{c('top_bar_bg')}}}")
    if c("top_bar_text"):
        t = c("top_bar_text")
        rules.append(f".top-bar,.top-bar__msg,.top-bar__links a,.top-bar__welcome,.top-bar__divider{{color:{t}}}")
    if c("header_bg"):
        rules.append(f".site-header,.nav-dropdown__menu{{background:{c('header_bg')}}}")
    if c("header_text"):
        rules.append(f".main-nav a,.nav-dropdown__trigger,.brand__label{{color:{c('header_text')}}}")
    if c("btn_bg") or c("btn_text"):
        bg = c("btn_bg") or "var(--navy)"
        tx = c("btn_text") or "#fff"
        rules.append(f".btn-primary,.btn.btn-primary{{background:{bg};border-color:{bg};color:{tx}}}")
    if c("btn_hover"):
        rules.append(f".btn-primary:hover,.btn.btn-primary:hover{{background:{c('btn_hover')};border-color:{c('btn_hover')}}}")
    if c("footer_bg"):
        rules.append(f".site-footer{{background:{c('footer_bg')}}}")
    if c("footer_text"):
        t = c("footer_text")
        rules.append(f".site-footer,.footer-col a,.footer-col p,.footer-brand p,.footer-bottom,.footer-bottom a{{color:{t}}}")
        rules.append(f".footer-col h5,.footer-brand h4{{color:{t}}}")
    # maintenance message in the top bar (templates/base.html, static/css/base.css)
    if c("maint_bg"):
        rules.append(f".top-bar.top-bar--maint{{background:{c('maint_bg')}}}")
    if c("maint_text"):
        rules.append(f".top-bar--maint .top-bar__msg,.top-bar--maint .top-bar__closed,.top-bar--maint .top-bar__maint-link{{color:{c('maint_text')}}}")
    if c("maint_tag"):
        t = c("maint_tag")
        rules.append(f".top-bar__tag--maint{{background:{t};color:{_ink(t)}}}.top-bar__until{{color:{t}}}.top-bar__pop{{border-top-color:{t}}}")
    # About Us page, newer sections (static/css/aboutus.css "Newer About Us sections")
    if c("about_icon_bg"):
        rules.append(f".ab-facts li>i,.ab-doc__btn,.ab-award__yr{{background:{c('about_icon_bg')}}}")
    if c("about_fiesta"):
        f = c("about_fiesta")
        rules.append(f".ab-feature{{background:linear-gradient(135deg,{_mix(f, '#ff8a00', .3)} 0%,{f} 45%,{_mix(f, '#000000', .45)} 100%)}}")
    if c("about_hymn"):
        h = c("about_hymn")
        rules.append(f".ab-hymn{{background:linear-gradient(135deg,{h},{_mix(h, '#ffffff', .18)})}}")
    if c("about_medal"):
        m = c("about_medal")
        rules.append(f".ab-award__medal{{background:radial-gradient(circle at 35% 30%,{_mix(m, '#ffffff', .75)},{m} 60%,{_mix(m, '#000000', .15)});color:{_mix(m, '#000000', .55)}}}")
    if c("about_goal_num"):
        rules.append(f".ab-goal__n{{color:{c('about_goal_num')}}}")

    head_key = theme.heading_font if theme.heading_font in FONTS else ""
    body_key = theme.body_font if theme.body_font in FONTS else ""
    if body_key:
        root.append(f"--font-body:{FONTS[body_key][2]}")
        rules.append("body,button,input,select,textarea{font-family:var(--font-body)}")
    if head_key:
        root.append(f"--font-display:{FONTS[head_key][2]}")
        rules.append("h1,h2,h3,h4,h5,h6,.brand__name{font-family:var(--font-display)}")
    size = TEXT_SIZES.get(theme.text_size or "", TEXT_SIZES[""])[1]
    if size:
        rules.append(f"html{{font-size:{size}}}")

    css = ""
    if root:
        css += ":root{" + ";".join(root) + "}"
    css += "".join(rules)

    families = [FONTS[k][1] for k in dict.fromkeys([head_key, body_key]) if k and FONTS[k][1]]
    fonts_url = ("https://fonts.googleapis.com/css2?" + "&".join("family=" + f for f in families) + "&display=swap") if families else ""
    return css, fonts_url


# ---------------------------------------------------------------------------
# Dashboards (Super Admin / Office Representative). When "Apply to ... dashboard"
# is ticked, the colors and fonts CHANGED on the website are used there too.
# The dashboards have their own default look (dark sidebar, bright blue), so a
# color that was not changed keeps the dashboard's own default.
#   Main color        -> buttons, active menu, links   (--blue-600, --blue-50)
#   Light main color  -> button hover                   (--blue-500)
#   Dark main color   -> sidebar (darker shades)        (--navy-950 ... --navy-700)
#   Fonts             -> dashboard text and headings
def _mix(a, b, t):
    """a mixed with b; t = how much of b (0..1)."""
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _ink(bg):
    """Dark or white text, whichever reads better on the color bg."""
    r, g, b = (int(bg[i:i + 2], 16) for i in (1, 3, 5))
    return "#2b1d00" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#ffffff"


def dashboard_vars(colors):
    """{css variable: color} for the dashboards, from the saved website colors."""
    eff = effective(colors)
    out = {}
    if colors.get("navy"):
        out["--blue-600"] = eff["navy"]
        out["--blue-50"] = _mix(eff["navy"], "#ffffff", 0.9)
        if not colors.get("navy_light"):
            out["--blue-500"] = _mix(eff["navy"], "#ffffff", 0.15)   # a bit lighter for hover
    if colors.get("navy_light"):
        out["--blue-500"] = eff["navy_light"]
    if colors.get("navy_deep"):
        d = eff["navy_deep"]
        out.update({"--navy-950": _mix(d, "#000000", .55), "--navy-900": _mix(d, "#000000", .45),
                    "--navy-800": _mix(d, "#000000", .3), "--navy-700": _mix(d, "#000000", .15)})
    return out


def dashboard_css(theme, which):
    """<style> text for a dashboard: which = "super_admin" or "office_rep"."""
    if theme is None or not getattr(theme, "apply_" + which, False):
        return "", ""
    colors = {k: v for k, v in (theme.colors or {}).items() if k in DEFAULTS and HEX.match(v or "")}
    root = [f"{k}:{v}" for k, v in dashboard_vars(colors).items()]
    rules = []
    eff = effective(colors)
    # the sidebars have their own dark gradient and blue icon tiles
    # (static/css/super_admin_style.css .sidebar--sa, office_rep_style.css .sidebar--rep)
    if colors.get("navy_deep"):
        d = eff["navy_deep"]
        rules.append(f".sidebar.sidebar--sa,.sidebar.sidebar--rep{{background:linear-gradient(180deg,{_mix(d, '#000000', .5)} 0%,{_mix(d, '#000000', .66)} 100%)}}")
        rules.append(f".sidebar--rep .office-switcher{{background:linear-gradient(135deg,{_mix(d, '#000000', .05)} 0%,{_mix(d, '#000000', .3)} 100%)}}")
    if colors.get("navy"):
        m = eff["navy"]
        a, b = _mix(m, "#ffffff", .3), _mix(m, "#000000", .05)
        rules.append(f".sidebar.sidebar--sa{{--sa-tile-a:{a};--sa-tile-b:{b}}}.sidebar.sidebar--rep{{--rep-tile-a:{a};--rep-tile-b:{b}}}")
        rules.append(f".sidebar--sa .nav-item.active,.sidebar--rep .nav-item.active{{background:{_mix(m, '#ffffff', .18)}}}")
        rules.append(f".btn-primary:hover{{background:{_mix(m, '#000000', .15)}}}")
    head_key = theme.heading_font if theme.heading_font in FONTS else ""
    body_key = theme.body_font if theme.body_font in FONTS else ""
    if body_key:
        rules.append(f"body,button,input,select,textarea{{font-family:{FONTS[body_key][2]}}}")
    if head_key:
        rules.append(f"h1,h2,h3,h4,.panel-header h2,.sidebar-brand{{font-family:{FONTS[head_key][2]}}}")
    css = (":root{" + ";".join(root) + "}" if root else "") + "".join(rules)
    families = [FONTS[k][1] for k in dict.fromkeys([head_key, body_key]) if k and FONTS[k][1]]
    fonts_url = ("https://fonts.googleapis.com/css2?" + "&".join("family=" + f for f in families) + "&display=swap") if families else ""
    return css, fonts_url