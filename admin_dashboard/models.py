from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class SuperAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="super_admin")
    mobile_number = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="super_admin_photos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.pk and SuperAdmin.objects.exists():
            raise ValidationError("Only one Super Admin account is allowed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class SiteContactInfo(models.Model):
    DEFAULT_TAGLINE = "Abtik na serbisyo, masulong na bungto."

    phone = models.CharField(max_length=50, blank=True)
    phone_local = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    email_secondary = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    facebook_name = models.CharField(max_length=150, blank=True)
    facebook_url = models.URLField(blank=True)
    office_hours = models.CharField(max_length=150, blank=True)
    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    hero_banner = models.ImageField(upload_to="site/", blank=True, null=True)
    # Banner photo at the top of each public page (Website Settings → Appearance →
    # Page banners). Empty = the default LGU building photo (static/images/lgu_tunga_bldg.jpeg).
    banner_announcements = models.ImageField(upload_to="site/banners/", blank=True, null=True)
    banner_gallery = models.ImageField(upload_to="site/banners/", blank=True, null=True)
    banner_offices = models.ImageField(upload_to="site/banners/", blank=True, null=True)
    banner_about = models.ImageField(upload_to="site/banners/", blank=True, null=True)
    banner_contact = models.ImageField(upload_to="site/banners/", blank=True, null=True)
    # Shown under "MUNICIPALITY OF TUNGA" in the public site header (Website Settings → Appearance)
    site_tagline = models.CharField(max_length=120, default=DEFAULT_TAGLINE, blank=True)
    # Home page banner slider (Super Admin → Homepage → Banner Slider), see
    # portal/hero_slides.py:
    #   hero_slider_seconds  how long each slide shows (3 seconds to 60 minutes)
    #   hero_slider_mode     "auto" = newest posts with a picture,
    #                        "pick" = only the posts in hero_slider_items
    #   hero_slider_items    the picked posts in slide order: ["announcement:12", "news:5", "event:3", …]
    HERO_SLIDER_MODE_CHOICES = [("auto", "Automatic (newest posts with a picture)"), ("pick", "Chosen content")]
    hero_slider_seconds = models.PositiveIntegerField(default=6)
    hero_slider_mode = models.CharField(max_length=10, choices=HERO_SLIDER_MODE_CHOICES, default="auto")
    hero_slider_items = models.JSONField(default=list, blank=True)
    # Home page News slider: seconds before the next news story slides in
    # (Website Settings → Appearance).
    news_slider_seconds = models.PositiveIntegerField(default=6)
    # "Our Location" map on the Contact Us page (Website Settings → General):
    # where the pin goes. Empty = the town center of Tunga.
    DEFAULT_MAP_LAT = 11.2483
    DEFAULT_MAP_LNG = 124.7524
    map_place_name = models.CharField(max_length=120, blank=True, default="Municipal Hall of Tunga")
    map_latitude = models.FloatField(null=True, blank=True)
    map_longitude = models.FloatField(null=True, blank=True)
    # Website Settings → Maintenance: while on, visitors see the maintenance
    # page instead of the website (staff can still use everything).
    DEFAULT_MAINTENANCE_MESSAGE = ("We're currently performing scheduled maintenance on our website. "
                                   "Please check back shortly. For urgent concerns, please contact the Municipal Hall.")
    maintenance_mode = models.BooleanField(default=False)
    # what maintenance mode does:
    #   "site"   close the website: visitors see the maintenance page
    #   "notice" keep the website open: the message replaces the
    #            announcement bar at the top of every page
    MAINTENANCE_SCOPE_CHOICES = [
        ("site", "Close the website (show the maintenance page)"),
        ("notice", "Message only (keep the website open, show the message at the top)"),
    ]
    maintenance_scope = models.CharField(max_length=10, choices=MAINTENANCE_SCOPE_CHOICES, default="site")
    maintenance_message = models.TextField(blank=True, default=DEFAULT_MAINTENANCE_MESSAGE)
    maintenance_until = models.DateTimeField(null=True, blank=True)   # turns itself off at this time

    # Website Settings → SEO: how the website shows up in Google and when a
    # link is shared on Facebook / Messenger.
    DEFAULT_SEO_TITLE = "Municipality of Tunga, Leyte — Official Website"
    DEFAULT_SEO_DESCRIPTION = "Official website of the LGU of Tunga, Leyte: announcements, news, events, downloadable forms and contact details of all municipal offices."
    seo_title = models.CharField(max_length=70, blank=True, default=DEFAULT_SEO_TITLE)
    seo_description = models.CharField(max_length=300, blank=True, default=DEFAULT_SEO_DESCRIPTION)
    share_image = models.ImageField(upload_to="site/", blank=True, null=True)   # Facebook / Messenger preview picture
    search_console_code = models.CharField(max_length=120, blank=True)       # Google Search Console verification
    allow_indexing = models.BooleanField(default=True)                         # off = hide the site from Google
    social_facebook = models.URLField(blank=True)
    social_twitter = models.URLField(blank=True)
    social_instagram = models.URLField(blank=True)
    social_youtube = models.URLField(blank=True)
    show_facebook_footer = models.BooleanField(default=True)
    show_twitter_footer = models.BooleanField(default=True)
    show_instagram_footer = models.BooleanField(default=True)
    show_youtube_footer = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Contact Information"
        verbose_name_plural = "Site Contact Information"

    def __str__(self):
        return "Site Contact Information"

    @property
    def map_lat(self):
        return self.map_latitude if self.map_latitude is not None else self.DEFAULT_MAP_LAT

    @property
    def map_lng(self):
        return self.map_longitude if self.map_longitude is not None else self.DEFAULT_MAP_LNG

    @property
    def seo_title_text(self):
        return self.seo_title or self.DEFAULT_SEO_TITLE

    @property
    def seo_description_text(self):
        return self.seo_description or self.DEFAULT_SEO_DESCRIPTION

    # (field, label shown in Website Settings, public page)
    PAGE_BANNERS = [
        ("banner_announcements", "Announcements page", "announcement"),
        ("banner_gallery", "Gallery page", "gallery"),
        ("banner_offices", "Offices page", "offices"),
        ("banner_about", "About Us page", "about"),
        ("banner_contact", "Contact Us page", "contact"),
    ]

    @property
    def page_banners(self):
        """For the Appearance tab: [{key, label, url_name, image}, …]."""
        return [{"key": k, "label": label, "url_name": url_name, "image": getattr(self, k)}
                for k, label, url_name in self.PAGE_BANNERS]

    @property
    def maintenance_active(self):
        """On, and the "back online at" time (if any) hasn't passed yet."""
        if not self.maintenance_mode:
            return False
        if self.maintenance_until:
            from django.utils import timezone
            return timezone.now() < self.maintenance_until
        return True

    @property
    def maintenance_closes_site(self):
        """Maintenance is on and visitors get the maintenance page."""
        return self.maintenance_active and self.maintenance_scope != "notice"

    @property
    def maintenance_notice(self):
        """Maintenance is on, the website stays open and the message shows
        at the top of every page (the top bar)."""
        return self.maintenance_active and self.maintenance_scope == "notice"

    @property
    def hero_slider_unit(self):
        """'minutes' when the slide time is a whole number of minutes, else 'seconds'."""
        s = self.hero_slider_seconds or 6
        return "minutes" if s >= 60 and s % 60 == 0 else "seconds"

    @property
    def hero_slider_value(self):
        s = self.hero_slider_seconds or 6
        return s // 60 if self.hero_slider_unit == "minutes" else s

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            'phone': '(053) 456 789',
            'phone_local': 'Local 100',
            'email': 'tunga@gmail.com',
            'email_secondary': 'info@tunga.gov.ph',
            'address': '2nd Floor, Municipal Hall, Tunga, Leyte',
            'facebook_name': 'Municipality of Tunga - Official',
            'office_hours': 'Monday – Friday, 8:00 AM – 5:00 PM',
        })
        return obj

    @property
    def tagline(self):
        """The tagline to show — the default one if it was left empty."""
        return (self.site_tagline or "").strip() or self.DEFAULT_TAGLINE

