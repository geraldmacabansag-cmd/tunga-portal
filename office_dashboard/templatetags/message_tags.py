from django import template

from office_dashboard.models import Message, OfficeRepresentative
from admin_dashboard.models import SuperAdmin

register = template.Library()


@register.simple_tag
def unread_messages(request):
    """Number of chat messages waiting for the logged-in user: for the Super
    Admin, unread messages from any representative; for a representative,
    unread messages from the Super Admin. Used for the sidebar badge."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return 0
    if SuperAdmin.objects.filter(user=user).exists():
        return Message.objects.filter(sender=Message.SENDER_REP, read_at__isnull=True).count()
    rep = OfficeRepresentative.objects.filter(user=user).first()
    if rep is None:
        return 0
    return rep.chat_messages.filter(sender=Message.SENDER_ADMIN, read_at__isnull=True).count()