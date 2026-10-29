from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST

from apps.academics.models import AcademicPeriod
from apps.academics.selectors import (
    current_or_last_period,
    current_session,
    session_periods,
)
from apps.schools.lookups import get_for_school_or_404
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required
from apps.students.models import Student
from apps.subjects.models import TeacherAssignment

from .models import ResultSheet
from .services import (
    approve_sheet,
    components_for_sheet,
    ensure_can_edit_scores,
    publish_sheet,
    review_sheet,
    save_score,
    send_back,
    submit_sheet,
    teaching_assignments_for_sheet,
)

Role = Membership.Role
SCORE_ROLES = MANAGE_STRUCTURE_ROLES + (Role.TEACHER,)

# Owners/admins see all sheets; a teacher sees only the subjects they teach.
results_access = role_required(*SCORE_ROLES)
manager_only = role_required(*MANAGE_STRUCTURE_ROLES)


def _text(exc):
    return " ".join(exc.messages)


def _teacher_sees_sheet(request, sheet):
    """A teacher sees a sheet when they teach its subject to its class this
    session: same rule as score entry, including the section vs class-wide
    distinction."""
    return teaching_assignments_for_sheet(sheet).filter(
        teacher=request.membership,
    ).exists()


@results_access
def results_home(request):
    session = current_session(request.school)
    if session is None:
        return render(request, "results/home.html", {"no_session": True})
    periods = session_periods(session)
    wanted = request.GET.get("period", "")
    period = next((p for p in periods if str(p.pk) == wanted), None)
    if period is None:
        period = current_or_last_period(session)
    if period is None:
        return render(request, "results/home.html", {"session": session, "no_period": True})

    is_manager = request.membership.role in MANAGE_STRUCTURE_ROLES
    sheets = list(
        ResultSheet.objects.for_school(request.school)
        .filter(period=period)
        .select_related("school_class", "section", "subject")
        .order_by("school_class__order", "section__name", "subject__name")
    )
    if not is_manager:
        sheets = [s for s in sheets if _teacher_sees_sheet(request, s)]
    for sheet in sheets:
        sheet.pupil_count = len(
            set(sheet.scores.values_list("student_id", flat=True))
        )
    counts = {key: 0 for key, _ in ResultSheet.Status.choices}
    for sheet in sheets:
        counts[sheet.status] += 1

    return render(
        request, "results/home.html",
        {
            "session": session,
            "period": period,
            "periods": periods,
            "sheets": sheets,
            "counts": counts,
            "is_manager": is_manager,
        },
    )


@results_access
def sheet_page(request, pk):
    sheet = get_for_school_or_404(
        ResultSheet.objects.for_school(request.school).select_related(
            "period", "period__session",
            "school_class", "school_class__level",
            "section", "subject",
        ),
        request, pk=pk,
    )
    is_manager = request.membership.role in MANAGE_STRUCTURE_ROLES
    if not is_manager:
        ensure_can_edit_scores(request, sheet)
    editable = sheet.status == ResultSheet.Status.DRAFT

    # A draft shows the live components (with their ids). Any later state shows
    # the weights captured at submission, so later configuration changes cannot
    # distort what was graded.
    components = list(components_for_sheet(sheet))
    by_name = {component.name: component for component in components}
    if sheet.weights_snapshot:
        columns = [
            {
                "pk": by_name[entry["name"]].pk if entry["name"] in by_name else None,
                "name": entry["name"],
                "max_score": entry["max_score"],
                "weight": entry["weight"],
            }
            for entry in sheet.weights_snapshot
        ]
    else:
        columns = [
            {
                "pk": component.pk,
                "name": component.name,
                "max_score": component.max_score,
                "weight": component.weight,
            }
            for component in components
        ]

    pupils_qs = Student.objects.for_school(request.school).filter(
        status=Student.Status.ACTIVE, current_class=sheet.school_class,
    )
    if sheet.section_id:
        pupils_qs = pupils_qs.filter(current_section=sheet.section)
    pupils = pupils_qs.order_by("last_name", "first_name")

    score_map = {
        (score.student_id, score.component_id): score
        for score in sheet.scores.all()
    }
    result_map = {result.student_id: result for result in sheet.results.all()}

    rows = [
        {
            "pupil": pupil,
            "entries": [
                {"column": column,
                 "score": score_map.get((pupil.pk, column["pk"]))}
                for column in columns
            ],
            "result": result_map.get(pupil.pk),
        }
        for pupil in pupils
    ]

    return render(
        request, "results/sheet.html",
        {
            "sheet": sheet,
            "columns": columns,
            "rows": rows,
            "editable": editable,
            "is_manager": is_manager,
        },
    )


@require_POST
@results_access
def sheet_score(request, pk):
    sheet = get_for_school_or_404(ResultSheet, request, pk=pk)
    if request.membership.role not in MANAGE_STRUCTURE_ROLES:
        ensure_can_edit_scores(request, sheet)

    pupil_id = request.POST.get("student", "")
    if not pupil_id.isdigit():
        messages.error(request, "Choose a pupil.")
        return redirect("results:sheet", pk=pk)
    try:
        student = Student.objects.for_school(request.school).get(pk=int(pupil_id))
    except Student.DoesNotExist:
        messages.error(request, "That pupil is not in this school.")
        return redirect("results:sheet", pk=pk)

    saved = failed = 0
    for component in components_for_sheet(sheet):
        raw = request.POST.get(f"score_{component.pk}", "").strip()
        if raw == "":
            continue
        try:
            save_score(request, sheet, student, component, raw)
            saved += 1
        except (ValidationError, PermissionDenied) as exc:
            failed += 1
            failure = _text(exc) if isinstance(exc, ValidationError) else (
                str(exc) or "That score cannot be saved."
            )
            messages.error(request, f"{student.first_name} · {component.name}: {failure}")

    if saved:
        messages.success(request, f"Saved {saved} score(s) for {student.first_name}.")
    elif failed == 0:
        messages.info(request, f"No new scores entered for {student.first_name}.")
    return redirect("results:sheet", pk=pk)


