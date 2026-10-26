from django.contrib import admin

from .models import FeeItem, FeeItemPrice, Invoice, InvoiceItem, Payment


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "session", "charged", "is_active")
    list_filter = ("school", "session", "charged")


@admin.register(FeeItemPrice)
class FeeItemPriceAdmin(admin.ModelAdmin):
    list_display = ("fee_item", "school_class", "amount")
    list_filter = ("fee_item__school",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "school", "student", "status", "issue_date", "due_date")
    list_filter = ("school", "status")


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "amount")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "school", "invoice", "amount", "method", "paid_on")
    list_filter = ("school", "method")
