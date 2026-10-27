"""Deleting a citizen account after 30 days.

Settings -> "Delete my account" (portal.views.account_delete) does not delete
the account right away. It:
  1. saves an AccountDeletion with delete_after = now + 30 days,
  2. logs the account out on this device AND every other device,
  3. emails the person the date (if email is set up).

If the person logs in again within the 30 days (password or Google), they are
NOT logged in yet: the login page shows that the account is scheduled for
deletion, with a "Proceed anyway" button. Pressing it cancels the deletion and
logs them in (portal.views.account_restore).

After 30 days the account is deleted for good by purge_due(), which runs by
itself at most once an hour while people use the website
(PendingDeletionMiddleware), and can also run from a daily job:
    python manage.py delete_expired_accounts
"""
from datetime import timedelta
import time

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils import timezone

GRACE_DAYS = 30
SESSION_KEY = "pending_restore"     # who may press "Proceed anyway" on the login page
SESSION_MINUTES = 10                # ... for how long after the correct password


def pending_for(user):
    """The AccountDeletion of this user, or None."""
    from .models import AccountDeletion
    if not user or not getattr(user, "pk", None):
        return None
    return AccountDeletion.objects.filter(user=user).first()


def schedule(user):
    from .models import AccountDeletion
    now = timezone.now()
    req, _ = AccountDeletion.objects.update_or_create(
        user=user, defaults={"requested_at": now, "delete_after": now + timedelta(days=GRACE_DAYS)})
    return req


def cancel(user):
    from .models import AccountDeletion
    AccountDeletion.objects.filter(user=user).delete()


def logout_everywhere(user):
    """Ends every login session of this user (all phones, computers, browsers)."""
    from django.contrib.sessions.backends.db import SessionStore
    from django.core import signing
    store = SessionStore()
    uid = str(user.pk)
    gone = 0
    for s in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        try:   # read quietly (old sessions from another secret key are skipped)
            data = signing.loads(s.session_data, salt=store.key_salt, serializer=store.serializer)
        except Exception:
            continue
        if str(data.get("_auth_user_id")) == uid:
            s.delete()
            gone += 1
    return gone


def delete_now(user):
    """Deletes the account for good, with everything linked to it (profile,
    online form submissions, Google sign-in link, verification codes)."""
    from .models import CitizenProfile, EmailOTP
    profile = CitizenProfile.objects.filter(user=user).first()
    if profile and profile.photo:
        try:
            profile.photo.delete(save=False)
        except Exception:
            pass
    if user.email:
        EmailOTP.objects.filter(email__iexact=user.email).delete()
    logout_everywhere(user)
    user.delete()


def purge_due():
    """Deletes the accounts whose 30 days are over. Returns how many."""
    from .models import AccountDeletion
    n = 0
    for req in AccountDeletion.objects.filter(delete_after__lte=timezone.now()).select_related("user"):
        u = req.user
        if u.is_staff or u.is_superuser or hasattr(u, "super_admin") or hasattr(u, "office_rep"):
            req.delete()     # dashboard accounts are never deleted this way
            continue
        delete_now(u)
        n += 1
    return n


def send_notice(user, req):
    """Email: "your account will be deleted on ..." (best effort)."""
    if not user.email:
        return
    try:
        from admin_dashboard.email_utils import send_via_configured_provider
        when = timezone.localtime(req.delete_after).strftime("%B %d, %Y")
        name = user.first_name or "there"
        text = (f"Hi {name},\n\nWe received your request to delete your Tunga Portal account.\n"
                f"Your account and personal data will be deleted for good on {when}.\n\n"
                "Changed your mind? Just log in again before that date and choose \"Proceed anyway\" - "
                "the deletion is then cancelled.\n\nMunicipality of Tunga")
        send_via_configured_provider("Your Tunga Portal account will be deleted in 30 days", text, "", user.email)
    except Exception:
        pass


# ------------------------------------------------------------------ login page
def remember_pending(request, user, remember=False, next_url="home", method="password"):
    request.session[SESSION_KEY] = {"uid": user.pk, "at": int(time.time()), "remember": bool(remember),
                                    "next": next_url or "home", "method": method}


def pending_in_session(request):
    """(user, AccountDeletion, data) of the person who just entered the right
    password for an account scheduled for deletion - or (None, None, None)."""
    from django.contrib.auth.models import User
    data = request.session.get(SESSION_KEY)
    if not data:
        return None, None, None
    if time.time() - data.get("at", 0) > SESSION_MINUTES * 60:
        request.session.pop(SESSION_KEY, None)
        return None, None, None
    user = User.objects.filter(pk=data.get("uid"), is_active=True).first()
    req = pending_for(user)
    if not user or not req:
        request.session.pop(SESSION_KEY, None)
        return None, None, None
    return user, req, data


class PendingDeletionMiddleware:
    """1) At most once an hour: delete the accounts whose 30 days are over.
    2) Safety net: an account scheduled for deletion that is somehow logged
       in (e.g. Google sign-in) is logged out and sent to the login page,
       where "Proceed anyway" cancels the deletion."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if cache.add("portal:purge-deleted-accounts", 1, 3600):
                purge_due()
        except Exception:
            pass
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and pending_for(user):
            remember_pending(request, user, method="session")
            # keep the "pending" note: logout() empties the session
            note = request.session[SESSION_KEY]
            auth_logout(request)
            request.session[SESSION_KEY] = note
            messages.warning(request, "This account is scheduled for deletion. Log in to keep it.")
            return redirect("login")
        return self.get_response(request)