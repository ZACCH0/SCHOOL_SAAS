from django.contrib import admin

from .models import GuardianLink, Student, StudentClassHistory

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "first_name", "last_name", "admission_number", "school",
        "current_class", "current_section", "status",
    )
    list_filter = ("school", "status", "current_class")
    search_fields = ("first_name", "last_name", "admission_number")
    list_select_related = ("school", "current_class")

@admin.register(GuardianLink)
class GuardianLinkAdmin(admin.ModelAdmin):
    list_display = ("student", "guardian", "relationship", "is_primary", "school")
    list_filter = ("school", "relationship")

@admin.register(StudentClassHistory)
class StudentClassHistoryAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "school_class", "section", "school")
    list_filter = ("school", "session")