def _run_action(request, pk, service, past_tense):
    sheet = get_for_school_or_404(ResultSheet, request, pk=pk)
    try:
        service(request, sheet)
        messages.success(request, f"{sheet.subject.name} sheet {past_tense}.")
    except ValidationError as exc:
        messages.error(request, _text(exc))
    except PermissionDenied as exc:
        messages.error(request, str(exc) or "You cannot do that on this sheet.")
    return redirect("results:sheet", pk=pk)


@require_POST
@results_access
def sheet_submit(request, pk):
    return _run_action(request, pk, submit_sheet, "submitted")


@require_POST
@manager_only
def sheet_review(request, pk):
    return _run_action(request, pk, review_sheet, "marked as reviewed")


@require_POST
@manager_only
def sheet_approve(request, pk):
    return _run_action(request, pk, approve_sheet, "approved")


@require_POST
@manager_only
def sheet_publish(request, pk):
    return _run_action(request, pk, publish_sheet, "published")


@require_POST
@manager_only
def sheet_send_back(request, pk):
    return _run_action(request, pk, send_back, "sent back to draft")


@results_access
def student_report_card(request, student_pk, period_pk):
    context = _report_card_context(request, student_pk, period_pk)
    return render(request, "results/report_card.html", context)


@results_access
def student_report_card_pdf(request, student_pk, period_pk):
    """The same published results, as a printable A4 PDF report."""
    context = _report_card_context(request, student_pk, period_pk)
    html = render_to_string("results/report_card_pdf.html", context, request=request)
    from weasyprint import HTML  # imported here so a missing GTK library only affects this view

    pdf = HTML(string=html).write_pdf()
    safe_admission = "".join(
        ch if ch.isalnum() else "-" for ch in context["pupil"].admission_number
    )
    filename = "-".join(
        ("report-card", safe_admission, context["period"].name.lower().replace(" ", "-"))
    )
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = content_disposition_header(
        "attachment", f"{filename}.pdf"
    )
    return response


def _report_card_context(request, student_pk, period_pk):
    """Fetch the pupil and period with the shared access rules and assemble
    their published results. Raises Http404 outside the school and
    PermissionDenied for teachers without an assignment."""
    pupil = get_for_school_or_404(
        Student.objects.for_school(request.school).select_related(
            "current_class", "current_class__level", "current_section",
        ),
        request, pk=student_pk,
    )
    period = get_for_school_or_404(
        AcademicPeriod.objects.for_school(request.school).select_related("session"),
        request, pk=period_pk,
    )

    role = request.membership.role
    if role not in MANAGE_STRUCTURE_ROLES:
        assignments = TeacherAssignment.objects.for_school(request.school).filter(
            teacher=request.membership, session=period.session,
            school_class=pupil.current_class,
        )
        if pupil.current_section_id:
            assignments = assignments.filter(
                Q(section__isnull=True) | Q(section=pupil.current_section)
            )
        if not assignments.exists():
            raise PermissionDenied

    section_match = Q(section__isnull=True)
    if pupil.current_section_id:
        section_match |= Q(section=pupil.current_section)
    sheets = list(
        ResultSheet.objects.for_school(request.school)
        .filter(
            period=period,
            school_class=pupil.current_class,
            status=ResultSheet.Status.PUBLISHED,
        )
        .filter(section_match)
        .select_related("subject")
        .order_by("subject__name")
    )

    subject_rows = []
    percentages = []
    scale_lines = None
    columns = []  # ordered, unique component names across the pupil's sheets
    for sheet in sheets:
        result = sheet.results.filter(student=pupil).first()
        score_map = {
            score.component.name: (score.component.max_score, score.value)
            for score in
            sheet.scores.filter(student=pupil).select_related("component")
        }
        subject_rows.append({
            "sheet": sheet,
            "lines": [
                (name, max_score, value)
                for name, (max_score, value) in score_map.items()
            ],
            "score_map": score_map,
            "result": result,
        })
        for entry in sheet.weights_snapshot or []:
            if entry["name"] not in columns:
                columns.append(entry["name"])
        if result:
            percentages.append(result.percentage)
            if not scale_lines and result.scale_snapshot:
                scale_lines = result.scale_snapshot

    average = (
        (sum(percentages, Decimal("0")) / len(percentages)).quantize(Decimal("0.1"))
        if percentages else None
    )

    for row in subject_rows:
        # cells[i] matches columns[i]: a (max_score, value) pair or None
        row["cells"] = [row["score_map"].get(name) for name in columns]

    return {
        "pupil": pupil,
        "period": period,
        "subject_rows": subject_rows,
        "columns": columns,
        "average": average,
        "scale_lines": scale_lines,
        "today": timezone.localdate(),
    }
