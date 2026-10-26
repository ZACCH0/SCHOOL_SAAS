from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.academics.selectors import current_session
from apps.schools.lookups import get_for_school_or_404
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required
from apps.subjects.forms import ClassSubjectForm, TeacherAssignmentForm
from apps.subjects.models import ClassSubject, TeacherAssignment

from .forms import ClassForm, ClassTeacherForm, SectionForm
from .models import ClassTeacher, SchoolClass
from .services import (
    add_section, assign_class_teacher, create_class, set_class_active, update_class,
)

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)


def _text(exc):
    return " ".join(exc.messages)


@manager_only
def class_list(request):
    classes = (
        SchoolClass.objects.for_school(request.school)
        .select_related("level")
        .prefetch_related("sections")
    )
    return render(request, "classes/class_list.html", {"classes": classes})


@manager_only
def class_create(request):
    form = ClassForm(request.POST or None, school=request.school)
    if request.method == "POST" and form.is_valid():
        try:
            school_class = create_class(request, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{school_class.name} was created.")
            return redirect("classes:detail", pk=school_class.pk)
    return render(
        request,
        "form_page.html",
        {"form": form, "title": "Add class", "cancel_url": reverse("classes:list")},
    )


@manager_only
def class_edit(request, pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=pk)
    initial = {
        "level": school_class.level_id,
        "name": school_class.name,
        "order": school_class.order,
    }
    form = ClassForm(request.POST or None, initial=initial, school=request.school)
    if request.method == "POST" and form.is_valid():
        try:
            update_class(request, school_class, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Class updated.")
            return redirect("classes:detail", pk=school_class.pk)
    return render(
        request,
        "form_page.html",
        {
            "form": form,
            "title": f"Edit {school_class.name}",
            "cancel_url": reverse("classes:detail", args=[school_class.pk]),
        },
    )


@manager_only
def class_detail(request, pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=pk)
    school = request.school
    session = current_session(school)
    assignments, class_teacher = {}, None
    if session:
        assignments = {
            a.subject_id: a
            for a in TeacherAssignment.objects.for_school(school)
            .filter(school_class=school_class, session=session, section=None)
            .select_related("teacher__user")
        }
        class_teacher = (
            ClassTeacher.objects.for_school(school)
            .filter(school_class=school_class, session=session, section=None)
            .select_related("teacher__user")
            .first()
        )
    subject_rows = [
        {"link": link, "assignment": assignments.get(link.subject_id)}
        for link in ClassSubject.objects.for_school(school)
        .filter(school_class=school_class)
        .select_related("subject")
    ]
    context = {
        "school_class": school_class,
        "session": session,
        "class_teacher": class_teacher,
        "sections": school_class.sections.all(),
        "subject_rows": subject_rows,
        "section_form": SectionForm(),
        "teacher_form": ClassTeacherForm(school=school),
        "add_subject_form": ClassSubjectForm(school=school, school_class=school_class),
        "assign_form": TeacherAssignmentForm(school=school, school_class=school_class),
    }
    return render(request, "classes/class_detail.html", context)


@manager_only
@require_POST
def class_toggle(request, pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=pk)
    set_class_active(request, school_class, not school_class.is_active)
    messages.success(request, "Class updated.")
    return redirect("classes:detail", pk=school_class.pk)


@manager_only
@require_POST
def section_add(request, pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=pk)
    form = SectionForm(request.POST)
    if form.is_valid():
        try:
            add_section(request, school_class, form.cleaned_data["name"])
            messages.success(request, "Section added.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Please enter a section name.")
    return redirect("classes:detail", pk=school_class.pk)


@manager_only
@require_POST
def class_teacher_set(request, pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=pk)
    session = current_session(request.school)
    form = ClassTeacherForm(request.POST, school=request.school)
    if session is None:
        messages.error(request, "Set a current academic session before choosing a class teacher.")
    elif form.is_valid():
        try:
            assign_class_teacher(
                request, school_class=school_class, session=session,
                teacher=form.cleaned_data["teacher"],
            )
            messages.success(request, "Class teacher saved.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Please choose a teacher.")
    return redirect("classes:detail", pk=school_class.pk)