class EmailProviderSettings(models.Model):
    """Super Admin → System Settings. Emails go out through Brevo first; if
    Brevo fails (e.g. its 300-a-day free limit is used up) the same email is
    sent through the BACKUP sender (Mailjet or Gmail). admin_dashboard/email_utils.py"""
    BACKUP_CHOICES = [
        ("", "No backup"),
        ("mailjet", "Mailjet (works on Render's free plan)"),
        ("gmail", "Gmail (needs a host that allows SMTP)"),
    ]

    email_address = models.EmailField(blank=True, help_text="The verified sender email in Brevo")
    # Backup sender: the Gmail App Password, or the Mailjet Secret Key (encrypted)
    app_password_encrypted = models.TextField(blank=True)
    api_key_encrypted = models.TextField(blank=True)
    is_configured = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    backup_provider = models.CharField(max_length=20, choices=BACKUP_CHOICES, blank=True, default="")
    backup_email = models.EmailField(blank=True, help_text="Sender address of the backup (the Gmail address, or a sender verified in Mailjet)")
    backup_api_key_encrypted = models.TextField(blank=True)   # Mailjet API Key
    backup_last_used = models.DateTimeField(null=True, blank=True)
    backup_used_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Email Provider Settings"
        verbose_name_plural = "Email Provider Settings"

    def __str__(self):
        return "Email Provider Settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def set_api_key(self, plain_key):
        from .crypto_utils import encrypt_value
        self.api_key_encrypted = encrypt_value(plain_key)

    def get_api_key(self):
        from .crypto_utils import decrypt_value
        return decrypt_value(self.api_key_encrypted)

    # backup sender secrets (encrypted like the Brevo key)
    def set_backup_secret(self, plain):
        from .crypto_utils import encrypt_value
        self.app_password_encrypted = encrypt_value(plain)

    def get_backup_secret(self):
        from .crypto_utils import decrypt_value
        return decrypt_value(self.app_password_encrypted)

    def set_backup_api_key(self, plain):
        from .crypto_utils import encrypt_value
        self.backup_api_key_encrypted = encrypt_value(plain)

    def get_backup_api_key(self):
        from .crypto_utils import decrypt_value
        return decrypt_value(self.backup_api_key_encrypted)

    @property
    def backup_ready(self):
        """True when the chosen backup has everything it needs."""
        if self.backup_provider == "gmail":
            return bool(self.backup_email and self.app_password_encrypted)
        if self.backup_provider == "mailjet":
            return bool(self.backup_email and self.app_password_encrypted and self.backup_api_key_encrypted)
        return False

