from django.db import models

class Office(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=150)

    logo = models.ImageField(upload_to="office_logos/", blank=True, null=True)
    about = models.TextField(blank=True)
    description = models.TextField(blank=True)
    head_name = models.CharField(max_length=255, blank=True)
    position_title = models.CharField(max_length=255, blank=True)
    office_hours = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=100, blank=True)

    # These six are optional ("if applicable") — not every office has a
    # formal mandate/vision/etc., so they're left blank rather than required.
    service_pledge = models.TextField(blank=True)
    mandate = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    goal = models.TextField(blank=True)
    objective = models.TextField(blank=True)

    hero_image = models.ImageField(
        upload_to="office_hero/",
        blank=True,
        null=True,
        help_text="Banner image shown at the top of this office's public page. Defaults to the standard municipal hall photo when empty.",
    )

    is_visible = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this office from the public Offices page."
    )

    def __str__(self):
        return self.name