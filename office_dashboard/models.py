from django.db import models
from django.contrib.auth.models import User
from offices.models import Office


class OfficeRepresentative(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="office_rep")
    office = models.OneToOneField(Office, on_delete=models.CASCADE, related_name="representative")
    position = models.CharField(max_length=100, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="rep_photos/", blank=True, null=True)   # ADD THIS LINE

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

    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to="gallery/")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title



