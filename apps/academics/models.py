from django.db import models
from django.db.models import F, Q
from django.core.exceptions import ValidationError
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
    
class AcademicPeriod(SchoolOwnedModel):
    """A term or semester inside a session. Names are chosen by the school."""

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="periods"
    )
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "name"], name="unique_period_name_per_session"
            ),
            models.UniqueConstraint(
                fields=["session", "order"], name="unique_period_order_per_session"
            ),
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(is_current=True),
                name="one_current_period_per_school",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="period_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.session_id and self.school_id and self.session.school_id != self.school_id:
            raise ValidationError("A period must belong to the same school as its session.")
        if self.session_id and self.start_date and self.end_date:
            if (
                self.start_date < self.session.start_date
                or self.end_date > self.session.end_date
            ):
                raise ValidationError("Period dates must fall inside the session dates.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.session.name}"    