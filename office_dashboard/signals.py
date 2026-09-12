from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import OfficeRepresentative, log_activity


@receiver(user_logged_in)
def log_office_rep_login(sender, request, user, **kwargs):
    rep = OfficeRepresentative.objects.filter(user=user).first()
    if rep:
        log_activity(
            rep,
            "Signed in",
            "Successful login to the office dashboard",
            category="security",
            icon="fa-solid fa-right-to-bracket",
            icon_color="var(--gray-500)",
        )