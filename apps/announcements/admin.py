from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "audience", "is_active", "published_by", "created_at")
    list_filter = ("school", "audience", "is_active")
    search_fields = ("title", "body")
