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

def nav_offices(request):
    # Powers the "Offices" dropdown in the public site's navbar (base.html)
    # on every page, so it has to live in a context processor rather than
    # being passed in from each view individually. "Active" here matches
    # the same rule used for the "From Our Offices" tab on the Announcements
    # page: visible to the public AND currently has a representative whose
    # account is active — a visible office with no one assigned yet, or
    # whose rep account is disabled, doesn't show up here either.
    from django.urls import reverse
    from offices.models import Office

    offices_list = list(
        Office.objects
        .exclude(slug="lgu-super-admin")
        .filter(is_visible=True, representative__isnull=False, representative__user__is_active=True)
        .order_by("name")
    )
    for o in offices_list:
        o.nav_url = (
            reverse('offices:mayor') if o.slug == 'office-of-the-mayor'
            else reverse('offices:office_detail', args=[o.slug])
        )
    return {"nav_offices": offices_list}