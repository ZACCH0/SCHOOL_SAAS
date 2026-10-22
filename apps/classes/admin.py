from django.contrib import admin
from .models import ClassTeacher, Level, SchoolClass, Section


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "order", "is_active")
    list_filter = ("school", "is_active")

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "level", "order", "is_active")
    list_filter = ("school", "level", "is_active")

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("school_class", "name", "school", "is_active")
    list_filter = ("school",)

@admin.register(ClassTeacher)
class ClassTeacherAdmin(admin.ModelAdmin):
    list_display = ("school_class", "section", "session", "teacher", "school")
    list_filter = ("school", "session")