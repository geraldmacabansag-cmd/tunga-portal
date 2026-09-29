from admin_dashboard.email_utils import send_via_configured_provider
from .models import EmailOTP


def _send_otp(email, subject, intro_line):
    otp = EmailOTP.issue(email)

    plain_body = (
        f"Your verification code is: {otp.code}\n\n"
        "This code expires in 10 minutes. If you didn't request this, "
        "you can safely ignore this email."
    )
    html_body = f"""
    <div style="font-family:sans-serif;max-width:420px;">
      <h2 style="margin-bottom:4px;">Verify your email</h2>
      <p style="color:#555;">{intro_line}</p>
      <p style="font-size:32px;font-weight:700;letter-spacing:6px;margin:20px 0;">{otp.code}</p>
      <p style="color:#888;font-size:13px;">This code expires in 10 minutes. If you didn't request this, you can safely ignore this email.</p>
    </div>
    """

    return send_via_configured_provider(subject, plain_body, html_body, email)


def send_signup_otp(email):
    return _send_otp(
        email,
        subject="Your Tunga Portal verification code",
        intro_line="Use this code to finish creating your Tunga Portal account:",
    )


def send_password_reset_otp(email):
    return _send_otp(
        email,
        subject="Your Tunga Portal password reset code",
        intro_line="Use this code to reset your Tunga Portal account password:",
    )