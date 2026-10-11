"""Security limits for logins, verification codes and code emails.

1. Wrong passwords / wrong codes
   After 5 wrong tries on one account, that account is blocked for
   15 minutes. After 20 wrong tries from one computer (IP address), that
   computer is blocked for 15 minutes. (A computer gets more tries than an
   account because a whole office can share one internet connection.)

2. Code emails (sign-up, forgot password, change password)
   One code per email address per minute, at most 5 per hour, and at most
   10 per hour from one computer. This keeps someone from flooding a
   person's inbox or using up the free Brevo email allowance.

Everything is stored in portal.models.AttemptLog (old rows are deleted
automatically), so the limits work the same on every server.
"""
import math
from datetime import timedelta

from django.utils import timezone

ACCOUNT_MAX_TRIES = 5
COMPUTER_MAX_TRIES = 20
LOCK_MINUTES = 15

CODES_PER_HOUR = 5
CODES_PER_HOUR_PER_COMPUTER = 10


def client_ip(request):
    """The visitor's IP address. On Render / DigitalOcean the site sits behind
    a proxy, which puts the real address first in X-Forwarded-For."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:60]
    return (request.META.get("REMOTE_ADDR") or "unknown")[:60]


def _clean(value):
    return (value or "").strip().lower()[:150]


def _keys(kind, request, account):
    keys = {"ip": f"{kind}:ip:{client_ip(request)}"}
    if account:
        keys["acct"] = f"{kind}:acct:{_clean(account)}"
    return keys


def _cleanup():
    from .models import AttemptLog
    AttemptLog.objects.filter(created_at__lt=timezone.now() - timedelta(days=1)).delete()


def _lock_left(key, limit):
    """Minutes left on a lock for this key (0 = not locked). A key is locked
    for LOCK_MINUTES after its `limit`-th wrong try within LOCK_MINUTES."""
    from .models import AttemptLog
    now = timezone.now()
    window = timedelta(minutes=LOCK_MINUTES)
    times = list(AttemptLog.objects.filter(key=key, created_at__gte=now - 2 * window)
                 .order_by("-created_at").values_list("created_at", flat=True)[:limit])
    if len(times) < limit:
        return 0
    latest, oldest = times[0], times[-1]
    if latest - oldest > window or latest + window <= now:
        return 0
    return max(1, math.ceil((latest + window - now).total_seconds() / 60))


def locked_minutes(kind, request, account=None):
    """How many minutes this account or computer must still wait (0 = OK)."""
    keys = _keys(kind, request, account)
    waits = [_lock_left(keys["ip"], COMPUTER_MAX_TRIES)]
    if "acct" in keys:
        waits.append(_lock_left(keys["acct"], ACCOUNT_MAX_TRIES))
    return max(waits)


def tries_left(kind, request, account):
    from .models import AttemptLog
    since = timezone.now() - timedelta(minutes=LOCK_MINUTES)
    used = AttemptLog.objects.filter(key=_keys(kind, request, account)["acct"], created_at__gte=since).count()
    return max(0, ACCOUNT_MAX_TRIES - used)


def record_failure(kind, request, account=None):
    from .models import AttemptLog
    _cleanup()
    for key in _keys(kind, request, account).values():
        AttemptLog.objects.create(key=key)


def clear_failures(kind, account):
    """After a correct password/code, that account starts fresh."""
    from .models import AttemptLog
    AttemptLog.objects.filter(key=f"{kind}:acct:{_clean(account)}").delete()


def lock_message(minutes):
    unit = "minute" if minutes == 1 else "minutes"
    return (f"Too many wrong tries. For your security, this is blocked for "
            f"{minutes} {unit}. Please try again later.")


def wrong_message(text, kind, request, account):
    """The normal error, plus how many tries are left when it gets low
    (or the "blocked" message if this was the last try)."""
    minutes = locked_minutes(kind, request, account)
    if minutes:
        return lock_message(minutes)
    left = tries_left(kind, request, account)
    if 0 < left <= 3:
        text += f" You have {left} {'try' if left == 1 else 'tries'} left before it is blocked for {LOCK_MINUTES} minutes."
    return text


# ---------------------------------------------------------------------------
# Verification codes
# ---------------------------------------------------------------------------

def check_code(request, email, code, kind="code"):
    """Checks a 6-digit email code with the wrong-try limit.
    Returns None when the code is correct, otherwise the error to show."""
    from .models import EmailOTP
    minutes = locked_minutes(kind, request, email)
    if minutes:
        return lock_message(minutes)
    if EmailOTP.verify(email, code):
        clear_failures(kind, email)
        return None
    record_failure(kind, request, email)
    minutes = locked_minutes(kind, request, email)
    if minutes:
        # The code that was being guessed can't be used any more.
        EmailOTP.objects.filter(email=email, is_used=False).update(is_used=True)
        return lock_message(minutes) + " Request a new code after that."
    return wrong_message("That verification code is incorrect or has expired.", kind, request, email)


def code_send_problem(request, email):
    """None when a code email may be sent now, otherwise the reason it can't.
    Call this right before sending; it also counts the send."""
    from .models import AttemptLog, EmailOTP
    now = timezone.now()
    email = _clean(email)

    last = EmailOTP.objects.filter(email=email).order_by("-created_at").values_list("created_at", flat=True).first()
    if last and now - last < timedelta(minutes=1):
        seconds = max(1, 60 - int((now - last).total_seconds()))
        return f"A code was just sent. Please wait {seconds} seconds before asking for another one."

    hour_ago = now - timedelta(hours=1)
    sent = list(EmailOTP.objects.filter(email=email, created_at__gte=hour_ago)
                .order_by("created_at").values_list("created_at", flat=True))
    if len(sent) >= CODES_PER_HOUR:
        minutes = max(1, math.ceil((sent[0] + timedelta(hours=1) - now).total_seconds() / 60))
        return (f"Too many codes were requested for this email. Please wait {minutes} minutes, "
                "or use the last code you received.")

    ip_key = f"sendcode:ip:{client_ip(request)}"
    if AttemptLog.objects.filter(key=ip_key, created_at__gte=hour_ago).count() >= CODES_PER_HOUR_PER_COMPUTER:
        return "Too many codes were requested from this device. Please try again in an hour."

    _cleanup()
    AttemptLog.objects.create(key=ip_key)
    return None