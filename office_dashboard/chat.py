"""Messages between an Office Representative and the Super Admin: what one
message looks like to each side, and the actions of its "⋮" menu.

Used by office_dashboard/views.py (rep_messages_*) and
admin_dashboard/views.py (admin_messages_*). The page script is
static/js/messages.js.

  Reply           send a message that quotes another one
  Copy            (in the browser only)
  Edit            your own message, within EDIT_MINUTES of sending it
  Unsend          your own message: removed for both sides ("Message unsent"),
                  the text is erased
  Delete for me   hide any message from your own view only (the other side
                  still sees it)

Open chats check every few seconds: new messages come by id (?after=), and
messages that changed (edited, unsent, seen, deleted for me) come by
updated_at (?since=).
"""
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Message

EDIT_MINUTES = 15
MAX_LENGTH = 2000


def _time(dt):
    return timezone.localtime(dt).strftime("%b %d, %Y · %I:%M %p").replace(" 0", " ")


def hidden_field(viewer):
    return "hidden_for_rep" if viewer == Message.SENDER_REP else "hidden_for_admin"


def can_edit(m, viewer):
    return (m.sender == viewer and not m.unsent_at
            and timezone.now() - m.created_at <= timedelta(minutes=EDIT_MINUTES))


def serialize(m, viewer):
    """One message as the viewer ("rep" or "admin") sees it."""
    reply = None
    if m.reply_to_id:
        r = m.reply_to
        if r is not None:
            reply = {
                "id": r.id,
                "sender": r.sender,
                "body": "" if r.unsent_at else r.body[:160],
                "unsent": bool(r.unsent_at),
            }
    return {
        "id": m.id,
        "sender": m.sender,
        "body": "" if m.unsent_at else m.body,
        "time": _time(m.created_at),
        "edited": bool(m.edited_at) and not m.unsent_at,
        "unsent": bool(m.unsent_at),
        "read": bool(m.read_at),
        "read_time": _time(m.read_at) if m.read_at else "",
        "reply": reply,
        "can_edit": can_edit(m, viewer),
        "hidden": getattr(m, hidden_field(viewer)),
    }


def sync(rep, viewer, after, since):
    """New messages after the id `after`, and earlier messages changed after
    the time `since` (ISO text from the last answer). Returns the JSON data."""
    now = timezone.now()
    qs = rep.chat_messages.select_related("reply_to")
    new = [serialize(m, viewer) for m in qs.filter(id__gt=after).exclude(**{hidden_field(viewer): True})]
    changed = []
    try:   # a "+" in the time can arrive as a space when not URL-encoded
        since_dt = parse_datetime(since.strip().replace(" ", "+")) if since else None
    except ValueError:
        since_dt = None
    if since_dt is not None and after:
        if timezone.is_naive(since_dt):
            since_dt = timezone.make_aware(since_dt)
        # a little overlap, so nothing slips between two checks
        changed = [serialize(m, viewer) for m in qs.filter(id__lte=after, updated_at__gte=since_dt - timedelta(seconds=2))]
    return {"messages": new, "changed": changed, "now": now.isoformat(),
            "edit_minutes": EDIT_MINUTES}


def mark_read(rep, viewer):
    """The viewer opened the chat: the other side's messages are read ("Seen")."""
    other = Message.SENDER_ADMIN if viewer == Message.SENDER_REP else Message.SENDER_REP
    now = timezone.now()
    rep.chat_messages.filter(sender=other, read_at__isnull=True).update(read_at=now, updated_at=now)


def create(rep, viewer, body, reply_to_id=None):
    """Returns (message, error)."""
    body = (body or "").strip()
    if not body:
        return None, "Type a message first."
    if len(body) > MAX_LENGTH:
        return None, f"Messages are limited to {MAX_LENGTH} characters."
    reply_to = None
    if reply_to_id and str(reply_to_id).isdigit():
        reply_to = rep.chat_messages.filter(pk=int(reply_to_id)).first()
    m = Message.objects.create(representative=rep, sender=viewer, body=body, reply_to=reply_to)
    return m, None


def act(rep, viewer, pk, action, body=""):
    """edit / unsend / delete (for me) on one message. Returns (message, error)."""
    m = rep.chat_messages.select_related("reply_to").filter(pk=pk).first()
    if m is None:
        return None, "That message no longer exists."
    now = timezone.now()
    if action == "delete":
        setattr(m, hidden_field(viewer), True)
        m.save(update_fields=[hidden_field(viewer), "updated_at"])
        return m, None
    if m.sender != viewer:
        return None, "You can only change your own messages."
    if m.unsent_at:
        return None, "This message was already unsent."
    if action == "unsend":
        m.unsent_at = now
        m.body = ""
        if m.read_at is None:
            m.read_at = now          # an unsent message never counts as unread
        m.save(update_fields=["unsent_at", "body", "read_at", "updated_at"])
        return m, None
    if action == "edit":
        if not can_edit(m, viewer):
            return None, f"Messages can only be edited within {EDIT_MINUTES} minutes of sending them."
        body = (body or "").strip()
        if not body:
            return None, "The message can't be empty. Use Unsend to remove it."
        if len(body) > MAX_LENGTH:
            return None, f"Messages are limited to {MAX_LENGTH} characters."
        if body != m.body:
            m.body = body
            m.edited_at = now
            m.save(update_fields=["body", "edited_at", "updated_at"])
        return m, None
    return None, "Unknown action."