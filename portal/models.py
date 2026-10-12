from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import secrets


class CitizenProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    mobile_number = models.CharField(max_length=20, blank=True)
    # Profile picture (public site → side panel → Account). Office reps and the
    # Super Admin use the photo of their dashboard account instead — see
    # portal/profile_photo.py.
    photo = models.ImageField(upload_to="citizen_photos/", blank=True, null=True)

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
        return f"{secrets.randbelow(1000000):06d}"   # unpredictable, unlike random

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


class AttemptLog(models.Model):
    """One wrong password, one wrong code, or one code email sent. Used by
    portal/security.py to block an account or a computer for 15 minutes
    after too many wrong tries, and to limit how many code emails are sent.
    Old rows are deleted automatically."""
    key = models.CharField(max_length=200, db_index=True)   # e.g. "login:acct:juan@gmail.com" or "login:ip:1.2.3.4"
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.key} at {self.created_at:%Y-%m-%d %H:%M}"



class PortalFeedback(models.Model):
    """Feedback on using the portal itself (side menu → Rate this website):
    1–5 stars + an optional suggestion. One per user; they can update it.
    Results: Super Admin → Analytics & Reports → Portal Feedback."""
    RATING_LABELS = {5: "Excellent", 4: "Good", 3: "Okay", 2: "Poor", 1: "Very poor"}

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="portal_feedback")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.rating}/5 — {self.user.email or self.user.username}"

    @property
    def rating_label(self):
        return self.RATING_LABELS.get(self.rating, "")