from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User
from offices.models import Office


class OfficeRepresentative(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="office_rep")
    office = models.OneToOneField(Office, on_delete=models.CASCADE, related_name="representative")
    position = models.CharField(max_length=100, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="rep_photos/", blank=True, null=True)   # ADD THIS LINE

    # Notification preferences (My Account page). Account activated/
    # deactivated notices are always sent and have no switch.
    notify_approvals = models.BooleanField(default=True)        # submission approved / returned / rejected
    notify_messages = models.BooleanField(default=True)         # new message from the Super Admin
    notify_weekly_summary = models.BooleanField(default=False)  # weekly views & activity digest
    notify_announcements = models.BooleanField(default=True)    # announcements posted by the LGU Super Admin
    last_weekly_summary_at = models.DateTimeField(null=True, blank=True)

    @property
    def unread_notifications_count(self):
        return self.notifications.filter(is_read=False).count()

    @property
    def recent_notifications(self):
        return self.notifications.order_by('-created_at')[:5]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.office}"

class PhotoGalleryMixin:
    """For Announcement / NewsUpdate / Event: all of the item's photos — the
    main image (cover) first, then the extra photos (ContentPhoto). Used for
    the collage + slider on the public site."""
    cover_field = "image"

    @property
    def gallery_photos(self):
        photos = []
        cover = getattr(self, self.cover_field, None)
        if cover:
            photos.append({"id": None, "url": cover.url})
        if self.pk:
            for p in self.extra_photos.all():
                if p.image:
                    photos.append({"id": p.id, "url": p.image.url})
        return photos

    @property
    def gallery_urls_json(self):
        """Every photo's address as JSON, for the slider on the public site."""
        import json
        return json.dumps([p["url"] for p in self.gallery_photos])

    @property
    def extra_photos_json(self):
        """The extra photos as JSON, for the edit forms ([{"id":…, "url":…}])."""
        import json
        return json.dumps([p for p in self.gallery_photos if p["id"]])


