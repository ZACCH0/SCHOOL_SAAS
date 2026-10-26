from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q

from apps.academics.models import AcademicPeriod
from apps.audit.services import record
from apps.academics.selectors import current_session
from apps.classes.models import ClassTeacher
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain
from apps.students.models import Student
from apps.subjects.models import TeacherAssignment

from .models import AttendanceRecord, AttendanceSession

CanMarkRoles = MANAGE_STRUCTURE_ROLES + (Membership.Role.TEACHER,)


def ensure_can_mark(request, school_class, session, section=None):
    """Owner/admin may open any class. A teacher may only use their own class."""
    membership = getattr(request, "membership", None)
    if membership is None:
        raise PermissionDenied
    if membership.role in MANAGE_STRUCTURE_ROLES:
        return
    if membership.role != Membership.Role.TEACHER:
        raise PermissionDenied
    is_form_teacher = (
        ClassTeacher.objects.for_school(request.school)
        .filter(teacher=membership, session=session, school_class=school_class)
        .filter(_section_overlap(section))
        .exists()
    )
    is_subject_teacher = (
        TeacherAssignment.objects.for_school(request.school)
        .filter(teacher=membership, session=session, school_class=school_class)
        .filter(_section_overlap(section))
        .exists()
    )
    if not (is_form_teacher or is_subject_teacher):
        raise PermissionDenied(
            "You are not a teacher of that class or section."
        )


def _section_overlap(section):
    """A class-level assignment covers a section too; a section assignment is exact."""
    if section is None:
        return Q()
    return Q(section__isnull=True) | Q(section=section)


def _pupils(school, school_class, section):
    pupils = Student.objects.for_school(school).filter(
        current_class=school_class, status=Student.Status.ACTIVE
    )
    if section:
        pupils = pupils.filter(current_section=section)
    return pupils


@transaction.atomic
def open_register(request, *, school_class, section, day):
    """The register for (class, section, day). Opened once and reused afterwards."""
    require_role(request, CanMarkRoles)
    ensure_owned(request, school_class, *([section] if section else []))
    session = current_session(request.school)
    if session is None:
        raise ValidationError("There is no current academic session. Set one first.")
    ensure_can_mark(request, school_class, session, section)
    if section and section.school_class_id != school_class.pk:
        raise ValidationError("The section does not belong to this class.")
    existing = (
        AttendanceSession.objects.for_school(request.school)
        .filter(school_class=school_class, session=session, date=day)
        .filter(section=section)
        .first()
    )
    if existing:
        return existing, False
    register = save_or_explain(
        AttendanceSession(
            school=request.school, school_class=school_class, section=section,
            date=day, session=session, period=_current_period(request.school),
            marked_by=request.membership,
        ),
        "This class or section already has a register for that day.",
    )
    lines = 0
    for student in _pupils(request.school, school_class, section):
        AttendanceRecord.objects.create(
            school=request.school, register=register, student=student,
            status=AttendanceRecord.Status.PRESENT,
        )
        lines += 1
    record(
        request, "attendance.register_opened", target=register,
        for_class=school_class.name,
        section=section.name if section else None,
        date=str(day), lines=lines,
    )
    return register, True


def _current_period(school):
    return AcademicPeriod.objects.for_school(school).filter(is_current=True).first()


@transaction.atomic
def mark_student(request, register, student, status, remark=""):
    """Set or change one pupil's line on a register."""
    require_role(request, CanMarkRoles)
    ensure_owned(request, register, student)
    if register.session_id and register.session != current_session(request.school):
        raise PermissionDenied(
            "That register belongs to another academic session. Open one for the current session."
        )
    ensure_can_mark(request, register.school_class, register.session, register.section)
    if status not in AttendanceRecord.Status.values:
        raise ValidationError("Choose a status from the list.")
    line = AttendanceRecord.objects.for_school(request.school).filter(
        register=register, student=student
    ).first()
    if line:
        if line.status == status and line.remark == (remark or ""):
            return line
        previous = line.status
        line.status = status
        line.remark = remark or ""
        save_or_explain(line, "Could not save the attendance line.")
        record(
            request, "attendance.marked", target=line,
            student=student.admission_number,
            previous=previous, new=status,
        )
        return line
    if student.current_class_id != register.school_class_id:
        raise ValidationError("That pupil is not currently in this class.")
    if register.section and student.current_section_id != register.section_id:
        raise ValidationError("That pupil is not in this section.")
    line = save_or_explain(
        AttendanceRecord(
            school=request.school, register=register, student=student,
            status=status, remark=remark or "",
        ),
        "This pupil already has a line on this register.",
    )
    record(
        request, "attendance.marked", target=line,
        student=student.admission_number, new=status,
    )
    return line