class EmergencyContact(models.Model):

    CATEGORY_CHOICES = [
        ("Medical / Rescue", "Medical / Rescue"),
        ("Police", "Police"),
        ("Health", "Health"),
        ("Fire", "Fire"),
        ("General", "General"),
    ]

    ICON_CHOICES = [
        ("fa-truck-medical", "Ambulance"),
        ("fa-user-shield", "Shield"),
        ("fa-heart-pulse", "Heartbeat"),
        ("fa-fire", "Fire"),
        ("fa-hospital", "Hospital"),
        ("fa-life-ring", "Life Ring"),
        ("fa-shield-halved", "Shield Halved"),
        ("fa-house-fire", "House Fire"),
        ("fa-phone-volume", "Phone Volume"),
        ("fa-phone", "Phone"),
    ]

    # Colors of the icon and CALL button (CSS: super_admin_style.css "cc-…" and homepage.css "emergency__…")
    COLOR_CHOICES = [
        ("red", "Red"),
        ("maroon", "Maroon"),
        ("pink", "Pink"),
        ("orange", "Orange"),
        ("yellow", "Yellow"),
        ("brown", "Brown"),
        ("green", "Green"),
        ("teal", "Teal"),
        ("sky", "Sky Blue"),
        ("blue", "Blue"),
        ("navy", "Navy"),
        ("indigo", "Indigo"),
        ("purple", "Purple"),
        ("gray", "Gray"),
        ("black", "Black"),
    ]

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="General")
    icon = models.CharField(max_length=30, choices=ICON_CHOICES, default="fa-phone")
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default="gray")
    carrier_label = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=30)
    extra_detail = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    # The official Tunga hotlines. "Reset to default" on the Super Admin
    # Emergency Contacts page restores these and puts them first.
    # (name, category, icon, color, phone number, detail)
    DEFAULT_CONTACTS = [
        ("BFP – Fire Emergency", "Fire", "fa-fire", "red",
         "09856193119", "Bureau of Fire Protection"),
        ("PNP – Police Emergency", "Police", "fa-user-shield", "navy",
         "09062863422", "Philippine National Police"),
        ("MDRRMO – Disaster Management", "Medical / Rescue", "fa-life-ring", "red",
         "09815519256", "Municipal Disaster Risk Reduction and Management Office"),
    ]

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    @classmethod
    def reset_defaults(cls):
        """Leaves only the default hotlines (BFP, PNP, MDRRMO): every other
        contact is removed, deleted ones are added back and edits are undone."""
        numbers = [c[4] for c in cls.DEFAULT_CONTACTS]
        cls.objects.exclude(phone_number__in=numbers).delete()
        for position, (name, category, icon, color, phone, detail) in enumerate(cls.DEFAULT_CONTACTS):
            same_number = cls.objects.filter(phone_number=phone)
            contact = same_number.first() or cls(phone_number=phone)
            same_number.exclude(pk=contact.pk).delete()   # no duplicates
            contact.name = name
            contact.category = category
            contact.icon = icon
            contact.color = color
            contact.carrier_label = ""
            contact.extra_detail = detail
            contact.order = position
            contact.save()

