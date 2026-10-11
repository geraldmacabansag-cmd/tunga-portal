"""Maintenance mode (Website Settings → Maintenance).

While it's on, visitors get the "We'll be back soon" page instead of the
website. The Super Admin, office representatives and staff keep using the
whole site (they see a reminder bar), and the login pages and dashboards
always work so you can sign in and turn it off.

Added to settings.MIDDLEWARE as "admin_dashboard.maintenance.MaintenanceModeMiddleware".
"""
from django.shortcuts import render

# These always open, even during maintenance.
ALWAYS_OPEN = (
    "/super-admin/", "/office-dashboard/", "/admin/", "/static/", "/media/",
    "/login/", "/logout/", "/signup/", "/accounts/", "/forgot-password/",
    "/send-reset-otp/", "/send-signup-otp/", "/google-login-start/", "/google-signup-start/",
    "/map/api/", "/favicon.ico", "/robots.txt",
)


def is_staff_user(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    from admin_dashboard.models import SuperAdmin
    from office_dashboard.models import OfficeRepresentative
    return (SuperAdmin.objects.filter(user=user).exists()
            or OfficeRepresentative.objects.filter(user=user).exists())


def maintenance_page(request, info, preview=False, status=503):
    response = render(request, "portal/maintenance.html", {"info": info, "preview": preview}, status=status)
    if status == 503:
        response["Retry-After"] = "3600"
    return response


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not path.startswith(ALWAYS_OPEN):
            try:
                from admin_dashboard.models import SiteContactInfo
                info = SiteContactInfo.get_solo()
            except Exception:
                info = None   # e.g. before the first migrate
            if info is not None:
                user = getattr(request, "user", None)
                staff = user is not None and is_staff_user(user)
                # the Super Admin can look at the page: /?maintenance_preview=1
                if staff and request.GET.get("maintenance_preview"):
                    return maintenance_page(request, info, preview=True, status=200)
                if info.maintenance_active and not staff:
                    return maintenance_page(request, info)
        return self.get_response(request)