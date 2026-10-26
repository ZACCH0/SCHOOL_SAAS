from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.academics.selectors import current_session
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain

from .models import GuardianLink, Student, StudentClassHistory


def _clean_str(value):
    value = (value or "").strip()
    if not value:
        raise ValidationError("A name is required.")
    return value


def _upsert_history(request, student, session=None):
    """One history row per student per session, matching the student's current class."""
    session = session or current_session(student.school)
    if session is None:
        return
    session = session or current_session(student.school)
    section = student.current_section
    if section and section.school_class_id != student.current_class_id:
        section = None
    row = StudentClassHistory.objects.filter(
        school_id=student.school_id, student=student, session=session
    ).first()
    if row:
        row.school_class = student.current_class
        row.section = section
        save_or_explain(row, "Could not update the class history.")
    else:
        StudentClassHistory.objects.create(
            school_id=student.school_id,
            student=student,
            session=session,
            school_class=student.current_class,
            section=section,
        )


@transaction.atomic
def create_student(
    request, *, first_name, last_name, sex, date_of_birth, admission_number,
    middle_name="", address="", status=Student.Status.ACTIVE,
    current_class=None, current_section=None,
):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, *(
        [current_class] if current_class else []
    ) + (
        [current_section] if current_section else []
    ))
    student = save_or_explain(
        Student(
            school=request.school,
            first_name=_clean_str(first_name),
            middle_name=(middle_name or "").strip(),
            last_name=_clean_str(last_name),
            sex=sex,
            date_of_birth=date_of_birth,
            address=(address or "").strip(),
            admission_number=admission_number,
            status=status,
            current_class=current_class,
            current_section=current_section,
        ),
        "That admission number is already in use in this school.",
    )
    if student.current_class_id:
        _upsert_history(request, student)
    record(
        request, "student.created", target=student,
        admission_number=student.admission_number,
        class_name=current_class.name if current_class else None,
    )
    return student


@transaction.atomic
def update_student(request, student, *, fields):
    """Change plain details. `fields` is a dict containing only the keys to change."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, student)
    changes = {}
    for key, new in fields.items():
        old = getattr(student, key)
        if key in {"first_name", "last_name"}:
            new = _clean_str(new)
        elif key in {"middle_name", "address"}:
            new = (new or "").strip()
        if new != old:
            changes[key] = [old, new]
            setattr(student, key, new)
    if changes:
        save_or_explain(student, "Could not save the student.")
        record(request, "student.updated", target=student, changes=changes)
    return student


@transaction.atomic
def set_student_status(request, student, status):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, student)
    if status not in Student.Status.values:
        raise ValidationError("Unknown student status.")
    if status == student.status:
        return student
    previous = student.status
    student.status = status
    save_or_explain(student, "Could not save the student.")
    record(request, "student.status_changed", target=student, previous=previous, new=status)
    return student


@transaction.atomic
def move_student(request, student, *, school_class, section=None):
    """Change the student's current class and section; history follows."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, student, school_class, *([section] if section else []))
    if section and section.school_class_id != school_class.pk:
        raise ValidationError("The section does not belong to this class.")
    if school_class.pk == student.current_class_id and section == student.current_section:
        return student
    previous = str(student.current_class or "")
    student.current_class = school_class
    student.current_section = section
    save_or_explain(student, "Could not move the student.")
    if student.current_class_id:
        _upsert_history(request, student)
    record(
        request, "student.moved", target=student,
        previous=previous, new=school_class.name,
    )
    return student


@transaction.atomic
def add_guardian(request, student, *, membership, relationship, is_primary=False):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, student, membership)
    if membership.role != membership.Role.PARENT:
        raise ValidationError("Only a member with the Parent/Guardian role can be a guardian.")
    link = save_or_explain(
        GuardianLink(
            school=request.school,
            student=student,
            guardian=membership,
            relationship=relationship,
            is_primary=is_primary,
        ),
        "That guardian is already linked to this student.",
    )
    if is_primary:
        GuardianLink.objects.for_school(request.school).filter(
            student=student, is_primary=True
        ).exclude(pk=link.pk).update(is_primary=False)
    record(
        request, "guardian.linked", target=link,
        guardian=membership.user.get_username(),
        student=student.admission_number,
    )
    return link


@transaction.atomic
def remove_guardian(request, link):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, link)
    username = link.guardian.user.get_username()
    link.delete()
    record(request, "guardian.unlinked", target=None, guardian=username, student=link.student_id)
    return username
