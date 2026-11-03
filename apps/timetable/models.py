from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.academics.models import AcademicSession
from apps.classes.models import SchoolClass, Section
from apps.schools.models import ValidatedSchoolModel
from apps.subjects.models import Subject


class TimetableSlot(ValidatedSchoolModel):
    """One fixed period on a class timetable for a session.

    A slot always belongs to a class. When a section is set, the slot applies
    to that section only (sections may differ, e.g. during split subjects);
    otherwise it applies to the whole class. A slot without a subject is a
    break or assembly and must carry a label.
    """

    class WeekDay(models.IntegerChoices):
        MONDAY = 1, "Monday"
        TUESDAY = 2, "Tuesday"
        WEDNESDAY = 3, "Wednesday"
        THURSDAY = 4, "Thursday"
        FRIDAY = 5, "Friday"
        SATURDAY = 6, "Saturday"
        SUNDAY = 7, "Sunday"

    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="timetable_slots"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="timetable_slots"
    )
    section = models.ForeignKey(
        Section, null=True, blank=True, on_delete=models.PROTECT, related_name="timetable_slots"
    )
    subject = models.ForeignKey(
        Subject, null=True, blank=True, on_delete=models.PROTECT, related_name="timetable_slots"
    )
    label = models.CharField(max_length=100, blank=True)
    day = models.PositiveSmallIntegerField(choices=WeekDay.choices)
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day", "starts_at"]
        indexes = [
            models.Index(
                fields=["school", "session", "school_class", "day"], name="tt_lookup_idx"
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "session", "school_class", "day", "starts_at"],
                condition=Q(section__isnull=True) & Q(is_active=True),
                name="one_slot_per_class_day_start",
            ),
            models.UniqueConstraint(
                fields=["school", "session", "section", "day", "starts_at"],
                condition=Q(section__isnull=False) & Q(is_active=True),
                name="one_slot_per_section_day_start",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="slot_end_after_start",
            ),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("session", "school_class", "section", "subject")
        if self.section_id and self.section.school_class_id != self.school_class_id:
            raise ValidationError("The section does not belong to this class.")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("The end time must be after the start time.")
        if self.subject_id:
            if self.label:
                raise ValidationError(
                    "A lesson slot needs no extra label; the subject tells the story."
                )
        elif not self.label:
            raise ValidationError("A break or assembly needs a label, e.g. Long break.")
        self._refuse_overlap()

    def _refuse_overlap(self):
        if not (self.starts_at and self.ends_at):
            return
        others = TimetableSlot.objects.filter(
            school_id=self.school_id,
            session_id=self.session_id,
            school_class_id=self.school_class_id,
            day=self.day,
            is_active=True,
            starts_at__lt=self.ends_at,
            ends_at__gt=self.starts_at,
        ).exclude(pk=self.pk)
        if self.section_id:
            others = others.filter(Q(section__isnull=True) | Q(section_id=self.section_id))
        clash = others.first()
        if clash:
            when = f"{clash.starts_at:%H:%M}-{clash.ends_at:%H:%M}"
            subject = clash.subject or clash.label
            raise ValidationError(
                f"Something already runs for this class on {clash.get_day_display()} at {when} ({subject})."
            )

    @property
    def title(self):
        return self.subject.name if self.subject_id else self.label

    @property
    def segment(self):
        return self.section

    def __str__(self):
        return (
            f"{self.title} {self.get_day_display()} "
            f"{self.starts_at:%H:%M}-{self.ends_at:%H:%M}"
            f" ({self.section or self.school_class})"
        )
