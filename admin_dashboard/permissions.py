"""Roles & Permissions for the Super Admin dashboard.

Who can open the Super Admin dashboard:
- The Super Admin: everything, always (cannot be changed).
- A STAFF MEMBER: a user the Super Admin assigned to a custom role
  (Super Admin → Roles & Permissions). They only see and use the modules
  their role allows, and only the actions ticked for it:
      View   = open the page, see the list, download/export
      Create = add something new
      Edit   = change, approve/return, publish, toggle, reorder, reply
      Delete = delete / remove

Some modules are SUPER ADMIN ONLY and can never be given to a role, so a
staff member can't raise their own access or take over the system:
Roles & Permissions, Backup & Restore, System Settings, Notifications,
My Account and Change Password (staff change their password on the public
site → Settings).

How it is enforced: every Super Admin page uses @super_admin_required
(admin_dashboard/views.py). It asks module_for(url name) + action_for(...)
here and refuses anything the role doesn't allow. The sidebar hides what
the role can't open (template tag {% admin_access as access %}).
"""

# key, label, section — the same order as the sidebar
MODULES = [
    ("dashboard", "Dashboard", "Main"),
    ("approval-center", "Approval Center", "Main"),
    ("messages", "Messages", "Main"),
    ("archive", "Archive", "Main"),
    ("announcements", "Announcements", "Content Management"),
    ("news-updates", "News & Updates", "Content Management"),
    ("events", "Events", "Content Management"),
    ("downloadable-forms", "Downloadable Forms", "Content Management"),
    ("gallery", "Gallery", "Content Management"),
    ("offices", "Offices", "Office Management"),
    ("office-reps", "Office Representatives", "Office Management"),
    ("services", "Services", "Office Management"),
    ("submissions", "Submissions", "Office Management"),
    ("org-chart", "Organizational Chart", "Office Management"),
    ("users", "Users", "User Management"),
    ("homepage", "Homepage", "Website Management"),
    ("about-page", "About Us Page", "Website Management"),
    ("interactive-map", "Interactive Map", "Website Management"),
    ("emergency-contacts", "Emergency Contacts", "Website Management"),
    ("website-settings", "Website Settings", "Website Management"),
    ("analytics", "Analytics & Reports", "Reports & Analytics"),
    ("activity-logs", "Activity Logs", "System"),
]
MODULE_KEYS = [m[0] for m in MODULES]
ACTIONS = ("view", "create", "edit", "delete")

# shown on the Roles page as "Super Admin only"
SUPER_ADMIN_ONLY = [
    ("roles", "Roles & Permissions"),
    ("backup-restore", "Backup & Restore"),
    ("system-settings", "System Settings"),
    ("notifications", "Notifications"),
    ("account", "My Account & Change Password"),
]
SUPER_ADMIN_ONLY_KEYS = {k for k, _ in SUPER_ADMIN_ONLY}

