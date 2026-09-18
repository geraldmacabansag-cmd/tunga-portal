from .models import SiteContactInfo


def site_contact_info(request):
    return {"site_contact": SiteContactInfo.get_solo()}