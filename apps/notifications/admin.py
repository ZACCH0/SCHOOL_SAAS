from django.contrib import admin

from apps.schools.lookups import SchoolScopedMixin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(SchoolScopedMixin, admin.ModelAdmin):
    list_display = ("recipient", "kind", "title", "is_read", "created_at", "school")
    list_filter = ("is_read", "school", "kind")
    search_fields = ("title", "recipient__user__username")
    ordering = ("-created_at",)

    def has_change_permission(self, request, obj=None):
        return False  # notifications are written by services, not edited by hand

    def has_delete_permission(self, request, obj=None):
        return False
