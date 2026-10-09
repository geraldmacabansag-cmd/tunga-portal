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
    # Shown under "MUNICIPALITY OF TUNGA" in the public site header (Website Settings → Appearance)
    site_tagline = models.CharField(max_length=120, default=DEFAULT_TAGLINE, blank=True)
    # How long each announcement stays in the bar at the very top of the public
    # site before the next one shows (Website Settings → Appearance). In seconds.
    ticker_interval_seconds = models.PositiveIntegerField(default=2)
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
    def ticker_interval_unit(self):
        """'minutes' when the interval is a whole number of minutes, else 'seconds'."""
        s = self.ticker_interval_seconds or 2
        return "minutes" if s >= 60 and s % 60 == 0 else "seconds"

    @property
    def ticker_interval_value(self):
        s = self.ticker_interval_seconds or 2
        return s // 60 if self.ticker_interval_unit == "minutes" else s

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
    email_address = models.EmailField(blank=True, help_text="The verified sender email in Brevo")
    app_password_encrypted = models.TextField(blank=True)  # unused since the switch to Brevo — kept to avoid a destructive migration
    api_key_encrypted = models.TextField(blank=True)
    is_configured = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

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

    COLOR_CHOICES = [
        ("red", "Red"),
        ("navy", "Navy"),
        ("teal", "Teal"),
        ("orange", "Orange"),
        ("purple", "Purple"),
        ("gray", "Gray"),
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


class AboutOfficial(models.Model):
    """One official card shown in the About page's "Our Officials" strip.
    Deliberately separate from OfficeRepresentative (the Offices app's
    functional office-dashboard accounts) — this is just the public roster
    photo/name/title, same as the page's original hardcoded cards."""
    name = models.CharField(max_length=150)
    position = models.CharField(max_length=150)
    photo = models.ImageField(upload_to="about/officials/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} ({self.position})"


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