class QuickLink(models.Model):
    """A shortcut tile shown in the "services strip" near the top of the
    public homepage (e.g. Business Permits, Cedula). Managed from the
    Super Admin's Homepage page."""
 
    ICON_CHOICES = [
        ("fa-file-lines", "Document / Permit"),
        ("fa-camera", "Tourism / Culture"),
        ("fa-hand-holding-heart", "Financial Assistance"),
        ("fa-briefcase", "Jobs / Employment"),
        ("fa-id-card", "ID / Cedula"),
        ("fa-phone-volume", "Phone / Hotline"),
        ("fa-map-location-dot", "Map / Location"),
        ("fa-building", "Office / Government"),
    ]
 
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, choices=ICON_CHOICES, default="fa-file-lines")
    url = models.CharField(
        max_length=255,
        help_text="A path on this site (e.g. /offices/) or a full https:// link.",
    )
    open_in_new_tab = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class AboutPageContent(models.Model):
    """Singleton holding the editable text for the public "About Us" page's
    About Us, History, Barangays-intro and "At a Glance" sections — anything
    on that page that isn't a repeatable list (those are HistoryMilestone,
    AboutOfficial and Barangay below). Seeded with the municipality's
    original hardcoded copy, so the page looks the same the moment the
    Super Admin's "About Us Page" screen goes live."""

    # --- Hero + About Us (Vision / Mission / Values) ---
    hero_intro = models.TextField(
        default="The Municipality of Tunga is committed to good governance, transparent leadership, and the continuous progress and well-being of our people."
    )
    vision_text = models.TextField(
        default="Tunga is an innovative Smart City, becoming the institutional training center focused on peace and security instrumentalities of Region 8, and the home for empowered citizens, and progressive climate-resilient and sustained environment governed by transparent and accountable leaders"
    )
    mission_text = models.TextField(
        default="“Our mission at Tunga is to establish a pioneering Smart City that serves as the premier training center for peace and security instrumentalities in Region 8. We are dedicated to empowering our citizens and fostering a progressive, climate-resilient environment, all while ensuring governance that is transparent and accountable.”"
    )
    core_values = models.TextField(
        default="Integrity\nTransparency\nAccountability\nExcellence\nService to Others",
        help_text="One value per line.",
    )

    # --- History intro paragraphs + side image ---
    history_intro = models.TextField(
        default="The Municipality of Tunga was formerly a barrio of the Municipality of Barugo. Through Executive Order No. 266, signed by President Elpidio Quirino on September 26, 1949, Tunga was officially created as an independent municipality.\nSince its creation, Tunga has continued to develop while preserving its agricultural heritage, close-knit community, and local traditions.",
        help_text="One paragraph per line.",
    )
    history_image = models.ImageField(upload_to="about/", blank=True, null=True)

    def history_more_paragraphs(self):
        return [p.strip() for p in self.history_more.splitlines() if p.strip()]

    history_more_title = models.CharField(max_length=150, blank=True)
    history_more = models.TextField(blank=True, help_text="Extra history text shown under the timeline.")

    # --- Heritage section (under the History timeline) ---
    heritage_title = models.CharField(max_length=100, default="Heritage")
    heritage_intro = models.CharField(
        max_length=255, blank=True,
        default="Milestones and accomplishments that have shaped the Municipality of Tunga.",
    )

    # --- Barangays section intro line ---
    barangays_intro = models.CharField(
        max_length=255,
        default="The municipality is composed of 8 barangays.",
    )

    # --- Municipality at a Glance (5 stat tiles) ---
    glance_population_value = models.CharField(max_length=50, default="34,567+")
    glance_population_label = models.CharField(max_length=100, default="Population (2025 PSA Estimate)")
    glance_land_area_value = models.CharField(max_length=50, default="78.45 km²")
    glance_land_area_label = models.CharField(max_length=100, default="Total Land Area")
    glance_households_value = models.CharField(max_length=50, default="8,652+")
    glance_households_label = models.CharField(max_length=100, default="Households")
    glance_established_value = models.CharField(max_length=50, default="Established")
    glance_established_label = models.CharField(max_length=150, default="September 26, 1949 (E.O. No. 266)")

    # ---- Newer sections (one tab each in Super Admin → About Us Page). All
    # empty by default: a section only shows on the public page once it has
    # content. Their list entries are AboutItem rows. ----
    # Location
    location_intro = models.TextField(blank=True)
    location_neighbors = models.CharField(max_length=300, blank=True)      # comma separated
    location_distance = models.CharField(max_length=150, blank=True)       # e.g. "About 40 km · 1 hour by land"
    location_terrain = models.CharField(max_length=255, blank=True)
    location_show_map = models.BooleanField(default=True)                  # the Tunga Interactive Map in the section
    # Full Disclosure (documents are AboutItem section="document")
    disclosure_intro = models.CharField(max_length=300, blank=True)
    # Official Seal (the seal picture is the website logo)
    seal_intro = models.TextField(blank=True)
    # Fiesta & Culture (the main celebration; others are AboutItem section="fiesta")
    fiesta_title = models.CharField(max_length=200, blank=True)
    fiesta_date = models.CharField(max_length=100, blank=True)
    fiesta_description = models.TextField(blank=True)
    fiesta_image = models.ImageField(upload_to="about/", blank=True, null=True)
    # Places to Visit / Development Agenda / Awards: a line under the heading
    places_intro = models.CharField(max_length=255, blank=True)
    agenda_intro = models.CharField(max_length=255, blank=True)
    awards_intro = models.CharField(max_length=255, blank=True)
    # Municipal Hymn
    hymn_title = models.CharField(max_length=200, blank=True)
    hymn_composer = models.CharField(max_length=200, blank=True)
    hymn_link = models.URLField(max_length=500, blank=True)               # YouTube / Facebook video
    hymn_lyrics = models.TextField(blank=True)                            # only if the LGU allows it
    # Visit the Municipal Hall (address / phone / email come from Website Settings)
    visit_hours = models.TextField(blank=True)                            # "Monday – Friday | 8:00 AM – 5:00 PM", one per line
    visit_directions = models.TextField(blank=True)                       # one step per line
    visit_map_link = models.URLField(max_length=500, blank=True)          # empty = Google Maps to the Municipal Hall pin

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "About Page Content"
        verbose_name_plural = "About Page Content"

    def __str__(self):
        return "About Page Content"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def core_values_list(self):
        return [v.strip() for v in self.core_values.splitlines() if v.strip()]

    def history_intro_paragraphs(self):
        return [p.strip() for p in self.history_intro.splitlines() if p.strip()]

    # helpers for the newer sections
    def location_neighbor_list(self):
        return [n.strip() for n in self.location_neighbors.split(",") if n.strip()]

    def visit_hour_rows(self):
        """[(day, time), …] from "Monday – Friday | 8:00 AM – 5:00 PM" lines."""
        rows = []
        for line in self.visit_hours.splitlines():
            if line.strip():
                day, _, time = line.partition("|")
                rows.append((day.strip(), time.strip()))
        return rows

    def visit_direction_steps(self):
        return [s.strip() for s in self.visit_directions.splitlines() if s.strip()]

    def hymn_lyrics_paragraphs(self):
        return [p.strip() for p in self.hymn_lyrics.split("\n\n") if p.strip()]


