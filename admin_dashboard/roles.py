"""The three built-in roles of the Tunga Portal and what each can do.
Shown (read only) on Super Admin → Roles & Permissions. Roles are fixed:
they are enforced in the code, not chosen on a page —
  Super Admin            -> @super_admin_required   (admin_dashboard/views.py)
  Office Representative  -> @office_rep_required    (office_dashboard/views.py),
                            always limited to their own office
  Citizen                -> @login_required on the public site's account,
                            form and feedback pages (portal, offices)
"""

Y, N = True, False


def _row(area, view, create, edit, delete, note=""):
    return {"area": area, "view": view, "create": create, "edit": edit, "delete": delete, "note": note}


def built_in_roles():
    from django.contrib.auth.models import User
    from office_dashboard.models import OfficeRepresentative
    from .models import SuperAdmin

    sa_count = SuperAdmin.objects.count()
    rep_count = OfficeRepresentative.objects.exclude(office__slug="lgu-super-admin").count()
    citizen_count = (User.objects.filter(super_admin__isnull=True, office_rep__isnull=True,
                                         is_staff=False, is_superuser=False).count())

    return [
        {
            "key": "super-admin", "name": "Super Admin", "icon": "fa-solid fa-crown", "color": "amber",
            "count": sa_count, "where": "Super Admin dashboard",
            "summary": "The LGU's main administrator. Manages the whole website and approves what the "
                       "offices post. There is only one Super Admin account.",
            "rules": [
                "Only one Super Admin account can exist; it is assigned in the Django admin.",
                "What the Super Admin posts is published right away (no approval needed).",
                "Approves or returns everything the offices submit.",
                "Every action is recorded in Activity Logs.",
            ],
            "rows": [
                _row("Approval Center", Y, N, Y, N, "Approve or return office submissions"),
                _row("Announcements, News, Events", Y, Y, Y, Y, "For any office or the LGU"),
                _row("Downloadable Forms, Gallery", Y, Y, Y, Y),
                _row("Offices", Y, N, Y, N, "Edit details, reorder, show or hide"),
                _row("Office Representatives", Y, Y, Y, N, "Assign, replace, activate or deactivate"),
                _row("Services (Citizen's Charter)", Y, Y, Y, Y, "For any office; allow or lock editing"),
                _row("Online Submissions", Y, N, N, N, "All offices, view only"),
                _row("Users (citizen accounts)", Y, N, Y, N, "Activate or deactivate"),
                _row("Homepage, About Us, Emergency Contacts, Map", Y, Y, Y, Y),
                _row("Website Settings, Legal Pages", Y, N, Y, N),
                _row("Analytics & Reports", Y, N, N, N, "Includes client satisfaction; export CSV"),
                _row("Messages", Y, Y, N, N, "Chat with office representatives"),
                _row("Archive", Y, N, Y, Y, "Restore or delete permanently"),
                _row("Backup & Restore", Y, Y, Y, Y, "Back up, download, restore"),
                _row("System Settings (email)", Y, N, Y, N),
                _row("Activity Logs", Y, N, N, N),
            ],
        },
        {
            "key": "office-rep", "name": "Office Representative", "icon": "fa-solid fa-building-user", "color": "blue",
            "count": rep_count, "where": "Office Dashboard",
            "summary": "One staff member per office, assigned by the Super Admin. Manages only their own "
                       "office's page and requests.",
            "rules": [
                "Can only see and change their own office's records.",
                "Announcements, news, events and photos go to the Super Admin for approval first.",
                "Published content can't be edited; services stay locked unless the Super Admin allows editing.",
                "Every action is recorded in their Activity Logs.",
            ],
            "rows": [
                _row("Dashboard", Y, N, N, N, "Summary of the office"),
                _row("Announcements, News, Events", Y, Y, Y, Y, "Sent for approval; edit only before publishing"),
                _row("Gallery (photos and albums)", Y, Y, Y, Y, "Photos sent for approval"),
                _row("Services (Citizen's Charter)", Y, Y, Y, Y, "Add / edit only while the Super Admin allows service editing; delete only before publishing"),
                _row("Downloadable Forms", Y, Y, Y, Y, "Upload PDFs, make them fillable online"),
                _row("Submissions", Y, N, Y, N, "Open filled forms, update the status, write a note"),
                _row("Office Profile, Page Settings, Org Chart", Y, N, Y, N),
                _row("Messages", Y, Y, N, N, "Chat with the Super Admin"),
                _row("Notifications", Y, N, Y, Y),
                _row("Activity Logs", Y, N, N, N, "Own office only"),
                _row("My Account, Change Password", Y, N, Y, N),
            ],
        },
        {
            "key": "citizen", "name": "Citizen", "icon": "fa-solid fa-user", "color": "green",
            "count": citizen_count, "where": "Public website",
            "summary": "Any resident or visitor who signs up with a verified email or Google. Visitors who "
                       "are not logged in can still read the public pages.",
            "rules": [
                "Must log in to download forms or fill them out online.",
                "Can only see their own submissions and data.",
                "Can delete their own account and data (Data Privacy Act).",
            ],
            "rows": [
                _row("Public pages", Y, N, N, N, "Announcements, offices, services, gallery, about, contact"),
                _row("Downloadable Forms", Y, N, N, N, "View, download (login required)"),
                _row("Online Form Submissions", Y, Y, N, N, "Fill out online; follow the status"),
                _row("Service rating & website feedback", Y, Y, Y, N, "Rate finished requests; rate the website"),
                _row("Notifications", Y, N, N, Y, "Updates and request status"),
                _row("My Account, Password", Y, Y, Y, Y, "Sign up, edit profile, delete account"),
            ],
        },
    ]