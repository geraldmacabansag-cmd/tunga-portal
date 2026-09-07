from django.db import models

class Office(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    logo = models.ImageField(upload_to="office_logos/", blank=True, null=True)
    about = models.TextField(blank=True)
    description = models.TextField(blank=True)
    head_name = models.CharField(max_length=255, blank=True)
    position_title = models.CharField(max_length=255, blank=True)
    office_hours = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name