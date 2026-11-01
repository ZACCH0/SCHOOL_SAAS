from django import forms as dj_forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.schools.lookups import get_for_school_or_404
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required

from .forms import ApplicantForm, ConvertForm, DecideForm, ReviewForm
from .models import Applicant
from .services import convert_applicant, create_applicant, decide_applicant, review_applicant

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)

PAGE_SIZE = 25


def _text(exc):
    return " ".join(exc.messages)


@manager_only
def applicant_list(request):
    query = (request.GET.get("q") or "").strip()
    status = request.GET.get("status") or ""
    filters = Q()
    if query:
        filters &= (
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(reference__icontains=query)
            | Q(guardian_name__icontains=query)
        )
    if status in Applicant.Status.values:
        filters &= Q(status=status)
        chosen_status = status
    else:
        chosen_status = ""
    applicants = (
        Applicant.objects.for_school(request.school)
        .select_related("target_class", "converted_student")
        .filter(filters)
        .order_by("-created_at", "last_name", "first_name")
    )
    paginator = Paginator(applicants, PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page", "1"))
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(
        request, "admissions/applicant_list.html",
        {"page_obj": page_obj, "query": query, "chosen_status": chosen_status},
    )


@manager_only
def applicant_create(request):
    form = ApplicantForm(request.POST or None, school=request.school)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            applicant = create_applicant(
                request,
                first_name=data["first_name"], last_name=data["last_name"],
                middle_name=data["middle_name"], sex=data["sex"],
                date_of_birth=data["date_of_birth"],
                target_class=data["target_class"],
                guardian_name=data["guardian_name"],
                guardian_phone=data["guardian_phone"],
                guardian_email=data["guardian_email"],
                address=data["address"], notes=data["notes"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request, f"Application {applicant.reference} was recorded."
            )
            return redirect("admissions:detail", pk=applicant.pk)
    return render(
        request, "form_page.html",
        {
            "form": form,
            "title": "Add applicant",
            "cancel_url": reverse("admissions:list"),
        },
    )


@manager_only
def applicant_detail(request, pk):
    applicant = get_for_school_or_404(Applicant, request, pk=pk)
    return render(
        request, "admissions/applicant_detail.html",
        {
            "applicant": applicant,
            "review_form": ReviewForm(),
            "decide_form": DecideForm(),
            "convert_form": ConvertForm(applicant=applicant),
        },
    )


@manager_only
@require_POST
def applicant_review(request, pk):
    applicant = get_for_school_or_404(Applicant, request, pk=pk)
    form = ReviewForm(request.POST)
    if form.is_valid():
        try:
            review_applicant(request, applicant, notes=form.cleaned_data["notes"])
            messages.success(request, "Application marked as reviewed.")
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "The note could not be saved.")
    return redirect("admissions:detail", pk=applicant.pk)


@manager_only
@require_POST
def applicant_decide(request, pk):
    applicant = get_for_school_or_404(Applicant, request, pk=pk)
    form = DecideForm(request.POST)
    if form.is_valid():
        try:
            decide_applicant(
                request, applicant,
                decision=form.cleaned_data["decision"],
                notes=form.cleaned_data["notes"],
            )
            messages.success(
                request,
                "Applicant admitted." if form.cleaned_data["decision"] == "admit"
                else "Applicant declined.",
            )
        except ValidationError as exc:
            messages.error(request, _text(exc))
    else:
        messages.error(request, "Choose admit or decline.")
    return redirect("admissions:detail", pk=applicant.pk)


@manager_only
def applicant_convert(request, pk):
    applicant = get_for_school_or_404(Applicant, request, pk=pk)
    render_args = {
        "title": f"Enrol {applicant}",
        "cancel_url": reverse("admissions:detail", args=[applicant.pk]),
    }
    form = ConvertForm(request.POST or None, applicant=applicant)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            student = convert_applicant(
                request, applicant,
                admission_number=data["admission_number"].strip(),
                section=data["section"] or None,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                f"{student.first_name} {student.last_name} is now enrolled "
                f"({student.admission_number}).",
            )
            return redirect("/students/")
    return render(request, "form_page.html", {"form": form, **render_args})
