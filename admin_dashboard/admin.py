from django.contrib import admin
from django import forms
from django.shortcuts import redirect
from django.urls import reverse
from .models import SuperAdmin, EmergencyContact, EmailProviderSettings


@admin.register(SuperAdmin)
class SuperAdminAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    autocomplete_fields = ("user",)

    def has_add_permission(self, request):
        # Only allow adding a new SuperAdmin if none exists yet
        if SuperAdmin.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "phone_number", "order")
    list_filter = ("category",)


# ---------------------------------------------------------------------------
# Email Provider Settings in the Django admin, so the email (Brevo + backup)
# can be set up right after the first deploy, before logging in to the
# Super Admin dashboard. It is the SAME record as Super Admin → System
# Settings, so whatever is saved here shows there too (and the other way).
# Keys and passwords are encrypted before saving; they are never shown back.
# ---------------------------------------------------------------------------
class EmailProviderSettingsForm(forms.ModelForm):
    api_key = forms.CharField(
        label="Brevo API Key", required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "size": 60}),
        help_text="Brevo account → SMTP & API → API Keys. Leave blank to keep the saved key.")
    backup_api_key = forms.CharField(
        label="Mailjet API Key", required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "size": 60}),
        help_text="Only for the Mailjet backup (Mailjet → Account → API Keys). Leave blank to keep the saved key.")
    backup_secret = forms.CharField(
        label="Mailjet Secret Key / Gmail App Password", required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "size": 60}),
        help_text="Mailjet: the Secret Key. Gmail: the 16-letter App Password. Leave blank to keep the saved one.")

    class Meta:
        model = EmailProviderSettings
        fields = ["email_address", "backup_provider", "backup_email"]

    def clean(self):
        data = super().clean()
        try:
            from .crypto_utils import encrypt_value
            encrypt_value("test")   # needs OTP_ENCRYPTION_KEY
        except RuntimeError:
            if data.get("api_key") or data.get("backup_api_key") or data.get("backup_secret"):
                raise forms.ValidationError(
                    "Can't save keys yet: the OTP_ENCRYPTION_KEY environment variable is not set on the server.")
        if data.get("backup_provider") and not data.get("backup_email"):
            self.add_error("backup_email", "Enter the sender email of the backup.")
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        d = self.cleaned_data
        if d.get("api_key"):
            obj.set_api_key(d["api_key"].strip())
        if d.get("backup_api_key"):
            obj.set_backup_api_key(d["backup_api_key"].strip())
        if d.get("backup_secret"):
            obj.set_backup_secret(d["backup_secret"].strip())
        if not obj.backup_provider:
            obj.backup_email = ""
            obj.app_password_encrypted = ""
            obj.backup_api_key_encrypted = ""
        elif obj.backup_provider == "gmail":
            obj.backup_api_key_encrypted = ""
        obj.is_configured = bool(obj.email_address and obj.api_key_encrypted)
        if commit:
            obj.save()
        return obj


@admin.register(EmailProviderSettings)
class EmailProviderSettingsAdmin(admin.ModelAdmin):
    form = EmailProviderSettingsForm
    readonly_fields = ("brevo_status", "backup_status", "last_updated")
    fieldsets = (
        ("Main sender: Brevo (300 emails a day free)", {
            "fields": ("brevo_status", "email_address", "api_key"),
            "description": "Used for sign-up and password codes, notifications and form status emails. "
                           "The sender email must be verified in your Brevo account.",
        }),
        ("Backup sender (used automatically when Brevo can't send)", {
            "fields": ("backup_status", "backup_provider", "backup_email", "backup_api_key", "backup_secret"),
            "description": "Mailjet works on Render's free plan (200 a day free). Gmail needs hosting that allows SMTP "
                           "— Render's free plan blocks it.",
        }),
        (None, {"fields": ("last_updated",)}),
    )

    @admin.display(description="Status")
    def brevo_status(self, obj):
        return f"✔ Configured — sending from {obj.email_address}" if obj.is_configured else "✖ Not configured yet"

    @admin.display(description="Status")
    def backup_status(self, obj):
        if obj.backup_ready:
            used = f" · used {obj.backup_used_count} time(s)" if obj.backup_used_count else ""
            return f"✔ Ready — {obj.get_backup_provider_display()}, sending from {obj.backup_email}{used}"
        if obj.backup_provider:
            return "⚠ Missing a key or password — it won't be used yet"
        return "No backup"

    # Only one settings record: the list opens it directly; no add / delete.
    def changelist_view(self, request, extra_context=None):
        obj = EmailProviderSettings.get_solo()
        return redirect(reverse("admin:admin_dashboard_emailprovidersettings_change", args=[obj.pk]))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False