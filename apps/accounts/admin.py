from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User
# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Contact", {"fields": ("phone",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Contact", {"fields": ("phone",)}),)
    list_display = ("username", "first_name", "last_name", "phone", "is_active")