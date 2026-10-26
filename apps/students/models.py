from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.academics.models import AcademicSession
from apps.classes.models import SchoolClass, Section
from apps.schools.models import Membership, ValidatedSchoolModel


class Student(ValidatedSchoolModel):
    """A child enrolled in one school. Status tells the current state."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        GRADUATED = "graduated", "Graduated"
        WITHDRAWN = "withdrawn", "Withdrawn"
        SUSPENDED = "suspended", "Suspended"
        TRANSFERRED = "transferred", "Transferred"

    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    sex = models.CharField(
        max_length=6, choices=[("male", "Male"), ("female", "Female")]
    )
    date_of_birth = models.DateField()
    address = models.TextField(blank=True)
    admission_number = models.CharField(max_length=30)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.ACTIVE
    )
    current_class = models.ForeignKey(
        SchoolClass,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="students",
    )
    current_section = models.ForeignKey(
        Section,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="students",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                Lower("admission_number"),
                "school",
                name="unique_admission_number_per_school",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "status"]),
            models.Index(fields=["school", "last_name", "first_name"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("current_class", "current_section")
        if (
            self.current_section
            and self.current_class
            and self.current_section.school_class_id != self.current_class_id
        ):
            raise ValidationError("The section does not belong to this class.")

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.admission_number})"


class GuardianLink(ValidatedSchoolModel):
    """Documents link a parent's account to one child."""

    class Relationship(models.TextChoices):
        MOTHER = "mother", "Mother"
        FATHER = "father", "Father"
        GUARDIAN = "guardian", "Guardian"

    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="guardian_links"
    )
    guardian = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="guardian_links",
        limit_choices_to={"role__exact": Membership.Role.PARENT},
    )
    relationship = models.CharField(
        max_length=10,
        choices=Relationship.choices,
        default=Relationship.GUARDIAN,
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["student_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "guardian"],
                name="unique_guardian_per_student",
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("student", "guardian")
        if self.guardian_id and self.guardian.role != Membership.Role.PARENT:
            raise ValidationError("The guardian must have the Parent/Guardian role.")

    def __str__(self):
        return f"{self.guardian} for {self.student}"


class StudentClassHistory(ValidatedSchoolModel):
    """Which class and section this student was in during each session."""

    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="class_history"
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="student_history",
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="student_history"
    )
    section = models.ForeignKey(
        Section,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="student_history",
    )

    class Meta:
        ordering = ["session"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "session"],
                name="one_class_history_per_student_session",
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("student", "session", "school_class", "section")
        if self.section_id and self.section.school_class_id != self.school_class_id:
            raise ValidationError("The section does not belong to this class.")

    def __str__(self):
        return f"{self.student} in {self.section or self.school_class} ({self.session})"
