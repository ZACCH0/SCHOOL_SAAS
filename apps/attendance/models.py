from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.academics.models import AcademicPeriod, AcademicSession
from apps.classes.models import SchoolClass, Section
from apps.schools.models import Membership, ValidatedSchoolModel
from apps.students.models import Student


class AttendanceSession(ValidatedSchoolModel):
    """The register a teacher opens for one class (or section) on one day."""

    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="attendance_registers"
    )
    section = models.ForeignKey(
        Section,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attendance_registers",
    )
    date = models.DateField()
    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="attendance_registers"
    )
    period = models.ForeignKey(
        AcademicPeriod,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="attendance_registers",
    )
    marked_by = models.ForeignKey(
        Membership,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="opened_registers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "attendance register"
        constraints = [
            models.UniqueConstraint(
                fields=["date", "school_class", "session"],
                condition=Q(section__isnull=True),
                name="one_register_per_class_day",
            ),
            models.UniqueConstraint(
                fields=["date", "section", "session"],
                condition=Q(section__isnull=False),
                name="one_register_per_section_day",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "date"]),
            models.Index(fields=["school", "session", "school_class"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("school_class", "section", "session", "period", "marked_by")
        if self.section_id and self.section.school_class_id != self.school_class_id:
            raise ValidationError("The section does not belong to this class.")
        if self.date and self.session_id:
            if self.date < self.session.start_date or self.date > self.session.end_date:
                raise ValidationError("The register date falls outside the academic session.")
        if self.date and self.period_id:
            if self.date < self.period.start_date or self.date > self.period.end_date:
                raise ValidationError("The register date falls outside that term.")

    def __str__(self):
        for_ = self.section or self.school_class
        return f"{for_} — {self.date}"


class AttendanceRecord(ValidatedSchoolModel):
    """One pupil's line in one register."""

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    register = models.ForeignKey(
        AttendanceSession, on_delete=models.PROTECT, related_name="records"
    )
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="attendance_records"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PRESENT
    )
    remark = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["register__date", "student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["register", "student"], name="one_line_per_student_per_register"
            ),
        ]
        indexes = [models.Index(fields=["school", "status"])]

    def clean(self):
        super().clean()
        self.ensure_same_school("register", "student")

    def __str__(self):
        return f"{self.student} — {self.get_status_display()} ({self.register.date})"
