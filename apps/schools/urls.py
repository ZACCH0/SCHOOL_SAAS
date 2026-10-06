from django.urls import path
from . import views
app_name = "schools"

urlpatterns = [
    path("choose/", views.choose_school, name="choose"),
]