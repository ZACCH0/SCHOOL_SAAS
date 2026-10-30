from django.contrib import admin
from .models import Membership, School

# Register your models here.
@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "school_type", "town", "state", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
    list_filter = ("school_type", "is_active")

    fieldsets = (
        ("Basic information", {"fields": ("name", "slug", "motto", "school_type")}),
        ("Contact", {"fields": ("address", "phone", "email", "website")}),
        ("Location", {"fields": ("town", "lga", "state", "country")}),
        ("Status", {"fields": ("is_active", "show_ranking")}),
    )

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "role", "is_active")
    list_filter = ("school", "role", "is_active")
    search_fields = ("user__username",)