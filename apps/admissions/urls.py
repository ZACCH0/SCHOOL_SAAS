from django.urls import path

from . import views

app_name = "admissions"

urlpatterns = [
    path("", views.applicant_list, name="list"),
    path("new/", views.applicant_create, name="create"),
    path("<int:pk>/", views.applicant_detail, name="detail"),
    path("<int:pk>/review/", views.applicant_review, name="review"),
    path("<int:pk>/decide/", views.applicant_decide, name="decide"),
    path("<int:pk>/enrol/", views.applicant_convert, name="convert"),
]
