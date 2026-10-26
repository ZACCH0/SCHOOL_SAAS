from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("school/", include("apps.schools.urls")),
    path("classes/", include("apps.classes.urls")),
    path("subjects/", include("apps.subjects.urls")),
    path("", include("apps.core.urls")),
]
