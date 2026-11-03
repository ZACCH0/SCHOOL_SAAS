from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.classes.models import SchoolClass, Section
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain
from apps.subjects.models import Subject

from .models import TimetableSlot


@transaction.atomic
def create_slot(
    request, *, session, school_class, section=None, subject=None,
    label="", day, starts_at, ends_at,
):
    """The office places one period (or break) on a class timetable.

    The school always comes from the request; every related record must be
    from the same school or the service refuses. Overlaps clash in clean(),
    surfaced here as a friendly ValidationError.
    """
    require_role(request, MANAGE_STRUCTURE_ROLES)
    if not isinstance(school_class, SchoolClass) or school_class.school_id != request.school.pk:
        raise ValidationError("Choose a class offered by your school.")
    if section is not None:
        if not isinstance(section, Section) or section.school_id != request.school.pk:
            raise ValidationError("Choose a section of your school.")
        if section.school_class_id != school_class.pk:
            raise ValidationError("The section does not belong to this class.")
    if subject is not None:
        if not isinstance(subject, Subject) or subject.school_id != request.school.pk:
            raise ValidationError("Choose a subject offered by your school.")
    label = (label or "").strip()
    if subject is None and not label:
        raise ValidationError("A break or assembly needs a label, e.g. Long break.")
    slot = save_or_explain(
        TimetableSlot(
            school=request.school,
            session=session,
            school_class=school_class,
            section=section,
            subject=subject,
            label=label,
            day=day,
            starts_at=starts_at,
            ends_at=ends_at,
        ),
        "That period already exists or overlaps another one on this day.",
    )
    record(
        request,
        "timetable.slot_created",
        target=slot,
        slot_class=str(school_class),
        day=day,
        period=f"{starts_at:%H:%M}-{ends_at:%H:%M}",
        slot_subject=slot.title,
    )
    return slot


@transaction.atomic
def set_slot_active(request, slot, active):
    """Archive (take off) or restore a period; timetables are never deleted."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, slot)
    if slot.is_active == bool(active):
        return slot
    slot.is_active = bool(active)
    save_or_explain(
        slot, "That period clashes with another one; sort the clash first."
    )
    record(
        request,
        "timetable.slot_restored" if active else "timetable.slot_archived",
        target=slot,
    )
    return slot


@transaction.atomic
def copy_slot_to_session(request, source_slot, *, session):
    """Copy an archived or current period onto another session's timetable."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, source_slot, session)
    return create_slot(
        request,
        session=session,
        school_class=source_slot.school_class,
        section=source_slot.section,
        subject=source_slot.subject,
        label=source_slot.label,
        day=source_slot.day,
        starts_at=source_slot.starts_at,
        ends_at=source_slot.ends_at,
    )
