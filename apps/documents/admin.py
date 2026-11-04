from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "audience", "uploaded_by", "is_active")
    list_display_links = ("title",)
    list_filter = ("school", "audience", "is_active")
    search_fields = ("title", "category", "description")
