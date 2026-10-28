from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.db import transaction

from apps.audit.services import record
from apps.results.models import (
    AssessmentComponent,
    GradeBoundary,
    GradeScale,
    ResultSheet,
    Score,
    SubjectResult,
)
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain
from apps.subjects.models import TeacherAssignment

SCORE_ROLES = MANAGE_STRUCTURE_ROLES + (Membership.Role.TEACHER,)


def _text(exc):
    return " ".join(exc.messages)


def _decimal(value, message):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValidationError(message) from exc


def ensure_can_edit_scores(request, sheet):
    """Owner/admin may score any sheet. A teacher only the subject they are
    assigned to this session for the sheet's class (or exact section)."""
    membership = getattr(request, "membership", None)
    if membership is None:
        raise PermissionDenied
    if membership.role in MANAGE_STRUCTURE_ROLES:
        return
    if membership.role != Membership.Role.TEACHER:
        raise PermissionDenied
    scope = (
        Q(section__isnull=True) | Q(section=sheet.section)
        if sheet.section_id
        else Q(section__isnull=True)
    )
    assigned = TeacherAssignment.objects.for_school(request.school).filter(
        teacher=membership,
        session=sheet.period.session,
        school_class=sheet.school_class,
        subject=sheet.subject,
    ).filter(scope).exists()
    if not assigned:
        raise PermissionDenied(
            "Only the subject teacher of this class or section can enter scores for it."
        )


def _ensure_editable(sheet):
    if sheet.status != ResultSheet.Status.DRAFT:
        raise ValidationError(
            "Only a draft sheet can be edited. Send the sheet back first."
        )


def _component_scope(sheet):
    """School-wide components plus any scoped to the sheet's class level."""
    return Q(level__isnull=True) | Q(level=sheet.school_class.level_id)


def _applicable_components(sheet):
    return AssessmentComponent.objects.for_school(sheet.school).filter(
        _component_scope(sheet),
        session=sheet.period.session,
    )


def _ensure_component_applies(sheet, component):
    if component.session_id != sheet.period.session_id:
        raise ValidationError("The component belongs to another session.")
    if component.level_id and component.level_id != sheet.school_class.level_id:
        raise ValidationError("The component does not apply to this class's level.")


def _active_scale(session):
    scale = GradeScale.objects.for_school(session.school).filter(
        session=session, is_active=True
    ).first()
    if scale is None:
        raise ValidationError("There is no active grade scale for this session.")
    return scale


def _scale_snapshot(scale):
    return [
        {
            "grade": b.grade,
            "min_percent": str(b.min_percent),
            "remark": b.remark,
            "points": b.points,
        }
        for b in scale.boundaries.all()
    ]


def _grade_for(scale, percentage):
    boundary = (
        scale.boundaries.filter(min_percent__lte=percentage)
        .order_by("-min_percent")
        .first()
    )
    return (boundary.grade, boundary.remark) if boundary else ("", "")


def _recompute_student(sheet, student, scale):
    scores = list(
        sheet.scores.filter(student=student).select_related("component")
    )
    if not scores:
        return None
    total = Decimal("0")
    weighted = Decimal("0")
    weight_sum = Decimal("0")
    for score in scores:
        component = score.component
        total += score.value
        weighted += score.value / component.max_score * component.weight
        weight_sum += component.weight
    percentage = (weighted / weight_sum * 100).quantize(Decimal("0.1"))
    grade, remark = _grade_for(scale, percentage)
    result, _created = SubjectResult.objects.update_or_create(
        sheet=sheet,
        student=student,
        defaults={
            "school": sheet.school,
            "total": total.quantize(Decimal("0.01")),
            "percentage": percentage,
            "grade": grade,
            "grade_remark": remark,
            "scale_snapshot": _scale_snapshot(scale),
        },
    )
    return result


