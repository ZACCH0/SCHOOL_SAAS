"""Read-only helpers for timetables."""

from .models import TimetableSlot
from apps.subjects.selectors import assignments_for, assignment_covers


def covering_slots(school, session, membership, day=None):
    """The active lesson slots of one session this teacher membership covers,
    derived from their TeacherAssignments (never stored on the slot).

    A slot belongs to the teacher when one of their assignments matches the
    slot's class and subject and section (exact section assignment covers
    only that section, class-wide covers every section). Breaks have no
    subject, so they are never a lesson and never appear here. Read-only;
    when ``day`` is given only that weekday's slots come back.
    """
    assignments = assignments_for(school, membership, session)
    slots = (
        TimetableSlot.objects.filter(
            school=school, session=session, is_active=True,
            subject__isnull=False,
        )
        .select_related("subject", "section", "school_class")
        .order_by("day", "starts_at")
    )
    if day is not None:
        slots = slots.filter(day=day)
    return [
        slot for slot in slots
        if assignment_covers(
            assignments,
            school_class_id=slot.school_class_id,
            subject_id=slot.subject_id,
            section_id=slot.section_id,
        )
    ]
