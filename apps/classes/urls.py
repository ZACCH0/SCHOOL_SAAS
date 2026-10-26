from django.urls import path

from . import views

app_name = "classes"

urlpatterns = [
    path("", views.class_list, name="list"),
    path("new/", views.class_create, name="create"),
    path("<int:pk>/", views.class_detail, name="detail"),
    path("<int:pk>/edit/", views.class_edit, name="edit"),
    path("<int:pk>/toggle/", views.class_toggle, name="toggle"),
    path("<int:pk>/sections/add/", views.section_add, name="section_add"),
    path("<int:pk>/class-teacher/", views.class_teacher_set, name="class_teacher"),
]
