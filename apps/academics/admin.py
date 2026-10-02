from django.contrib import admin
from .models import AcademicPeriod, AcademicSession

# Register your models here.
@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "start_date", "end_date", "is_current")
    list_filter = ("school", "is_current")

@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "session", "school", "order", "start_date", "end_date", "is_current")
    list_filter = ("school", "session", "is_current")