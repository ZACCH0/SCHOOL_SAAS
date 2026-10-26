from django.urls import path

from . import views

app_name = "fees"

urlpatterns = [
    path("", views.fees_home, name="home"),
    path("structure/", views.fee_structure, name="structure"),
    path("structure/add/", views.fee_item_add, name="item_add"),
    path("structure/price/", views.fee_price_set, name="price_set"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/generate/", views.invoice_generate, name="generate"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:invoice_pk>/pay/", views.payment_record, name="pay"),
    path("payments/", views.payment_list, name="payment_list"),
    path("payments/<int:pk>/receipt/", views.receipt, name="receipt"),
]