# URL name (admin_dashboard:...) -> module key
URL_MODULES = {
    "admin_dash": "dashboard",
    "approval_center": "approval-center", "approval_details": "approval-center",
    "ad_messages": "messages", "ad_messages_data": "messages", "ad_messages_send": "messages",
    "ad_archive": "archive", "admin_archive_restore": "archive", "admin_archive_delete_permanent": "archive",
    "ad_announcement": "announcements", "admin_create_announcement": "announcements",
    "admin_edit_announcement": "announcements", "admin_delete_announcement": "announcements",
    "admin_announcement_toggle_pin": "announcements",
    "ad_news_update": "news-updates", "admin_news_save": "news-updates", "admin_news_delete": "news-updates",
    "ad_events": "events", "admin_event_save": "events", "admin_event_delete": "events",
    "ad_forms": "downloadable-forms", "admin_form_save": "downloadable-forms", "admin_form_delete": "downloadable-forms",
    "admin_download_form_file": "downloadable-forms", "admin_view_form_file": "downloadable-forms",
    "admin_preview_form": "downloadable-forms", "admin_form_fields_builder": "downloadable-forms",
    "admin_save_form_fields": "downloadable-forms",
    "ad_gallery": "gallery", "ad_album_detail": "gallery", "admin_photo_archive": "gallery",
    "admin_photo_delete": "gallery", "admin_photo_save": "gallery", "admin_album_toggle_featured": "gallery",
    "ad_offices": "offices", "admin_offices_reorder": "offices", "admin_office_edit": "offices",
    "admin_office_toggle_visibility": "offices",
    "ad_office_rep": "office-reps", "admin_rep_toggle_active": "office-reps",
    "admin_assign_representative": "office-reps", "admin_rep_replace_user": "office-reps",
    "ad_services": "services", "ad_service_detail": "services", "ad_service_delete": "services",
    "admin_toggle_service_editing": "services", "office_services_pick": "services", "services": "services",
    "add_service": "services", "upload_form": "services", "edit_service": "services", "delete_service": "services",
    "save_process_steps": "services", "save_reminders": "services", "save_requirements": "services",
    "save_legal_basis": "services", "save_schedule_of_service": "services", "delete_service_form": "services",
    "download_form": "services",
    "ad_submissions": "submissions", "ad_submission_pdf": "submissions",
    "ad_org_chart": "org-chart", "ad_office_org_chart": "org-chart",
    "ad_users": "users", "admin_user_toggle_active": "users",
    "ad_homepage": "homepage", "admin_quicklink_save": "homepage", "admin_quicklink_create": "homepage",
    "admin_quicklink_delete": "homepage", "admin_quicklink_move_up": "homepage", "admin_quicklink_move_down": "homepage",
    "ad_about_page": "about-page", "admin_about_reset_defaults": "about-page",
    "admin_about_milestone_save": "about-page", "admin_about_milestone_create": "about-page",
    "admin_about_milestone_delete": "about-page", "admin_about_heritage_save": "about-page",
    "admin_about_heritage_create": "about-page", "admin_about_heritage_delete": "about-page",
    "admin_about_heritage_move": "about-page", "admin_about_official_save": "about-page",
    "admin_about_official_create": "about-page", "admin_about_official_delete": "about-page",
    "admin_about_barangay_save": "about-page", "admin_about_barangay_create": "about-page",
    "admin_about_barangay_delete": "about-page",
    "ad_map": "interactive-map", "ad_map_location": "interactive-map",
    "ad_emergency_contact": "emergency-contacts", "admin_contact_save": "emergency-contacts",
    "admin_contact_create": "emergency-contacts", "admin_contact_delete": "emergency-contacts",
    "admin_contact_reset": "emergency-contacts",
    "ad_web_setting": "website-settings",
    "ad_analytics": "analytics", "admin_export_office_activity": "analytics",
    "admin_export_approval_history": "analytics", "admin_export_satisfaction": "analytics",
    "admin_export_portal_feedback": "analytics",
    "ad_activity_log": "activity-logs",
    # Super Admin only
    "ad_roles": "roles", "ad_role_save": "roles", "ad_role_delete": "roles",
    "ad_role_member_add": "roles", "ad_role_member_remove": "roles",
    "ad_backup": "backup-restore", "ad_backup_create": "backup-restore", "ad_backup_upload": "backup-restore",
    "ad_backup_status": "backup-restore", "ad_backup_download": "backup-restore",
    "ad_backup_restore": "backup-restore", "ad_backup_delete": "backup-restore",
    "ad_system_settings": "system-settings",
    "ad_notifications": "notifications", "ad_notification_open": "notifications",
    "ad_notification_delete": "notifications", "ad_notifications_read_all": "notifications",
    "admin_account": "account", "admin_change_pass": "account",
}

