from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("token/", views.obtain_token, name="token"),
    path("me/", views.me, name="me"),
    path("children/", views.children, name="children"),
    path("children/<int:pk>/results/", views.child_results, name="child-results"),
    path("announcements/", views.announcements, name="announcements"),
    path("timetable/my/", views.my_timetable, name="my-timetable"),
]
