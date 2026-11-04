from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.academics.selectors import current_session
from apps.classes.models import SchoolClass
from apps.schools.lookups import get_for_school_or_404
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required
from apps.subjects.models import Subject, TeacherAssignment

from .forms import SlotForm
from .models import TimetableSlot
from .selectors import covering_slots
from .services import create_slot, set_slot_active

Role = Membership.Role
TIMETABLE_ROLES = MANAGE_STRUCTURE_ROLES + (Role.TEACHER,)
manager_only = role_required(*MANAGE_STRUCTURE_ROLES)
timetable_access = role_required(*TIMETABLE_ROLES)


def _joined(exc):
    return " ".join(getattr(exc, "messages", None) or [str(exc)])


def _class_of(slot):
    return slot.school_class


def _subject_choices(klass):
    """The subjects the class actually takes (ClassSubject), active only."""
    return Subject.objects.filter(
        school_id=klass.school_id, class_subjects__school_class=klass, is_active=True,
    ).order_by("name")


def _teacher_names(slot):
    """Teachers shown for a lesson slot, derived from the session's
    TeacherAssignment rows (never stored on the slot): an exact section
    assignment wins, otherwise the class-wide one."""
    assignments = TeacherAssignment.objects.filter(
        school_id=slot.school_id, session_id=slot.session_id,
        school_class_id=slot.school_class_id, subject_id=slot.subject_id,
    )
    if slot.section_id:
        exact = list(assignments.filter(section_id=slot.section_id))
    else:
        exact = []
    wider = list(assignments.filter(section__isnull=True))
    return [assignment.teacher for assignment in [*exact, *wider]]


@timetable_access
def timetable_home(request):
    session = current_session(request.school)
    if session is None:
        return render(request, "timetable/home.html", {"no_session": True})

    today_slot_q = Q(timetable_slots__session=session, timetable_slots__is_active=True)
    classes = (
        SchoolClass.objects.for_school(request.school)
        .select_related("level")
        .annotate(
            section_count=Count("sections", distinct=True),
            slot_count=Count("timetable_slots", distinct=True, filter=today_slot_q),
        )
        .order_by("level__order", "order")
    )
    if request.membership.role not in MANAGE_STRUCTURE_ROLES:
        taught = set(
            TeacherAssignment.objects.filter(
                school=request.school, session=session,
                teacher=request.membership,
            ).values_list("school_class_id", flat=True)
        )
        classes = [c for c in classes if c.pk in taught]

    is_manager = request.membership.role in MANAGE_STRUCTURE_ROLES
    return render(
        request, "timetable/home.html",
        {"session": session, "classes": list(classes), "is_manager": is_manager},
    )


def _grid_entries(request, session, klass):
    slots = list(
        TimetableSlot.objects.filter(
            school_id=request.school.pk, session_id=session.pk,
            school_class=klass, is_active=True,
        ).select_related("subject", "section")
        .order_by("day", "starts_at")
    )
    by_day = {}
    for slot in slots:
        slot.slot_teachers = _teacher_names(slot)
        by_day.setdefault(slot.day, []).append(slot)
    return [
        {
            "day": day,
            "name": TimetableSlot.WeekDay(day).label,
            "slots": by_day.get(day, []),
        }
        for day in range(1, 8)
        if by_day.get(day)
    ]


@timetable_access
def class_grid(request, pk):
    klass = get_for_school_or_404(SchoolClass, request, pk=pk)
    session = current_session(request.school)
    if session is None:
        return render(request, "timetable/grid.html", {"no_session": True})
    is_manager = request.membership.role in MANAGE_STRUCTURE_ROLES
    if not is_manager:
        if not TeacherAssignment.objects.filter(
            school=request.school, session=session,
            teacher=request.membership, school_class=klass,
        ).exists():
            raise PermissionDenied

    form = None
    if is_manager:
        form = SlotForm(subjects=_subject_choices(klass), sections=klass.sections.all())
    return render(
        request, "timetable/grid.html",
        {
            "klass": klass,
            "session": session,
            "entries": _grid_entries(request, session, klass),
            "form": form,
            "is_manager": is_manager,
        },
    )


@timetable_access
def my_timetable(request):
    """The signed-in teacher's own schedule, derived from the class slots:
    a slot belongs to them when one of their TeacherAssignments covers it —
    an exact section assignment wins, a class-wide one covers every section.
    Breaks are not lessons, so they never appear here."""
    session = current_session(request.school)
    if session is None:
        return render(request, "timetable/my.html", {"no_session": True})

    by_day = {}
    for slot in covering_slots(request.school, session, request.membership):
        by_day.setdefault(slot.day, []).append(slot)
    entries = [
        {"name": TimetableSlot.WeekDay(day).label, "slots": by_day[day]}
        for day in sorted(by_day)
    ]
    return render(request, "timetable/my.html", {"session": session, "entries": entries})


@manager_only
def add_slot(request, class_pk):
    """Place a period on a class's timetable (owner/admin only)."""
    klass = get_for_school_or_404(SchoolClass, request, pk=class_pk)
    session = current_session(request.school)
    if session is None:
        messages.error(request, "Set a current academic session first.")
        return redirect("timetable:home")

    form = SlotForm(data=request.POST or None,
                    subjects=_subject_choices(klass), sections=klass.sections.all())
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            create_slot(
                request, session=session, school_class=klass,
                section=data["section"], subject=data["subject"],
                label=data["label"], day=data["day"],
                starts_at=data["starts_at"], ends_at=data["ends_at"],
            )
        except ValidationError as exc:
            form.add_error(None, _joined(exc))
        else:
            title = data["subject"] or data["label"]
            messages.success(request, f"{title} added to {klass}'s timetable.")
            return redirect("timetable:grid", pk=klass.pk)

    return render(
        request, "form_page.html",
        {
            "form": form,
            "title": f"Add period to {klass}",
            "cancel_url": reverse("timetable:grid", args=[klass.pk]),
        },
    )


def _set_active(request, pk, active):
    slot_obj = get_for_school_or_404(TimetableSlot, request, pk=pk)
    try:
        set_slot_active(request, slot_obj, active)
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, _joined(exc))
    else:
        messages.success(
            request, f"{slot_obj.title} "
            f"{'put back on the timetable' if active else 'taken off the timetable'}."
        )
    return redirect("timetable:grid", pk=slot_obj.school_class_id)


@manager_only
@require_POST
def slot_archive(request, pk):
    return _set_active(request, pk, False)


@manager_only
@require_POST
def slot_restore(request, pk):
    return _set_active(request, pk, True)
