from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.academics.selectors import current_session
from apps.classes.models import SchoolClass
from apps.schools.lookups import get_for_school_or_404
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required

from .forms import ClassSubjectForm, SubjectForm, TeacherAssignmentForm
from .models import Subject, TeacherAssignment
from .services import (
    add_subject_to_class, assign_teacher, create_subject, remove_subject_from_class,
    set_subject_active, unassign_teacher, update_subject,
)

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)


def _text(exc):
    return " ".join(exc.messages)


@manager_only
def subject_list(request):
    subjects = Subject.objects.for_school(request.school)
    return render(request, "subjects/subject_list.html", {"subjects": subjects})


@manager_only
def subject_create(request):
    form = SubjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            subject = create_subject(request, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{subject.name} was added.")
            return redirect("subjects:list")
    return render(
        request,
        "form_page.html",
        {"form": form, "title": "Add subject", "cancel_url": reverse("subjects:list")},
    )


@manager_only
def subject_edit(request, pk):
    subject = get_for_school_or_404(Subject, request, pk=pk)
    form = SubjectForm(
        request.POST or None, initial={"name": subject.name, "code": subject.code}
    )
    if request.method == "POST" and form.is_valid():
        try:
            update_subject(request, subject, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Subject updated.")
            return redirect("subjects:list")
    return render(
        request,
        "form_page.html",
        {"form": form, "title": f"Edit {subject.name}", "cancel_url": reverse("subjects:list")},
    )


@manager_only
@require_POST
def subject_toggle(request, pk):
    subject = get_for_school_or_404(Subject, request, pk=pk)
    set_subject_active(request, subject, not subject.is_active)
    messages.success(request, "Subject updated.")
    return redirect("subjects:list")


@manager_only
@require_POST
def class_add(request, class_pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=class_pk)
    form = ClassSubjectForm(request.POST, school=request.school, school_class=school_class)
    if form.is_valid():
        try:
            add_subject_to_class(
                request, school_class, form.cleaned_data["subject"],
                is_optional=form.cleaned_data["is_optional"],
            )
            messages.success(request, "Subject added to the class.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Please choose a subject that the class does not take yet.")
    return redirect("classes:detail", pk=school_class.pk)


@manager_only
@require_POST
def class_remove(request, class_pk, subject_pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=class_pk)
    subject = get_for_school_or_404(Subject, request, pk=subject_pk)
    try:
        remove_subject_from_class(request, school_class, subject)
        messages.success(request, "Subject removed from the class.")
    except ValidationError as exc:
        messages.error(request, _text(exc))
    return redirect("classes:detail", pk=school_class.pk)


@manager_only
@require_POST
def assign(request, class_pk):
    school_class = get_for_school_or_404(SchoolClass, request, pk=class_pk)
    session = current_session(request.school)
    form = TeacherAssignmentForm(request.POST, school=request.school, school_class=school_class)
    if session is None:
        messages.error(request, "Set a current academic session before assigning teachers.")
    elif form.is_valid():
        try:
            assign_teacher(
                request, school_class=school_class, session=session, **form.cleaned_data
            )
            messages.success(request, "Teacher assigned.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Please choose a subject and a teacher.")
    return redirect("classes:detail", pk=school_class.pk)


@manager_only
@require_POST
def unassign(request, pk):
    assignment = get_for_school_or_404(TeacherAssignment, request, pk=pk)
    class_pk = assignment.school_class_id
    unassign_teacher(request, assignment)
    messages.success(request, "Teacher removed from the subject.")
    return redirect("classes:detail", pk=class_pk)
