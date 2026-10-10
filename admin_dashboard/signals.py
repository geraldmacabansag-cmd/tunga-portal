"""Creates Super Admin notifications (the bell in the dashboard top bar).

- An office submits (or resubmits) an announcement, news, event, photo,
  form or service for approval  -> "New ... waiting for approval"
- An office representative sends a message to the Super Admin -> "New message"
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse

from office_dashboard.models import (Announcement, NewsUpdate, Event, Photo,
                                     DownloadableForm, Service, Message)
from .models import SuperAdmin, AdminNotification

LGU_SLUG = "lgu-super-admin"

# model -> (label shown in the notification, Approval Center type, icon)
WATCHED = {
    Announcement: ("announcement", "Announcement", "fa-solid fa-bullhorn"),
    NewsUpdate: ("news update", "News", "fa-regular fa-newspaper"),
    Event: ("event", "Event", "fa-regular fa-calendar"),
    Photo: ("photo", "Gallery", "fa-regular fa-image"),
    DownloadableForm: ("form", "Form", "fa-solid fa-file-arrow-down"),
    Service: ("service", "Service", "fa-solid fa-list-check"),
}


def notify_super_admins(title, description="", level="info", icon="fa-regular fa-bell", link_url=""):
    AdminNotification.objects.bulk_create([
        AdminNotification(user_id=uid, title=title[:255], description=description[:500],
                          level=level, icon=icon, link_url=link_url)
        for uid in SuperAdmin.objects.values_list("user_id", flat=True)
    ])


def _office_of(obj):
    office = getattr(obj, "office", None)
    if office is None and getattr(obj, "representative_id", None):
        office = obj.representative.office
    return office


def _remember_old_status(sender, instance, **kwargs):
    instance._old_status = None
    if kwargs.get("raw"):
        return  # loading a backup: no notifications
    if instance.pk:
        instance._old_status = sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()


def _content_saved(sender, instance, created, **kwargs):
    if kwargs.get("raw") or instance.status != "pending":
        return
    if not created and getattr(instance, "_old_status", None) == "pending":
        return  # still pending after an edit: already notified
    office = _office_of(instance)
    if office is None or office.slug == LGU_SLUG:
        return  # the Super Admin's own posts don't need approval
    label, item_type, icon = WATCHED[sender]
    name = getattr(instance, "title", None) or getattr(instance, "name", "") or "Untitled"
    again = not created and getattr(instance, "_old_status", None) == "returned"
    try:
        link = reverse("admin_dashboard:approval_details", args=[item_type, instance.pk])
    except Exception:
        link = reverse("admin_dashboard:approval_center")
    notify_super_admins(
        f"{'Resubmitted' if again else 'New'} {label} waiting for approval",
        f'{office.name}: "{name}"',
        "warning", icon, link,
    )


for _model in WATCHED:
    pre_save.connect(_remember_old_status, sender=_model, dispatch_uid=f"admin_notif_pre_{_model.__name__}")
    post_save.connect(_content_saved, sender=_model, dispatch_uid=f"admin_notif_post_{_model.__name__}")


@receiver(post_save, sender=Message, dispatch_uid="admin_notif_message")
def _message_saved(sender, instance, created, **kwargs):
    if kwargs.get("raw") or not created or instance.sender != Message.SENDER_REP:
        return
    rep = instance.representative
    link = reverse("admin_dashboard:ad_messages") + f"?rep={rep.pk}"
    who = rep.user.get_full_name() or rep.user.username
    office = rep.office.name if rep.office else ""
    preview = instance.body if len(instance.body) <= 120 else instance.body[:117] + "..."
    # One unread notice per conversation: a chat burst updates it instead of
    # filling the bell with one notice per message.
    existing = AdminNotification.objects.filter(link_url=link, is_read=False)
    if existing.exists():
        existing.update(title=f"New messages from {who}", description=f"{office}: {preview}")
        return
    notify_super_admins(f"New message from {who}", f"{office}: {preview}",
                        "info", "fa-regular fa-envelope", link)