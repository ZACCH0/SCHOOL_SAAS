from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("school/", include("apps.schools.urls")),
    path("classes/", include("apps.classes.urls")),
    path("subjects/", include("apps.subjects.urls")),
    path("students/", include("apps.students.urls")),
    path("attendance/", include("apps.attendance.urls")),
    path("fees/", include("apps.fees.urls")),
    path("results/", include("apps.results.urls")),
    path("", include("apps.core.urls")),
]
