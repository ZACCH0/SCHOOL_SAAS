from django.contrib import admin

from .models import TimetableSlot


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ("title", "day", "starts_at", "ends_at", "section", "school_class", "is_active", "school")
    list_filter = ("school", "session", "day", "is_active")
    search_fields = ("label", "subject__name", "school_class__name")