class AboutItem(models.Model):
    """One entry of the newer About Us sections (Super Admin → About Us Page,
    one tab each). Which fields are used depends on the section — see
    admin_dashboard/about_sections.py:
      seal      a symbol of the seal: title, meaning, color (extra)
      fiesta    another celebration: title, description, date (extra)
      place     a place to visit: title, description, type (extra), photo
      goal      a development goal: title, description, progress % (extra)
      award     an award: title, given by (description), year
      document  a Full Disclosure PDF: title, fiscal year, period (extra), file
    """
    SECTION_CHOICES = [
        ("seal", "Official Seal"), ("fiesta", "Fiesta & Culture"), ("place", "Places to Visit"),
        ("goal", "Development Agenda"), ("award", "Awards"), ("document", "Full Disclosure"),
    ]
    section = models.CharField(max_length=20, choices=SECTION_CHOICES, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    extra = models.CharField(max_length=100, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to="about/items/", blank=True, null=True)
    file = models.FileField(upload_to="about/documents/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.get_section_display()}: {self.title}"

    @property
    def progress(self):
        """Development goal progress 0-100, or None."""
        try:
            value = int(str(self.extra).strip().rstrip("%"))
        except ValueError:
            return None
        return max(0, min(value, 100))


class HistoryMilestone(models.Model):
    """One row of the About page's History timeline (e.g. "1949" paired with
    the E.O. No. 266 paragraph). is_present styles the row as the gold
    "Present" marker instead of a plain year, matching the page's original
    hardcoded timeline."""
    year_label = models.CharField(max_length=30, help_text='e.g. "1949", "1950s", or "Present"')
    description = models.TextField()
    is_present = models.BooleanField(default=False, help_text='Styles this entry as the gold "Present" marker instead of a year.')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.year_label


class HeritageItem(models.Model):
    """One card of the About page's "Heritage" section (under the History
    timeline): a photo, a title and a short description. Edited on the
    Super Admin's About Us Page → Heritage tab."""
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="about/heritage/", blank=True, null=True)   # empty = the Municipal Hall photo
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class AboutOfficial(models.Model):
    """One official card shown in the About page's "Our Officials" strip.
    Deliberately separate from OfficeRepresentative (the Offices app's
    functional office-dashboard accounts) — this is just the public roster
    photo/name/title, same as the page's original hardcoded cards."""
    name = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    photo = models.ImageField(upload_to="about/officials/", blank=True, null=True)
    # Term of office (years), e.g. 2025 – 2028. Both optional.
    term_start = models.PositiveSmallIntegerField(null=True, blank=True)
    term_end = models.PositiveSmallIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} ({self.position})"

    @property
    def term_label(self):
        """'2025 – 2028', 'Since 2025', 'Until 2028' or '' (no term set)."""
        if self.term_start and self.term_end:
            return f"{self.term_start} – {self.term_end}"
        if self.term_start:
            return f"Since {self.term_start}"
        if self.term_end:
            return f"Until {self.term_end}"
        return ""


