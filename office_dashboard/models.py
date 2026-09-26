from django.db import models
from django.contrib.auth.models import User
from offices.models import Office


class OfficeRepresentative(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="office_rep")
    office = models.OneToOneField(Office, on_delete=models.CASCADE, related_name="representative")
    position = models.CharField(max_length=100, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="rep_photos/", blank=True, null=True)   # ADD THIS LINE

    @property
    def unread_notifications_count(self):
        return self.notifications.filter(is_read=False).count()

    @property
    def recent_notifications(self):
        return self.notifications.order_by('-created_at')[:5]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.office}"

class Announcement(models.Model):

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

    views = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.title

class NewsUpdate(models.Model):

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

class Event(models.Model):

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

    published_at = models.DateTimeField(auto_now_add=True)

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
    fee = models.CharField(max_length=150, blank=True)  # Fees to be Paid
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

    def __str__(self):
        return self.title

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