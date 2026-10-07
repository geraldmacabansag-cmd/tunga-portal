from django.contrib import admin
from django.utils.html import format_html

from .models import Place, PlaceImage


class PlaceImageInline(admin.TabularInline):
    model = PlaceImage
    extra = 1
    fields = ("preview", "image", "order")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px">', obj.image.url)
        return ""


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "barangay", "is_published", "updated_at")
    list_filter = ("category", "barangay", "is_published")
    search_fields = ("name", "description", "contact")
    list_editable = ("is_published",)
    readonly_fields = ("created_by", "created_at", "updated_at")
    inlines = [PlaceImageInline]
    fieldsets = (
        (None, {"fields": ("name", "category", "barangay", "description", "contact", "is_published")}),
        ("Location", {"fields": ("latitude", "longitude"), "description": "Easier to set by dragging the pin on the map page."}),
        ("Record", {"fields": ("created_by", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)