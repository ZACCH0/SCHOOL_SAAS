from django.db import models
from django.db.models import F, Q

from apps.schools.models import SchoolOwnedModel

# Create your models here.
class AcademicSession(SchoolOwnedModel):
    """One school year, e.g. 2026/2027. Names are chosen by the school."""

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"], name="unique_session_name_per_school"
            ),
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(is_current=True),
                name="one_current_session_per_school",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="session_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.school})"