from django.contrib import admin

from .models import AttendanceRecord, AttendanceSession

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ("school", "date", "school_class", "section", "session", "marked_by")
    list_filter = ("school", "school_class", "session")
    date_hierarchy = "date"

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "register", "status", "school")
    list_filter = ("school", "status")
    search_fields = ("student__first_name", "student__last_name", "student__admission_number")
