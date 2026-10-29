from django.urls import path

from . import views

app_name = "results"

urlpatterns = [
    path("", views.results_home, name="home"),
    path("sheets/<int:pk>/", views.sheet_page, name="sheet"),
    path("sheets/<int:pk>/score/", views.sheet_score, name="score"),
    path("sheets/<int:pk>/submit/", views.sheet_submit, name="submit"),
    path("sheets/<int:pk>/review/", views.sheet_review, name="review"),
    path("sheets/<int:pk>/approve/", views.sheet_approve, name="approve"),
    path("sheets/<int:pk>/publish/", views.sheet_publish, name="publish"),
    path("sheets/<int:pk>/send-back/", views.sheet_send_back, name="send_back"),
    path(
        "students/<int:student_pk>/report-card/<int:period_pk>/",
        views.student_report_card, name="report_card",
    ),
]
