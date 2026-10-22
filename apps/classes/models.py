from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from apps.academics.models import AcademicSession
from apps.schools.models import Membership, ValidatedSchoolModel


class Level(ValidatedSchoolModel):
    """A stage of schooling: Primary, Junior Secondary, Senior Secondary."""

    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "school", name="unique_level_name_per_school"),
            models.UniqueConstraint(
                fields=["school", "order"], name="unique_level_order_per_school"
            ),
        ]

    def __str__(self):
        return self.name


class SchoolClass(ValidatedSchoolModel):
    """A class such as Primary 4. `order` is the promotion order across the school."""

    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="classes")
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "school classes"
        constraints = [
            models.UniqueConstraint(Lower("name"), "school", name="unique_class_name_per_school"),
            models.UniqueConstraint(
                fields=["school", "order"], name="unique_class_order_per_school"
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("level")

    def __str__(self):
        return self.name


class Section(ValidatedSchoolModel):
    """A split of one class, such as Primary 6 A and Primary 6 B."""

    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="sections"
    )
    name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["school_class__order", "name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "school_class", name="unique_section_name_per_class"
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("school_class")

    def __str__(self):
        return f"{self.school_class} {self.name}"


class ClassTeacher(ValidatedSchoolModel):
    """The class (or section) teacher for one session."""

    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="class_teachers"
    )
    section = models.ForeignKey(
        Section, null=True, blank=True, on_delete=models.PROTECT, related_name="class_teachers"
    )
    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="class_teachers"
    )
    teacher = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="class_teacher_roles"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "session"],
                condition=Q(section__isnull=True),
                name="one_class_teacher_per_class_session",
            ),
            models.UniqueConstraint(
                fields=["section", "session"],
                condition=Q(section__isnull=False),
                name="one_class_teacher_per_section_session",
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("school_class", "section", "session", "teacher")
        if self.teacher_id and self.teacher.role != Membership.Role.TEACHER:
            raise ValidationError("The class teacher must have the Teacher role.")
        if self.section_id and self.section.school_class_id != self.school_class_id:
            raise ValidationError("The section does not belong to this class.")

    def __str__(self):
        return f"{self.teacher} - {self.section or self.school_class} ({self.session})"