from .models import SiteContactInfo, SuperAdmin


def site_contact_info(request):
    return {"site_contact": SiteContactInfo.get_solo()}

def is_super_admin(request):
    if not request.user.is_authenticated:
        return {"is_super_admin": False}
    return {"is_super_admin": SuperAdmin.objects.filter(user=request.user).exists()}

def ticker_announcements(request):
    from office_dashboard.models import Announcement
    announcements = list(
        Announcement.objects.filter(status='published').order_by('-date_posted', '-created_at')[:5]
    )
    return {"ticker_announcements": announcements}