class Announcement(PhotoGalleryMixin, models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("reject", "Reject"),
        ("returned", "Returned"),
        ("archive", "Archived"),
    ]

    PRIORITY_CHOICES = [
        ("Normal", "Normal"),
        ("Low", "Low"),
        ("High", "High"),
        ("Urgent", "Urgent"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="announcements"
    )

    title = models.CharField(max_length=255)

    subtitle = models.CharField(
        max_length=255,
        blank=True
    )

    category = models.CharField(
        max_length=100,
        blank=True
    )

    content = models.TextField(
        blank=True
    )

    image = models.ImageField(
        upload_to="announcements/",
        blank=True,
        null=True
    )

    author = models.CharField(
        max_length=255,
        blank=True
    )

    date_posted = models.DateField(
        null=True,
        blank=True
    )

    expiration_date = models.DateTimeField(
        null=True,
        blank=True
    )

    last_updated = models.DateTimeField(auto_now=True)

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="Normal"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    admin_note = models.TextField(blank=True)

    # Set only by a Super Admin; shows this announcement in the "Pinned
    # Notice" box on the public Announcements tab, regardless of its date.
    is_pinned = models.BooleanField(default=False)

    @classmethod
    def public(cls):
        """Announcements the public may see: published and not past their
        expiration date (no expiration date = never expires)."""
        return cls.objects.filter(status="published").filter(
            Q(expiration_date__isnull=True) | Q(expiration_date__gt=timezone.now())
        )

    views = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title

class NewsUpdate(PhotoGalleryMixin, models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("reject", "Reject"),
        ("returned", "Returned"),
        ("archive", "Archived"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="news_updates"
    )

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="news/", blank=True, null=True)
    author = models.CharField(max_length=255, blank=True)
    date_published = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    source = models.CharField(max_length=255, blank=True)
    tags = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Event(PhotoGalleryMixin, models.Model):
    cover_field = "poster"


    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("reject", "Reject"),
        ("returned", "Returned"),
        ("archive", "Archived"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="events"
    )

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    event_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    location = models.CharField(max_length=255, blank=True)
    organizer = models.CharField(max_length=255, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_info = models.CharField(max_length=255, blank=True)

    poster = models.ImageField(upload_to="events/", blank=True, null=True)

    # When true, this event is pinned as the "Featured Event" hero on the
    # public Events tab instead of just falling in wherever its date puts it.
    # Only the Super Admin can set this (office reps have no control for it).
    is_featured = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Album(models.Model):
    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="albums"
    )
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Set by the Super Admin only, to control the "Featured Albums" row on
    # the public Gallery page. Office reps have no UI to set this.
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def cover(self):
        """The album's cover thumbnail — the first photo ever uploaded to it."""
        return self.photos.order_by('created_at').first()


class Photo(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("reject", "Reject"),
        ("returned", "Returned"),
        ("archive", "Archived"),
    ]

    # Used to power the category filter pills on the public Gallery page.
    # Left as a plain freeform field (like Announcement.category /
    # Event.category elsewhere in this file) rather than DB-enforced
    # choices, so new categories can be introduced later without a
    # migration; CATEGORY_CHOICES is just what the upload forms offer.
    CATEGORY_CHOICES = [
        ("Events", "Events"),
        ("Community", "Community"),
        ("Tourism", "Tourism"),
        ("Governance", "Governance"),
        ("Infrastructure", "Infrastructure"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="photos"
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        related_name="photos",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="gallery/")
    category = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Service(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("reject", "Reject"),
        ("returned", "Returned"),
        ("archive", "Archived"),
    ]


    CATEGORY_CHOICES = [
        ("permits", "Permits & Licensing"),
        ("certificates", "Certificates & Documents"),
        ("registration", "Registration"),
        ("assistance", "Public Assistance"),
        ("complaints", "Complaints & Inquiries"),
        ("appointments", "Appointments"),
        ("financial", "Financial Services"),
        ("other", "Other"),
    ]

    ICON_CHOICES = [
        ("fa-solid fa-file-signature", "Document / Signature"),
        ("fa-solid fa-id-card", "ID Card"),
        ("fa-solid fa-hands-holding-circle", "Public Assistance"),
        ("fa-solid fa-comments", "Complaints / Inquiries"),
        ("fa-solid fa-star", "Special Requests"),
        ("fa-solid fa-bullhorn", "Proclamations / Announcements"),
        ("fa-regular fa-calendar-check", "Appointments"),
        ("fa-solid fa-briefcase", "Business / Permits"),
        ("fa-solid fa-house", "Housing / Residency"),
        ("fa-solid fa-heart-pulse", "Health Services"),
        ("fa-solid fa-graduation-cap", "Education / Scholarship"),
        ("fa-solid fa-tree", "Environment / Agriculture"),
        ("fa-solid fa-shield-halved", "Peace & Order"),
        ("fa-solid fa-money-check-dollar", "Financial / Treasury"),
        ("fa-solid fa-gavel", "Legal Services"),
    ]

    SERVICE_SCOPE_CHOICES = [
        ("internal", "Internal"),
        ("external", "External"),
    ]

    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="services")

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    icon = models.CharField(max_length=60, choices=ICON_CHOICES, default="fa-solid fa-file-signature")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")  
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order on the office's public page. Lower numbers show first.",
    )
    admin_note = models.TextField(blank=True)
    reminders = models.TextField(blank=True)  # one reminder per line

    availability = models.CharField(max_length=150, blank=True)  # e.g. "Monday - Friday, 8:00 AM - 5:00 PM"
    processing_time = models.CharField(max_length=100, blank=True)  # e.g. "3-5 business days"

    division = models.CharField(max_length=150, blank=True)  # office or division that handles this service
    classification = models.CharField(max_length=50, blank=True)  # e.g. "Simple" or "Complex"
    transaction_type = models.CharField(max_length=50, blank=True)  # comma-separated: G2G, G2B, G2C
    who_may_avail = models.CharField(max_length=255, blank=True)
    service_scope = models.CharField(max_length=10, choices=SERVICE_SCOPE_CHOICES, blank=True)  # "internal", "external", or blank for none
    legal_basis = models.TextField(blank=True)  # Legal Basis (if applicable)
    schedule_of_service = models.CharField(max_length=255, blank=True)  # Schedule of Service (if applicable)

    published_at = models.DateTimeField(auto_now_add=True)  # when the service was created/submitted (used by the approval queue)
    updated_at = models.DateTimeField(auto_now=True)  # last time the service was saved
    approved_at = models.DateTimeField(null=True, blank=True)  # when the Super Admin approved/published it

    TRANSACTION_TYPE_LABELS = {
        "G2G": "G2G – Government to Government",
        "G2B": "G2B – Government to Business",
        "G2C": "G2C – Government to Citizen",
    }

    @property
    def transaction_type_list(self):
        return [t for t in self.transaction_type.split(",") if t]

    @property
    def transaction_type_display(self):
        return ", ".join(self.TRANSACTION_TYPE_LABELS.get(t, t) for t in self.transaction_type_list)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class ServiceEditSettings(models.Model):
    """Site-wide switch, not per-service: controls whether ANY office
    representative can edit a service's basic info (name, description,
    division, classification, type of transaction, who may avail,
    internal/external, icon) across the whole site. Toggled from a single
    switch on the Super Admin's Services page. Singleton — always use
    get_solo() rather than querying/creating rows directly."""
    editing_enabled = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service Edit Settings"
        verbose_name_plural = "Service Edit Settings"

    def __str__(self):
        return "Service Edit Settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class ProcessStep(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="steps")

    order = models.DecimalField(max_digits=6, decimal_places=2, default=1)  # Client Step Number, entered by the rep — allows 1.1, 1.2, etc.
    title = models.TextField()  # Client Step Name
    description = models.TextField(blank=True)

    agency_action = models.TextField(blank=True)
    fee = models.TextField(blank=True)  # Fees to be Paid — any text, any length (e.g. "₱50.00 per copy; free for senior citizens")
    processing_time = models.CharField(max_length=150, blank=True)  # free text, e.g. "5 minutes", "3-5 days", "Same day"
    person_responsible = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.order}. {self.title}"

