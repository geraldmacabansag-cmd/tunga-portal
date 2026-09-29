from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random


class CitizenProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mobile_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class EmailOTP(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["email", "code"])]

    def __str__(self):
        return f"{self.email} — {self.code}"

    @staticmethod
    def generate_code():
        return f"{random.randint(0, 999999):06d}"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @classmethod
    def issue(cls, email):
        cls.objects.filter(email=email, is_used=False).update(is_used=True)
        code = cls.generate_code()
        return cls.objects.create(email=email, code=code)

    @classmethod
    def verify(cls, email, code):
        otp = (cls.objects
               .filter(email=email, code=code, is_used=False)
               .order_by('-created_at')
               .first())
        if not otp:
            return False
        if otp.is_expired():
            return False
        otp.is_used = True
        otp.save(update_fields=["is_used"])
        return True