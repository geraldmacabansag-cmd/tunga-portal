from django.contrib import admin
from .models import OfficeRepresentative, Announcement, NewsUpdate, Event, DownloadableForm, Photo, Album, Service, ProcessStep, Notification, ActivityLog

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

@admin.register(DownloadableForm)
class DownloadableFormAdmin(admin.ModelAdmin):
    list_display = ("title", "office", "category", "status", "download_count", "date_uploaded")
    list_filter = ("status", "category", "office")
    search_fields = ("title", "description", "uploaded_by")

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("name", "representative", "created_at")
    search_fields = ("name",)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "office", "category", "published_at")
    list_filter = ("category",)
    search_fields = ("name",)

@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ("title", "service", "order", "created_at")
    list_filter = ("service",)
    search_fields = ("title",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "level", "is_read", "created_at")
    list_filter = ("level", "is_read")
    search_fields = ("title", "description")

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("title", "representative", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("title", "description")