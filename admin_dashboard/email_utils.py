"""Every email the website sends goes through send_via_configured_provider().

1. Brevo (main sender, HTTPS API, 300 emails a day on the free plan)
2. If Brevo fails — daily limit used up, Brevo down, key wrong — the same
   email is sent through the BACKUP sender chosen in Super Admin → System
   Settings:
     - Mailjet (HTTPS API, 200 a day free) — works on Render's free plan
     - Gmail   (SMTP with an App Password, ~500 a day) — only on a host that
       allows SMTP; Render's FREE plan blocks SMTP ports 25/465/587.

Returns (True, None) when one of them sent it, otherwise (False, "reason").
"""
import requests
from django.db.models import F
from django.utils import timezone


def send_via_configured_provider(subject, plain_body, html_body, to_email):
    from .models import EmailProviderSettings
    s = EmailProviderSettings.get_solo()

    ok, error = send_with_brevo(s, subject, plain_body, html_body, to_email)
    if ok:
        return True, None

    from .alerts import email_backup_used, email_failed   # Super Admin bell
    if s.backup_ready:
        ok2, error2 = send_with_backup(s, subject, plain_body, html_body, to_email)
        if ok2:
            EmailProviderSettings.objects.filter(pk=s.pk).update(
                backup_last_used=timezone.now(), backup_used_count=F("backup_used_count") + 1)
            if s.is_configured:   # Brevo is set up but failed (limit reached / down)
                email_backup_used(error or "", s.get_backup_provider_display().split(" (")[0])
            return True, None
        full = f"{error} | Backup ({s.get_backup_provider_display()}) also failed: {error2}"
        email_failed(full)
        return False, full

    if s.is_configured:
        email_failed(error or "")
    return False, error


def send_with_brevo(s, subject, plain_body, html_body, to_email):
    if not s.is_configured:
        return False, "Email provider is not configured yet. Go to Super Admin → System Settings."
    try:
        api_key = s.get_api_key()
        if not api_key:
            return False, "Stored API key could not be read (encryption key may be missing or changed)."

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {"email": s.email_address},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": plain_body,
                "htmlContent": html_body or plain_body,
            },
            timeout=15,
        )

        if response.status_code in (200, 201):
            return True, None
        return False, f"Brevo rejected the request ({response.status_code}): {response.text[:300]}"

    except Exception as e:
        return False, f"Brevo: {e}"


def send_with_backup(s, subject, plain_body, html_body, to_email):
    try:
        secret = s.get_backup_secret()
        if not secret:
            return False, "The backup password/secret key could not be read."
        if s.backup_provider == "mailjet":
            return _send_mailjet(s.get_backup_api_key(), secret, s.backup_email, subject, plain_body, html_body, to_email)
        if s.backup_provider == "gmail":
            return _send_gmail(s.backup_email, secret, subject, plain_body, html_body, to_email)
        return False, "No backup sender is set up."
    except Exception as e:
        return False, str(e)


def _send_mailjet(api_key, secret_key, sender, subject, plain_body, html_body, to_email):
    response = requests.post(
        "https://api.mailjet.com/v3.1/send",
        auth=(api_key, secret_key),
        json={"Messages": [{
            "From": {"Email": sender, "Name": "Municipality of Tunga"},
            "To": [{"Email": to_email}],
            "Subject": subject,
            "TextPart": plain_body,
            "HTMLPart": html_body or plain_body,
        }]},
        timeout=15,
    )
    if response.status_code == 200:
        return True, None
    return False, f"Mailjet rejected the request ({response.status_code}): {response.text[:300]}"


def _send_gmail(gmail_address, app_password, subject, plain_body, html_body, to_email):
    from django.core.mail import EmailMultiAlternatives, get_connection
    connection = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host="smtp.gmail.com", port=587, use_tls=True,
        username=gmail_address, password=app_password.replace(" ", ""),
        timeout=15, fail_silently=False,
    )
    msg = EmailMultiAlternatives(subject, plain_body, f"Municipality of Tunga <{gmail_address}>", [to_email],
                                 connection=connection)
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send()
    return True, None