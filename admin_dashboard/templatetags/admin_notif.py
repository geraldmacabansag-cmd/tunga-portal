"""{% load admin_notif %}{% admin_notifications as notif %} — the Super Admin
bell: unread count and the latest notifications, on every dashboard page."""
from django import template

from admin_dashboard.models import AdminNotification

register = template.Library()


@register.simple_tag(takes_context=True)
def admin_notifications(context, limit=6):
    request = context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"unread": 0, "items": []}
    qs = AdminNotification.objects.filter(user=user)
    return {"unread": qs.filter(is_read=False).count(), "items": list(qs[:limit])}


@register.simple_tag
def pending_approvals():
    """Items an office has submitted that are waiting for the Super Admin to
    approve (status "pending"). "Returned" items are waiting on the office,
    so they are not counted. Used for the Approval Center badge."""
    from office_dashboard.models import (Announcement, NewsUpdate, Event, Photo,
                                         DownloadableForm, Service)
    return sum(m.objects.filter(status="pending").count()
               for m in (Announcement, NewsUpdate, Event, Photo, DownloadableForm, Service))