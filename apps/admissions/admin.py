from django.contrib import admin

from .models import Applicant


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "school",
        "last_name",
        "first_name",
        "target_class",
        "status",
        "created_at",
    )
    list_filter = ("school", "status")
    search_fields = ("reference", "first_name", "last_name", "guardian_name", "notes")
    autocomplete_fields = ("target_class", "converted_student")