class DownloadableForm(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("reject", "Reject"),
        ("returned", "Returned"),
        ("archive", "Archived"),
    ]

    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="downloadable_forms")
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, related_name="forms", null=True, blank=True)

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to="downloadable_forms/")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    uploaded_by = models.CharField(max_length=150, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date_uploaded"]

    @property
    def is_fillable(self):
        return self.fields.exists()

    def __str__(self):
        return self.title


class FormField(models.Model):
    """
    One input field positioned on top of a specific page of a
    DownloadableForm's PDF. x/y/width/height are stored as fractions
    (0.0–1.0) of the page's width/height, not pixels — this keeps the
    position correct no matter what size the PDF is rendered at,
    whether that's the builder canvas, the public fill page, or the
    final stamped output.
    """

    FIELD_TYPE_CHOICES = [
        ("text", "Short Text"),
        ("date", "Date"),
        ("number", "Number"),
        ("checkbox", "Checkbox"),
    ]

    form = models.ForeignKey(DownloadableForm, on_delete=models.CASCADE, related_name="fields")
    label = models.CharField(max_length=150)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default="text")
    required = models.BooleanField(default=True)

    page_number = models.PositiveIntegerField(default=1)  # 1-indexed
    x = models.FloatField()       # left edge, as a fraction of page width
    y = models.FloatField()       # top edge, as a fraction of page height
    width = models.FloatField(default=0.2)
    height = models.FloatField(default=0.03)

    order = models.PositiveIntegerField(default=0)

    # ---- How the typed answer looks (set in the Make Fillable builder) ----
    ALIGN_CHOICES = [("left", "Left"), ("center", "Center"), ("right", "Right")]
    V_ALIGN_CHOICES = [("bottom", "Bottom"), ("middle", "Middle"), ("top", "Top")]

    text_align = models.CharField(max_length=10, choices=ALIGN_CHOICES, default="left")
    v_align = models.CharField(max_length=10, choices=V_ALIGN_CHOICES, default="bottom")
    font_size = models.PositiveSmallIntegerField(default=0)  # points; 0 = auto-fit the box
    bold = models.BooleanField(default=False)
    text_color = models.CharField(max_length=7, default="#000000")
    uppercase = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["page_number", "order", "id"]

    def __str__(self):
        return f"{self.label} ({self.form.title}, page {self.page_number})"


class FormSubmission(models.Model):
    form = models.ForeignKey(DownloadableForm, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="form_submissions")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.form.title} — {self.user.get_full_name() or self.user.username}"


class FormSubmissionValue(models.Model):
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name="values")
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name="submitted_values")
    value = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.field.label}: {self.value}"

