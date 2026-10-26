from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.attendance_home, name="home"),
    path("open/", views.register_open, name="open"),
    path("registers/<int:pk>/", views.register_page, name="register"),
    path("registers/<int:pk>/mark/", views.line_mark, name="mark"),
]
