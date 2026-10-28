from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.academics.models import AcademicPeriod, AcademicSession
from apps.classes.models import Level, SchoolClass, Section
from apps.schools.models import Membership, ValidatedSchoolModel
from apps.students.models import Student
from apps.subjects.models import Subject


class GradeScale(ValidatedSchoolModel):
    """A school's grading table for one session, e.g. A1 to F9 or A to F."""

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="grade_scales"
    )
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "session", name="unique_scale_name_per_session"
            ),
        ]
        indexes = [
            models.Index(fields=["school", "session"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("session")

    def __str__(self):
        return self.name


class GradeBoundary(ValidatedSchoolModel):
    """One row of a grade scale: any score from min_percent up earns this grade."""

    scale = models.ForeignKey(
        GradeScale, on_delete=models.PROTECT, related_name="boundaries"
    )
    grade = models.CharField(max_length=10)
    min_percent = models.DecimalField(max_digits=5, decimal_places=1)
    remark = models.CharField(max_length=100, blank=True)
    points = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Optional grading points, e.g. WASSCE-style point 1 to 9.",
    )

    class Meta:
        ordering = ["-min_percent"]
        constraints = [
            models.UniqueConstraint(
                Lower("grade"), "scale", name="unique_grade_label_per_scale"
            ),
            models.UniqueConstraint(
                fields=["scale", "min_percent"], name="unique_boundary_start_per_scale"
            ),
            models.CheckConstraint(
                condition=Q(min_percent__gte=0, min_percent__lte=100),
                name="boundary_percent_0_to_100",
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("scale")

    def __str__(self):
        return f"{self.grade} from {self.min_percent}%"


class AssessmentComponent(ValidatedSchoolModel):
    """One scored part of a subject's total, e.g. First CA 20, Exam 60. Most school-wide; level set limits it to one level."""

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="assessment_components"
    )
    level = models.ForeignKey(
        Level,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assessment_components",
        help_text="Leave empty to apply to every level; set it to apply to that level only.",
    )
    name = models.CharField(max_length=100)
    max_score = models.DecimalField(max_digits=7, decimal_places=2)
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Share of the subject's 100%, e.g. 40 for CA and 60 for Exam.",
    )

    class Meta:
        ordering = ["session", "level__order", "name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "session", "level", name="unique_component_name_per_scope"
            ),
            models.CheckConstraint(
                condition=Q(max_score__gt=0), name="component_max_score_positive"
            ),
            models.CheckConstraint(
                condition=Q(weight__gt=0), name="component_weight_positive"
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("session")
        if self.level_id:
            self.ensure_same_school("level")
        if self.session_id and self.name and not self.level_id:
            clash = (
                AssessmentComponent.objects.filter(
                    school_id=self.school_id, session_id=self.session_id
                )
                .annotate(name_lower=Lower("name"))
                .filter(name_lower=self.name.lower())
                .exclude(pk=self.pk)
                .exists()
            )
            if clash:
                raise ValidationError(
                    "A school-wide assessment component already has that name this session."
                )

    def __str__(self):
        return f"{self.name} ({self.max_score})"


class ResultSheet(ValidatedSchoolModel):
    """One subject's score sheet for one class (or section) in one term. Its status is the workflow."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"

    period = models.ForeignKey(
        AcademicPeriod, on_delete=models.PROTECT, related_name="result_sheets"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="result_sheets"
    )
    section = models.ForeignKey(
        Section,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="result_sheets",
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="result_sheets"
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    weights_snapshot = models.JSONField(
        null=True, blank=True, help_text="Components and weights captured when the sheet was submitted."
    )
    submitted_by = models.ForeignKey(
        Membership, null=True, blank=True, on_delete=models.PROTECT, related_name="submitted_sheets"
    )
    reviewed_by = models.ForeignKey(
        Membership, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_sheets"
    )
    approved_by = models.ForeignKey(
        Membership, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_sheets"
    )
    published_by = models.ForeignKey(
        Membership, null=True, blank=True, on_delete=models.PROTECT, related_name="published_sheets"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["period", "school_class__order", "subject__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["period", "school_class", "subject"],
                condition=Q(section__isnull=True),
                name="one_sheet_per_class_subject_period",
            ),
            models.UniqueConstraint(
                fields=["period", "section", "subject"],
                condition=Q(section__isnull=False),
                name="one_sheet_per_section_subject_period",
            ),
            models.CheckConstraint(
                condition=Q(submitted_by__isnull=True) | ~Q(status__in=["draft"]),
                name="submitted_needs_submitter",
            ),
        ]
        indexes = [
            models.Index(fields=["school", "period", "status"]),
            models.Index(fields=["school", "period", "school_class"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school(
            "period",
            "school_class",
            "section",
            "subject",
            "submitted_by",
            "reviewed_by",
            "approved_by",
            "published_by",
        )
        if self.section_id and self.section.school_class_id != self.school_class_id:
            raise ValidationError("The section does not belong to this class.")

    def __str__(self):
        for_ = self.section or self.school_class
        return f"{self.subject.name} — {for_} ({self.period.name})"


class Score(ValidatedSchoolModel):
    """One pupil's raw score on one component of one subject sheet."""

    sheet = models.ForeignKey(
        ResultSheet, on_delete=models.PROTECT, related_name="scores"
    )
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="scores"
    )
    component = models.ForeignKey(
        AssessmentComponent, on_delete=models.PROTECT, related_name="scores"
    )
    value = models.DecimalField(max_digits=7, decimal_places=2)

    class Meta:
        ordering = ["sheet", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["sheet", "student", "component"],
                name="one_score_per_student_component_sheet",
            ),
            models.CheckConstraint(condition=Q(value__gte=0), name="score_value_not_negative"),
        ]
        indexes = [
            models.Index(fields=["school", "student"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("sheet", "student", "component")
        if (
            self.sheet_id
            and self.component_id
            and self.component.session_id != self.sheet.period.session_id
        ):
            raise ValidationError("The component belongs to another session.")
        if self.sheet_id and self.student_id:
            if self.student.current_class_id != self.sheet.school_class_id:
                raise ValidationError("That pupil is not currently in this class.")
            if self.sheet.section_id and self.student.current_section_id != self.sheet.section_id:
                raise ValidationError("That pupil is not in this section.")

    def __str__(self):
        return f"{self.student} — {self.component.name}: {self.value}"


class SubjectResult(ValidatedSchoolModel):
    """One pupil's computed outcome for one subject sheet, kept with a snapshot of the grading used."""

    sheet = models.ForeignKey(
        ResultSheet, on_delete=models.PROTECT, related_name="results"
    )
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="subject_results"
    )
    total = models.DecimalField(max_digits=7, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=1)
    grade = models.CharField(max_length=10, blank=True)
    grade_remark = models.CharField(max_length=100, blank=True)
    scale_snapshot = models.JSONField(
        null=True, blank=True, help_text="Grade boundaries captured when the result was computed."
    )

    class Meta:
        ordering = ["sheet", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["sheet", "student"], name="one_result_per_student_per_sheet"
            ),
            models.CheckConstraint(
                condition=Q(percentage__gte=0), name="result_percentage_not_negative"
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("sheet", "student")

    def __str__(self):
        return f"{self.student} — {self.sheet.subject.name}: {self.percentage}% ({self.grade or '-'})"
