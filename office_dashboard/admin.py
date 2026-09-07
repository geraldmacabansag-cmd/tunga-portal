from django.contrib import admin
from .models import OfficeRepresentative, Announcement, NewsUpdate, Event, Photo

@admin.register(OfficeRepresentative)
class OfficeRepresentativeAdmin(admin.ModelAdmin):
    list_display = ("user", "office", "position")
    autocomplete_fields = ("user",)

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "status", "priority", "date_posted", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "content", "author")

@admin.register(NewsUpdate)
class NewsUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "status", "date_published", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "content", "author")

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "status", "event_date", "location")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "location")

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)