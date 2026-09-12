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

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.office}"

class Announcement(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("draft", "Draft"),
        ("returned", "Returned"),
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
        ("draft", "Draft"),
        ("returned", "Returned"),
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
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Event(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("completed", "Completed"),
        ("returned", "Returned"),
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


class Photo(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
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
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Service(models.Model):

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

    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="services")

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    icon = models.CharField(max_length=60, choices=ICON_CHOICES, default="fa-solid fa-file-signature")

    availability = models.CharField(max_length=150, blank=True)  # e.g. "Monday - Friday, 8:00 AM - 5:00 PM"
    processing_time = models.CharField(max_length=100, blank=True)  # e.g. "3-5 business days"

    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

class ProcessStep(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="steps")

    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.order}. {self.title}"

class DownloadableForm(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("published", "Published"),
        ("completed", "Completed"),
        ("returned", "Returned"),
    ]

    office = models.ForeignKey(Office, on_delete=models.CASCADE, related_name="downloadable_forms")

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    file = models.FileField(upload_to="downloadable_forms/")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    uploaded_by = models.CharField(max_length=150, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date_uploaded"]

    def __str__(self):
        return self.title

class Requirement(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="requirements")

    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

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





