from django import forms as dj_forms
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.classes.models import SchoolClass, Section
from apps.academics.models import AcademicSession
from apps.schools.lookups import get_for_school_or_404
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required

from .forms import GuardianForm, StudentDetailForm, StudentForm
from .models import GuardianLink, Student
from .services import (
    add_guardian, create_student, move_student, remove_guardian,
    set_student_status, update_student,
)

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)

PAGE_SIZE = 25


def _text(exc):
    return " ".join(exc.messages)


def _classes(school):
    return SchoolClass.objects.for_school(school).filter(is_active=True)


def _sections(school):
    return Section.objects.for_school(school).filter(is_active=True)


class MoveForm(dj_forms.Form):
    school_class = dj_forms.ModelChoiceField(
        required=False, empty_label="No class", label="Class",
        queryset=SchoolClass.objects.none(),
    )
    section = dj_forms.ModelChoiceField(
        required=False, empty_label="No section", label="Section",
        queryset=Section.objects.none(),
    )

    def __init__(self, *args, school, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["school_class"].queryset = _classes(school)
        self.fields["section"].queryset = _sections(school)

    def clean(self):
        cleaned = super().clean()
        section = cleaned.get("section")
        if section and cleaned.get("school_class") != section.school_class:
            raise ValidationError("The section does not belong to the chosen class.")
        return cleaned


class StatusForm(dj_forms.Form):
    status = dj_forms.ChoiceField(choices=Student.Status.choices)


@manager_only
def student_list(request):
    query = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    selected_class = request.GET.get("class") or ""
    filters = Q()
    if query:
        filters &= (
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(admission_number__icontains=query)
        )
    if status in Student.Status.values:
        filters &= Q(status=status)
        chosen_status = status
    else:
        chosen_status = ""
    chosen_class = ""
    if selected_class.isdigit():
        chosen_class = int(selected_class)
        filters &= Q(current_class_id=chosen_class)
    students = (
        Student.objects.for_school(request.school)
        .select_related("current_class", "current_section")
        .filter(filters)
        .order_by("last_name", "first_name")
    )
    paginator = Paginator(students, PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page", "1"))
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(
        request, "students/student_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "chosen_status": chosen_status,
            "chosen_class": chosen_class,
            "classes": _classes(request.school),
        },
    )


@manager_only
def student_create(request):
    form = StudentForm(request.POST or None, school=request.school)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            student = create_student(
                request, first_name=data["first_name"], last_name=data["last_name"],
                sex=data["sex"], date_of_birth=data["date_of_birth"],
                admission_number=data["admission_number"],
                middle_name=data["middle_name"], address=data["address"],
                current_class=data["current_class"],
                current_section=data["current_section"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{student.first_name} {student.last_name} was enrolled.")
            return redirect("students:detail", pk=student.pk)
    return render(
        request, "form_page.html",
        {"form": form, "title": "Add student", "cancel_url": reverse("students:list")},
    )


@manager_only
def student_edit(request, pk):
    student = get_for_school_or_404(Student, request, pk=pk)
    initial = {
        "first_name": student.first_name, "middle_name": student.middle_name,
        "last_name": student.last_name, "sex": student.sex,
        "date_of_birth": student.date_of_birth, "address": student.address,
        "current_class": student.current_class_id,
        "current_section": student.current_section_id,
    }
    form = StudentDetailForm(request.POST or None, initial=initial, school=request.school)
    if request.method == "POST" and form.is_valid():
        try:
            update_student(request, student, fields=form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Student updated.")
            return redirect("students:detail", pk=student.pk)
    return render(
        request, "form_page.html",
        {
            "form": form,
            "title": f"Edit {student}",
            "cancel_url": reverse("students:detail", args=[student.pk]),
        },
    )


@manager_only
def student_detail(request, pk):
    student = get_for_school_or_404(
        Student, request, pk=pk,
    )
    context = {
        "student": student,
        "links": (
            GuardianLink.objects.for_school(request.school)
            .filter(student=student)
            .select_related("guardian__user")
        ),
        "guardian_form": GuardianForm(school=request.school, student=student),
        "status_form": StatusForm(initial={"status": student.status}),
        "move_form": MoveForm(
            school=request.school, initial={
                "school_class": student.current_class_id,
                "section": student.current_section_id,
            }
        ),
        "history": (
            student.class_history.select_related("session", "school_class", "section")
        ),
        "sessions": AcademicSession.objects.for_school(request.school),
    }
    return render(request, "students/student_detail.html", context)


@manager_only
@require_POST
def status_set(request, pk):
    student = get_for_school_or_404(Student, request, pk=pk)
    form = StatusForm(request.POST)
    if form.is_valid():
        try:
            set_student_status(request, student, form.cleaned_data["status"])
            messages.success(request, "Status updated.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Choose a status from the list.")
    return redirect("students:detail", pk=student.pk)


@manager_only
@require_POST
def move(request, pk):
    student = get_for_school_or_404(
        Student, request, pk=pk,
    )
    form = MoveForm(request.POST, school=request.school)
    if form.is_valid():
        data = form.cleaned_data
        try:
            move_student(
                request, student, school_class=data["school_class"],
                section=data["section"] or None,
            )
            messages.success(request, "Class updated.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Choose a valid class and section.")
    return redirect("students:detail", pk=student.pk)


@manager_only
@require_POST
def guardian_add(request, pk):
    student = get_for_school_or_404(Student, request, pk=pk)
    form = GuardianForm(request.POST, school=request.school, student=student)
    if form.is_valid():
        data = form.cleaned_data
        try:
            add_guardian(
                request, student, membership=data["guardian"],
                relationship=data["relationship"], is_primary=data["is_primary"],
            )
            messages.success(request, "Guardian linked.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Choose a parent or guardian from the list.")
    return redirect("students:detail", pk=student.pk)


@manager_only
@require_POST
def guardian_remove(request, pk, link_pk):
    student = get_for_school_or_404(Student, request, pk=pk)
    try:
        link = GuardianLink.objects.for_school(request.school).get(pk=link_pk, student=student)
    except GuardianLink.DoesNotExist:
        messages.error(request, "That guardian link no longer exists.")
        return redirect("students:detail", pk=student.pk)
    remove_guardian(request, link)
    messages.success(request, "Guardian unlinked.")
    return redirect("students:detail", pk=student.pk)