class Barangay(models.Model):
    """One barangay listed on the About page's Barangays section."""
    GROUP_CHOICES = [
        ("poblacion", "Poblacion (Urban)"),
        ("rural", "Rural"),
    ]
    name = models.CharField(max_length=100)
    group = models.CharField(max_length=20, choices=GROUP_CHOICES, default="poblacion")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group", "order", "id"]

    def __str__(self):
        return self.name


class AdminNotification(models.Model):
    """A notification for a Super Admin (the bell in the dashboard's top bar).
    Created automatically by admin_dashboard/signals.py when an office
    submits something for approval or sends a message."""

    LEVEL_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("danger", "Danger"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="admin_notifications")
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="info")
    icon = models.CharField(max_length=50, default="fa-regular fa-bell")
    link_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class BackupSettings(models.Model):
    """Backup & Restore page settings (one row). Not included in backups and
    not touched by a restore, so the restore status survives the restore."""
    auto_enabled = models.BooleanField(default=True)
    keep_count = models.PositiveIntegerField(default=14)
    auto_include_files = models.BooleanField(default=True)

    restore_status = models.CharField(max_length=20, blank=True)   # "", running, success, failed
    restore_message = models.TextField(blank=True)
    restore_started_at = models.DateTimeField(null=True, blank=True)
    restore_finished_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Backup settings"


