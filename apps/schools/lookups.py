from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
def get_for_school_or_404(source, request, **lookup):
    """Fetch one record that belongs to the active school, or raise 404.

    `source` is a model class or a queryset of a school-owned model.
    """
    school = getattr(request, "school", None)
    if school is None:
        raise Http404
    queryset = source.objects.all() if hasattr(source, "objects") else source
    return get_object_or_404(queryset.for_school(school), **lookup)


class SchoolScopedMixin:
    """For class-based views: only the active school's records are visible."""

    def get_queryset(self):
        school = getattr(self.request, "school", None)
        if school is None:
            raise PermissionDenied
        return super().get_queryset().for_school(school)