@transaction.atomic
def save_score(request, sheet, student, component, value):
    """Enter or change one pupil's score on a draft sheet and refresh that
    pupil's computed result."""
    require_role(request, SCORE_ROLES)
    ensure_owned(request, sheet, student, component)
    _ensure_editable(sheet)
    ensure_can_edit_scores(request, sheet)
    _ensure_component_applies(sheet, component)
    value = _decimal(value, "Enter a valid score.")

    previous = Score.objects.for_school(request.school).filter(
        sheet=sheet, student=student, component=component
    ).first()
    previous_value = str(previous.value) if previous else None
    score = previous or Score(
        school=request.school, sheet=sheet, student=student, component=component,
    )
    score.value = value
    try:
        score.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    save_or_explain(score, "This pupil already has a score for that component.")

    scale = _active_scale(sheet.period.session)
    _recompute_student(sheet, student, scale)

    record(
        request, "results.score_saved", target=score,
        student=student.admission_number, component=component.name,
        previous=previous_value,
        value=str(value),
    )
    return score


@transaction.atomic
def submit_sheet(request, sheet):
    """Teacher hands the sheet in: snapshot the weights, grade every pupil,
    and move the sheet to submitted."""
    require_role(request, SCORE_ROLES)
    ensure_owned(request, sheet)
    _ensure_editable(sheet)
    ensure_can_edit_scores(request, sheet)

    components = list(_applicable_components(sheet))
    if not components:
        raise ValidationError("This session has no assessment components set up.")
    if not sheet.scores.exists():
        raise ValidationError("Enter at least one score before submitting.")

    scored = {s.student_id for s in sheet.scores.all()}
    incomplete = len(scored) * len(components) - sheet.scores.count()
    if incomplete:
        raise ValidationError(
            f"{incomplete} component score(s) are still missing. "
            "Every pupil needs a score for every component before submitting."
        )

    scale = _active_scale(sheet.period.session)
    for student in sheet.scores.values_list("student", flat=True).distinct():
        _recompute_student(sheet, student, scale)

    sheet.weights_snapshot = [
        {
            "name": c.name,
            "max_score": str(c.max_score),
            "weight": str(c.weight),
            "level": c.level.name if c.level_id else None,
        }
        for c in components
    ]
    sheet.status = ResultSheet.Status.SUBMITTED
    sheet.submitted_by = request.membership
    try:
        sheet.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    sheet.save()

    record(
        request, "results.sheet_submitted", target=sheet,
        subject=sheet.subject.name,
        for_class=sheet.section.name if sheet.section_id else sheet.school_class.name,
        students=len(scored),
    )
    return sheet


def _advance(request, sheet, from_status, to_status, actor_field, action):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, sheet)
    if sheet.status != from_status:
        raise ValidationError(
            f"Only a {from_status} sheet can move to {to_status}."
        )
    setattr(sheet, actor_field, request.membership)
    sheet.status = to_status
    try:
        sheet.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    sheet.save()
    record(
        request, action, target=sheet,
        subject=sheet.subject.name,
        for_class=sheet.section.name if sheet.section_id else sheet.school_class.name,
    )
    return sheet


@transaction.atomic
def review_sheet(request, sheet):
    return _advance(
        request, sheet, ResultSheet.Status.SUBMITTED,
        ResultSheet.Status.REVIEWED, "reviewed_by", "results.sheet_reviewed",
    )


@transaction.atomic
def approve_sheet(request, sheet):
    return _advance(
        request, sheet, ResultSheet.Status.REVIEWED,
        ResultSheet.Status.APPROVED, "approved_by", "results.sheet_approved",
    )


@transaction.atomic
def publish_sheet(request, sheet):
    return _advance(
        request, sheet, ResultSheet.Status.APPROVED,
        ResultSheet.Status.PUBLISHED, "published_by", "results.sheet_published",
    )


@transaction.atomic
def send_back(request, sheet):
    """Return a submitted or reviewed sheet to draft so scores can change.
    Once approved, results are final and can no longer be sent back."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, sheet)
    if sheet.status not in (
        ResultSheet.Status.SUBMITTED, ResultSheet.Status.REVIEWED,
    ):
        raise ValidationError(
            "Only a submitted or reviewed sheet can be sent back."
        )
    previous = sheet.status
    sheet.status = ResultSheet.Status.DRAFT
    sheet.submitted_by = None
    sheet.weights_snapshot = None
    try:
        sheet.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    sheet.save()
    record(
        request, "results.sheet_sent_back", target=sheet,
        subject=sheet.subject.name, previous=previous,
        for_class=sheet.section.name if sheet.section_id else sheet.school_class.name,
    )
    return sheet
