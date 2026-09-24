import requests


def send_via_configured_provider(subject, plain_body, html_body, to_email):
    from .models import EmailProviderSettings

    settings_obj = EmailProviderSettings.get_solo()
    if not settings_obj.is_configured:
        return False, "Email provider is not configured yet. Go to Super Admin → System Settings."

    try:
        api_key = settings_obj.get_api_key()
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
                "sender": {"email": settings_obj.email_address},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": plain_body,
                "htmlContent": html_body or plain_body,
            },
            timeout=15,
        )

        if response.status_code in (200, 201):
            return True, None
        return False, f"Brevo rejected the request ({response.status_code}): {response.text}"

    except Exception as e:
        return False, str(e)