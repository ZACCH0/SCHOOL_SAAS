from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain

from .models import ClassSubject, Subject, TeacherAssignment


def _name(value):
    value = (value or "").strip()
    if not value:
        raise ValidationError("A name is required.")
    return value


@transaction.atomic
def create_subject(request, *, name, code=""):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    subject = save_or_explain(
        Subject(school=request.school, name=_name(name), code=(code or "").strip()),
        "A subject with that name already exists.",
    )
    record(request, "subject.created", target=subject)
    return subject


@transaction.atomic
def update_subject(request, subject, *, name=None, code=None):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, subject)
    changes = {}
    if name is not None and _name(name) != subject.name:
        changes["name"] = [subject.name, _name(name)]
        subject.name = _name(name)
    if code is not None and code.strip() != subject.code:
        changes["code"] = [subject.code, code.strip()]
        subject.code = code.strip()
    if changes:
        save_or_explain(subject, "A subject with that name already exists.")
        record(request, "subject.updated", target=subject, changes=changes)
    return subject


@transaction.atomic
def set_subject_active(request, subject, active):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, subject)
    if subject.is_active != active:
        subject.is_active = active
        save_or_explain(subject, "Could not save the subject.")
        record(request, "subject.activated" if active else "subject.deactivated", target=subject)
    return subject


@transaction.atomic
def add_subject_to_class(request, school_class, subject, *, is_optional=False):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class, subject)
    link = save_or_explain(
        ClassSubject(
            school=request.school, school_class=school_class,
            subject=subject, is_optional=is_optional,
        ),
        "This class already takes that subject.",
    )
    record(request, "class_subject.added", target=link)
    return link


@transaction.atomic
def remove_subject_from_class(request, school_class, subject):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class, subject)
    link = ClassSubject.objects.for_school(request.school).filter(
        school_class=school_class, subject=subject
    ).first()
    if link is None:
        raise ValidationError("This class does not take that subject.")
    if TeacherAssignment.objects.for_school(request.school).filter(
        school_class=school_class, subject=subject
    ).exists():
        raise ValidationError("Remove the teacher assignments for this subject first.")
    record(request, "class_subject.removed", target=link)
    link.delete()


@transaction.atomic
def assign_teacher(request, *, school_class, subject, teacher, session, section=None):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class, subject, teacher, session, *([section] if section else []))
    existing = (
        TeacherAssignment.objects.for_school(request.school)
        .filter(session=session, school_class=school_class, section=section, subject=subject)
        .first()
    )
    if existing:
        if existing.teacher_id == teacher.pk:
            return existing
        previous = existing.teacher.user.get_username()
        existing.teacher = teacher
        save_or_explain(existing, "Could not change the teacher.")
        record(
            request, "teacher.reassigned", target=existing,
            previous=previous, new=teacher.user.get_username(),
        )
        return existing
    assignment = save_or_explain(
        TeacherAssignment(
            school=request.school, school_class=school_class, section=section,
            subject=subject, teacher=teacher, session=session,
        ),
        "That subject already has a teacher for this class and session.",
    )
    record(request, "teacher.assigned", target=assignment, teacher=teacher.user.get_username())
    return assignment


@transaction.atomic
def unassign_teacher(request, assignment):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, assignment)
    record(request, "teacher.unassigned", target=assignment)
    assignment.delete()
