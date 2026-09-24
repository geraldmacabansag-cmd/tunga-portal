from django.core.mail import get_connection, EmailMultiAlternatives


def send_via_configured_provider(subject, plain_body, html_body, to_email):
    from .models import EmailProviderSettings

    settings_obj = EmailProviderSettings.get_solo()
    if not settings_obj.is_configured:
        return False, "Email provider is not configured yet. Go to Super Admin → System Settings."

    app_password = settings_obj.get_app_password()
    if not app_password:
        return False, "Stored App Password could not be read (encryption key may be missing or changed)."

    try:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend", 
            host="smtp.gmail.com",
            port=465,
            username=settings_obj.email_address,
            password=app_password,
            use_tls=True,
            timeout=15, 
        )
        message = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=settings_obj.email_address,
            to=[to_email],
            connection=connection,
        )
        if html_body:
            message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        return True, None
    except Exception as e:
        return False, str(e)