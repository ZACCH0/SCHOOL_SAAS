from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="list"),
    path("new/", views.student_create, name="create"),
    path("<int:pk>/", views.student_detail, name="detail"),
    path("<int:pk>/edit/", views.student_edit, name="edit"),
    path("<int:pk>/status/", views.status_set, name="status"),
    path("<int:pk>/move/", views.move, name="move"),
    path("<int:pk>/guardians/add/", views.guardian_add, name="guardian_add"),
    path("<int:pk>/guardians/<int:link_pk>/remove/", views.guardian_remove, name="guardian_remove"),
    path("parents/", views.parent_list, name="parent_list"),
    path("parents/new/", views.parent_create, name="parent_create"),
]