class Requirement(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="requirements")

    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    where_to_secure = models.CharField(max_length=200, blank=True)
    transaction_type = models.CharField(max_length=100, blank=True)  # groups this requirement under a type of transaction, if applicable — free text, matched by exact text
    is_required = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["transaction_type", "order", "created_at"]

    def __str__(self):
        return self.title
    
class Fee(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="fees")

    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return self.title

class Notification(models.Model):

    LEVEL_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("danger", "Danger"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="info")
    link_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class ActivityLog(models.Model):

    CATEGORY_CHOICES = [
        ("content", "Content"),
        ("account", "Account"),
        ("security", "Security"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="content")
    icon = models.CharField(max_length=50, default="fa-solid fa-circle-info")
    icon_color = models.CharField(max_length=20, default="var(--blue-600)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


def log_activity(rep, title, description="", category="content", icon="fa-solid fa-circle-info", icon_color="var(--blue-600)"):
    """Call this from any view right after a successful action to record it in the audit trail."""
    ActivityLog.objects.create(
        representative=rep,
        title=title,
        description=description,
        category=category,
        icon=icon,
        icon_color=icon_color,
    )


class Message(models.Model):
    """One chat message between an Office Representative and the Super Admin.

    Each representative has exactly one conversation with the Super Admin,
    so the conversation is simply "all messages for this representative".
    read_at is set when the *recipient* opens it (a rep's messages are read by
    the Super Admin, the Super Admin's messages are read by the rep)."""

    SENDER_REP = "rep"
    SENDER_ADMIN = "admin"
    SENDER_CHOICES = [
        (SENDER_REP, "Office Representative"),
        (SENDER_ADMIN, "Super Admin"),
    ]

    representative = models.ForeignKey(
        OfficeRepresentative,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["representative", "id"], name="msg_rep_id_idx"),
        ]

    def __str__(self):
        return f"{self.get_sender_display()} -> {self.representative.office}: {self.body[:40]}"

class OrgChartNode(models.Model):
    """One box on an office's Organizational Chart: a person (name, position,
    photo) or a section/unit title (e.g. "Personal Staff Section"). `parent`
    is the box it reports to — no parent means it's at the top of the chart."""

    KIND_PERSON = "person"
    KIND_SECTION = "section"
    KIND_CHOICES = [(KIND_PERSON, "Person"), (KIND_SECTION, "Section / Unit")]

    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="org_chart_nodes")
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_PERSON)
    name = models.CharField(max_length=150)                # person's name, or the section title
    position = models.CharField(max_length=200, blank=True)  # e.g. "Municipal Administrator"
    photo = models.ImageField(upload_to="org_chart/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)         # left-to-right among boxes with the same parent
    # Where the rep dragged the box on the chart (pixels). Empty = automatic
    # place (it follows the box above it in the tidy tree layout).
    pos_x = models.IntegerField(null=True, blank=True)
    pos_y = models.IntegerField(null=True, blank=True)
    # Look of the box, chosen in the editor. Missing keys = default look.
    # shape (circle/rounded/square/none), border, fill, text (#rrggbb colors),
    # line (#rrggbb), line_style (solid/dashed/dotted), size (s/m/l), case (upper/normal)
    style = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} ({self.office})"

    @property
    def initials(self):
        parts = [p for p in self.name.replace(".", " ").split() if p[:1].isalpha()]
        return ((parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")) if parts else "?").upper()


class OrgChartSettings(models.Model):
    """Per-office settings of the Organizational Chart. show_on_office_page:
    the rep chose to display the chart at the bottom of the public office page."""
    office = models.OneToOneField(Office, on_delete=models.CASCADE, related_name="org_chart_settings")
    show_on_office_page = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Org chart settings · {self.office}"

    @classmethod
    def for_office(cls, office):
        obj, _ = cls.objects.get_or_create(office=office)
        return obj


class ContentPhoto(models.Model):
    """An extra photo of an announcement, a news post or an event (on top of
    its main image / poster). Exactly one of the three links is set."""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, null=True, blank=True, related_name="extra_photos")
    news = models.ForeignKey(NewsUpdate, on_delete=models.CASCADE, null=True, blank=True, related_name="extra_photos")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name="extra_photos")
    image = models.ImageField(upload_to="content_photos/")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Photo #{self.pk}"