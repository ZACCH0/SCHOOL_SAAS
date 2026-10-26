from django.urls import path

from . import views

app_name = "subjects"

urlpatterns = [
    path("", views.subject_list, name="list"),
    path("new/", views.subject_create, name="create"),
    path("<int:pk>/edit/", views.subject_edit, name="edit"),
    path("<int:pk>/toggle/", views.subject_toggle, name="toggle"),
    path("classes/<int:class_pk>/add/", views.class_add, name="class_add"),
    path("classes/<int:class_pk>/remove/<int:subject_pk>/", views.class_remove, name="class_remove"),
    path("classes/<int:class_pk>/assign/", views.assign, name="assign_teacher"),
    path("assignments/<int:pk>/remove/", views.unassign, name="unassign_teacher"),
]