class SiteBackup(models.Model):
    """One backup .zip (data + uploaded files) kept in the backup storage.
    Not included in backups and not touched by a restore."""

    KIND_CHOICES = [
        ("manual", "Manual"),
        ("auto", "Automatic"),
        ("safety", "Safety (before restore)"),
        ("uploaded", "Uploaded"),
    ]
    STATUS_CHOICES = [
        ("running", "In progress"),
        ("success", "Complete"),
        ("failed", "Failed"),
    ]

    filename = models.CharField(max_length=255, blank=True)     # name inside the backup storage
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    include_files = models.BooleanField(default=True)
    size = models.BigIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_by_name = models.CharField(max_length=150, blank=True)  # plain text: users can change on restore
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename or f"Backup #{self.pk}"


class LegalPage(models.Model):
    """Privacy Policy, Terms of Use and Accessibility Statement — edited in
    Website Settings → Legal Pages, shown at /privacy-policy/, /terms-of-use/
    and /accessibility/ (links in the footer and on the sign-up page).
    The starting text is in portal/legal_defaults.py."""
    KEY_CHOICES = [
        ("privacy", "Privacy Policy"),
        ("terms", "Terms of Use"),
        ("accessibility", "Accessibility Statement"),
    ]
    key = models.CharField(max_length=20, choices=KEY_CHOICES, unique=True)
    title = models.CharField(max_length=120)
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    @classmethod
    def get(cls, key):
        """The page, created from the starting text if it doesn't exist yet."""
        from portal.legal_defaults import PAGES
        page = cls.objects.filter(key=key).first()
        if page is None:
            for k, title, _url, text in PAGES:
                if k == key:
                    page = cls.objects.create(key=k, title=title, content=text)
        return page

    @classmethod
    def all_pages(cls):
        from portal.legal_defaults import PAGES
        return [cls.get(k) for k, _t, _u, _x in PAGES]

    @property
    def url_name(self):
        from portal.legal_defaults import PAGES
        return next(u for k, _t, u, _x in PAGES if k == self.key)


class SiteTheme(models.Model):
    """Colors, fonts and text size of the public website (Super Admin →
    Theme & Colors). Only what was changed is stored; empty = the original
    look. See admin_dashboard/theme.py."""
    colors = models.JSONField(default=dict, blank=True)
    heading_font = models.CharField(max_length=30, blank=True)
    body_font = models.CharField(max_length=30, blank=True)
    text_size = models.CharField(max_length=10, blank=True)
    # also use the changed colors / fonts in the dashboards
    apply_super_admin = models.BooleanField(default=False)
    apply_office_rep = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Website theme"
        verbose_name_plural = "Website theme"

    def __str__(self):
        return "Website theme"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_default(self):
        return not (self.colors or self.heading_font or self.body_font or self.text_size
                    or self.apply_super_admin or self.apply_office_rep)