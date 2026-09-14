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