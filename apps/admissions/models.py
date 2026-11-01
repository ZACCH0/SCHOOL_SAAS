from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.classes.models import SchoolClass
from apps.schools.models import ValidatedSchoolModel
from apps.students.models import Student


class Applicant(ValidatedSchoolModel):
    """A child whose family applied for admission into the school.

    The office records applications, reviews them, admits or declines, and
    finally converts an admitted applicant into a real Student record.
    The invitation of a public online form is postponed to T21.
    """

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        REVIEWED = "reviewed", "Reviewed"
        ADMITTED = "admitted", "Admitted"
        DECLINED = "declined", "Declined"
        CONVERTED = "converted", "Converted"

    reference = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(
        max_length=6, choices=[("male", "Male"), ("female", "Female")]
    )
    date_of_birth = models.DateField(null=True, blank=True)
    target_class = models.ForeignKey(
        SchoolClass,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="applicants",
    )
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_phone = models.CharField(max_length=20, blank=True)
    guardian_email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.APPLIED
    )
    converted_student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="admission_applicant",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                Lower("reference"),
                "school",
                name="unique_applicant_reference_per_school",
            ),
            models.CheckConstraint(
                condition=Q(converted_student__isnull=False) | ~Q(status="converted"),
                name="converted_applicant_has_student",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "status"]),
            models.Index(fields=["school", "last_name", "first_name"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("target_class", "converted_student")

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.reference})"
