from django.urls import path

from . import views

app_name = "timetable"

urlpatterns = [
    path("", views.timetable_home, name="home"),
    path("my/", views.my_timetable, name="my"),
    path("classes/<int:pk>/", views.class_grid, name="grid"),
    path("classes/<int:class_pk>/add/", views.add_slot, name="add"),
    path("slots/<int:pk>/archive/", views.slot_archive, name="archive"),
    path("slots/<int:pk>/restore/", views.slot_restore, name="restore"),
]
