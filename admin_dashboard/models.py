from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class SuperAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="super_admin")
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
    phone = models.CharField(max_length=50, blank=True)
    phone_local = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    email_secondary = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    facebook_name = models.CharField(max_length=150, blank=True)
    facebook_url = models.URLField(blank=True)
    office_hours = models.CharField(max_length=150, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Contact Information"
        verbose_name_plural = "Site Contact Information"

    def __str__(self):
        return "Site Contact Information"

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

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name

    