# URL names whose POST makes something NEW (create) — the rest are edit/delete
CREATE_NAMES = {
    "admin_create_announcement", "add_service", "upload_form", "admin_assign_representative",
    "admin_quicklink_create", "admin_about_milestone_create", "admin_about_heritage_create",
    "admin_about_official_create", "admin_about_barangay_create", "admin_contact_create",
    "ad_messages_send",
}
# "save" pages where pk 0 means "new"
SAVE_NAMES_NEW_WHEN_ZERO = {"admin_news_save", "admin_event_save", "admin_form_save", "admin_photo_save",
                            "admin_quicklink_save", "admin_contact_save", "admin_about_milestone_save",
                            "admin_about_heritage_save", "admin_about_official_save", "admin_about_barangay_save"}


def module_for(url_name):
    return URL_MODULES.get(url_name or "")


def action_for(request, url_name, kwargs):
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return "view"
    name = url_name or ""
    if "delete" in name or "remove" in name:
        return "delete"
    if name in CREATE_NAMES:
        return "create"
    if name in SAVE_NAMES_NEW_WHEN_ZERO and str(kwargs.get("pk", "")) == "0":
        return "create"
    return "edit"


def empty_permissions():
    return {k: {a: False for a in ACTIONS} for k in MODULE_KEYS}


def clean_permissions(raw):
    """Only known modules/actions; 'view' is switched on whenever any other
    action is (you can't edit what you can't open)."""
    perms = empty_permissions()
    if isinstance(raw, dict):
        for k in MODULE_KEYS:
            row = raw.get(k) or {}
            if isinstance(row, dict):
                for a in ACTIONS:
                    perms[k][a] = bool(row.get(a))
                if any(perms[k][a] for a in ("create", "edit", "delete")):
                    perms[k]["view"] = True
    return perms


def is_super_admin(user):
    from .models import SuperAdmin
    return user.is_authenticated and SuperAdmin.objects.filter(user=user).exists()


def staff_role(user):
    """The StaffRole of a staff member, or None."""
    if not user.is_authenticated:
        return None
    from .models import StaffMember
    m = StaffMember.objects.filter(user=user).select_related("role").first()
    return m.role if m else None


def access_for(user):
    """{module: {view, create, edit, delete}} for this user (Super Admin = all)."""
    if is_super_admin(user):
        full = {k: {a: True for a in ACTIONS} for k in MODULE_KEYS}
        for k in SUPER_ADMIN_ONLY_KEYS:
            full[k] = {a: True for a in ACTIONS}
        return full
    role = staff_role(user)
    perms = clean_permissions(role.permissions if role else {})
    for k in SUPER_ADMIN_ONLY_KEYS:
        perms[k] = {a: False for a in ACTIONS}
    return perms


def can(user, module, action="view"):
    return bool(access_for(user).get(module, {}).get(action))


def first_allowed_url(user):
    """Where a staff member lands: the first module they can view."""
    from django.urls import reverse, NoReverseMatch
    access = access_for(user)
    first_page = {
        "dashboard": "admin_dash", "approval-center": "approval_center", "messages": "ad_messages",
        "archive": "ad_archive", "announcements": "ad_announcement", "news-updates": "ad_news_update",
        "events": "ad_events", "downloadable-forms": "ad_forms", "gallery": "ad_gallery",
        "offices": "ad_offices", "office-reps": "ad_office_rep", "services": "ad_services",
        "submissions": "ad_submissions", "org-chart": "ad_org_chart", "users": "ad_users",
        "homepage": "ad_homepage", "about-page": "ad_about_page", "interactive-map": "ad_map",
        "emergency-contacts": "ad_emergency_contact", "website-settings": "ad_web_setting",
        "analytics": "ad_analytics", "activity-logs": "ad_activity_log",
    }
    for k in MODULE_KEYS:
        if access[k]["view"]:
            try:
                return reverse("admin_dashboard:" + first_page[k])
            except NoReverseMatch:
                continue
    return None


def has_dashboard_access(user):
    """Super Admin, or a staff member whose role can open at least one page."""
    return is_super_admin(user) or (staff_role(user) is not None and first_allowed_url(user) is not None)