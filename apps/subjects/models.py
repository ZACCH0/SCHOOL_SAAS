from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from apps.academics.models import AcademicSession
from apps.classes.models import SchoolClass, Section
from apps.schools.models import Membership, ValidatedSchoolModel


class Subject(ValidatedSchoolModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "school", name="unique_subject_name_per_school"),
        ]

    def __str__(self):
        return self.name

class ClassSubject(ValidatedSchoolModel):
    """A subject that a class takes."""

    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="class_subjects"
    )
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="class_subjects")
    is_optional = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "subject"], name="unique_subject_per_class"
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("school_class", "subject")

    def __str__(self):
        return f"{self.school_class}: {self.subject}"


class TeacherAssignment(ValidatedSchoolModel):
    """This teacher teaches this subject to this class (or section) in this session."""

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    section = models.ForeignKey(
        Section, null=True, blank=True, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.PROTECT, related_name="teacher_assignments"
    )
    teacher = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="teacher_assignments"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "school_class", "subject"],
                condition=Q(section__isnull=True),
                name="one_teacher_per_class_subject_session",
            ),
            models.UniqueConstraint(
                fields=["session", "section", "subject"],
                condition=Q(section__isnull=False),
                name="one_teacher_per_section_subject_session",
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("session", "school_class", "section", "subject", "teacher")
        if self.teacher_id and self.teacher.role != Membership.Role.TEACHER:
            raise ValidationError("Only a member with the Teacher role can be assigned.")
        if self.section_id and self.section.school_class_id != self.school_class_id:
            raise ValidationError("The section does not belong to this class.")
        if (
            self.school_class_id
            and self.subject_id
            and not ClassSubject.objects.filter(
                school_class_id=self.school_class_id, subject_id=self.subject_id
            ).exists()
        ):
            raise ValidationError("This class does not take that subject.")

    def __str__(self):
        return f"{self.teacher}: {self.subject} in {self.section or self.school_class}"