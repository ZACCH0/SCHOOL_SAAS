from django.contrib import admin

from .models import (
    AssessmentComponent,
    GradeBoundary,
    GradeScale,
    ResultSheet,
    Score,
    SubjectResult,
)


@admin.register(GradeScale)
class GradeScaleAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "session", "is_active")
    list_filter = ("school", "session", "is_active")


@admin.register(GradeBoundary)
class GradeBoundaryAdmin(admin.ModelAdmin):
    list_display = ("scale", "grade", "min_percent", "remark", "points")
    list_filter = ("scale__school", "scale")
    ordering = ("scale", "-min_percent")


@admin.register(AssessmentComponent)
class AssessmentComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "max_score", "weight", "level", "session", "school")
    list_filter = ("school", "session", "level")


@admin.register(ResultSheet)
class ResultSheetAdmin(admin.ModelAdmin):
    list_display = (
        "subject", "school_class", "section", "period", "status", "school",
    )
    list_filter = ("school", "period", "status")
    search_fields = ("subject__name", "school_class__name")


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "component", "value", "sheet", "school")
    list_filter = ("school",)
    search_fields = ("student__first_name", "student__last_name", "student__admission_number")


@admin.register(SubjectResult)
class SubjectResultAdmin(admin.ModelAdmin):
    list_display = ("student", "sheet", "percentage", "grade", "total", "school")
    list_filter = ("school",)
    search_fields = ("student__first_name", "student__last_name", "student__admission_number")
