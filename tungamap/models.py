from django.conf import settings
from django.db import models


class Place(models.Model):
    """A piece of infrastructure or an establishment shown on the Tunga map."""

    CATEGORY_CHOICES = [
        ("school", "School"),
        ("health", "Health"),
        ("government", "Government"),
        ("church", "Church"),
        ("market", "Market & stores"),
        ("food", "Food"),
        ("safety", "Police & fire"),
        ("finance", "Bank & remittance"),
        ("transport", "Transport"),
        ("infra", "Roads & utilities"),
        ("recreation", "Parks & sports"),
        ("other", "Other"),
    ]

    BARANGAY_CHOICES = [
        (b, b)
        for b in [
            "Astorga", "Balire", "Banawang", "San Antonio",
            "San Pedro", "San Roque", "San Vicente", "Santo Niño",
        ]
    ]

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other", db_index=True)
    barangay = models.CharField(max_length=40, choices=BARANGAY_CHOICES, blank=True)
    description = models.TextField(blank=True)
    contact = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_published = models.BooleanField(default=True, help_text="Unpublished places are only visible to map editors.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlaceImage(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="tungamap/%Y/%m/")
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Photo of {self.place}"