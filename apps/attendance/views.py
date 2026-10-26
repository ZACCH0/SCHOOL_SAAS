from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render, reverse
from django.views.decorators.http import require_POST

from apps.academics.selectors import current_session
from apps.classes.models import ClassTeacher, SchoolClass, Section
from apps.schools.lookups import get_for_school_or_404
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required
from apps.schools.models import Membership

from .forms import OPEN_STATUSES, OpenRegisterForm
from .models import AttendanceSession
from .services import mark_student, open_register

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)
mark_allowed = role_required(
    MANAGE_STRUCTURE_ROLES[0], MANAGE_STRUCTURE_ROLES[1], Membership.Role.TEACHER
)


def _text(exc):
    return " ".join(exc.messages)


def _my_classes(request, session):
    """Registers a teacher may mark: the classes/sections they are the form
    teacher of this session. Subject teachers mark scores instead."""
    return list(
        ClassTeacher.objects.for_school(request.school)
        .filter(teacher=request.membership, session=session)
        .select_related("school_class", "section")
        .order_by("school_class__order", "section__name")
    )


@mark_allowed
def attendance_home(request):
    session = current_session(request.school)
    if session is None:
        return render(request, "attendance/home.html", {"session": None, "no_session": True})

    day = request.GET.get("day", "")
    try:
        chosen_day = date.fromisoformat(day)
    except ValueError:
        chosen_day = date.today()

    choices = []
    if request.membership.role in MANAGE_STRUCTURE_ROLES:
        for school_class in SchoolClass.objects.for_school(request.school).filter(is_active=True):
            for section in school_class.sections.filter(is_active=True) or [None]:
                choices.append({"school_class": school_class, "section": section})
    else:
        choices = [
            {"school_class": link.school_class, "section": link.section}
            for link in _my_classes(request, session)
        ]
    for choice in choices:
        exists = (
            AttendanceSession.objects.for_school(request.school)
            .filter(
                school_class=choice["school_class"], date=chosen_day,
                section=choice["section"],
            )
            .first()
        )
        choice["register"] = exists
    return render(
        request, "attendance/home.html",
        {
            "session": session, "chosen_day": chosen_day, "choices": choices,
            "is_manager": request.membership.role in MANAGE_STRUCTURE_ROLES,
            "today": date.today(),
        },
    )


@require_POST
@mark_allowed
def register_open(request):
    form_class = request.POST.get("school_class", "")
    section_id = request.POST.get("section", "")
    day = request.POST.get("day", "")
    if not form_class.isdigit():
        messages.error(request, "Choose a class.")
        return redirect("attendance:home")
    try:
        chosen_day = date.fromisoformat(day)
    except ValueError:
        messages.error(request, "Choose a valid day.")
        return redirect("attendance:home")
    school_class = get_for_school_or_404(SchoolClass, request, pk=int(form_class))
    section = None
    if section_id.isdigit():
            section = get_for_school_or_404(Section, request, pk=int(section_id))
    try:
        register, opened = open_register(
            request, school_class=school_class, section=section, day=chosen_day
        )
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _text(exc) if isinstance(exc, ValidationError) else str(exc))
        return redirect("attendance:home")
    messages.success(request, "Register opened." if opened else "Register is already open.")
    return redirect("attendance:register", pk=register.pk)


@mark_allowed
def register_page(request, pk):
    register = get_for_school_or_404(
        AttendanceSession.objects.for_school(request.school)
        .select_related("school_class", "section", "session", "period", "marked_by__user"),
        request, pk=pk,
    )
    editable = register.session_id and register.session == current_session(request.school)
    records = (
        register.records.select_related("student", "student__current_class", "student__current_section")
    )
    summary = {key: 0 for key, _ in OPEN_STATUSES}
    for line in records:
        summary[line.status] = summary.get(line.status, 0) + 1
    return render(
        request, "attendance/register.html",
        {
            "register": register,
            "records": records.order_by("student__last_name", "student__first_name"),
            "editable": editable,
            "statuses": OPEN_STATUSES,
            "summary": summary,
        },
    )


@require_POST
@mark_allowed
def line_mark(request, pk):
    register = get_for_school_or_404(AttendanceSession, request, pk=pk)
    pupil_id = request.POST.get("student", "")
    status = request.POST.get("status", "")
    remark = request.POST.get("remark", "")
    if not pupil_id.isdigit():
        messages.error(request, "Choose a pupil.")
        return redirect("attendance:register", pk=register.pk)
    from apps.students.models import Student
    try:
        student = Student.objects.for_school(request.school).get(pk=int(pupil_id))
    except Student.DoesNotExist:
        messages.error(request, "That pupil is not in this school.")
        return redirect("attendance:register", pk=register.pk)
    try:
        line = mark_student(request, register, student, status, remark)
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _text(exc) if isinstance(exc, ValidationError) else str(exc))
        return redirect("attendance:register", pk=register.pk)
    messages.success(request, f"{line.student.first_name}: {line.get_status_display()}.")
    return redirect("attendance:register", pk=register.pk)
