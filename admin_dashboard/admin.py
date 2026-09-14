from django.contrib import admin
from .models import SuperAdmin


@admin.register(SuperAdmin)
class SuperAdminAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    autocomplete_fields = ("user",)

    def has_add_permission(self, request):
        # Only allow adding a new SuperAdmin if none exists yet
        if SuperAdmin.objects.exists():
            return False
        return super().has_add_permission(request)