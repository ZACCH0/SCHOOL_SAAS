from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.children, name="children"),
    path("children/<int:pk>/", views.child_page, name="child"),
]
