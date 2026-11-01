from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain
from apps.students.models import Student

from .models import Applicant


def _next_applicant_number(school):
    """APP-0001 style reference, unique per school, like invoice numbers."""
    last = Applicant.objects.for_school(school).order_by("-id").first()
    if last is None:
        return "APP-0001"
    tail = last.reference.rsplit("-", 1)[-1]
    if tail.isdigit():
        return f"APP-{int(tail) + 1:04d}"
    return f"APP-{Applicant.objects.for_school(school).count() + 1:04d}"


@transaction.atomic
def create_applicant(
    request, *, first_name, last_name, sex,
    middle_name="", date_of_birth=None, target_class=None,
    guardian_name="", guardian_phone="", guardian_email="",
    address="", notes="",
):
    """The office records a family's application. Status starts APPLIED."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, *([target_class] if target_class else []))
    applicant = save_or_explain(
        Applicant(
            school=request.school,
            reference=_next_applicant_number(request.school),
            first_name=(first_name or "").strip(),
            middle_name=(middle_name or "").strip(),
            last_name=(last_name or "").strip(),
            sex=sex,
            date_of_birth=date_of_birth,
            target_class=target_class,
            guardian_name=(guardian_name or "").strip(),
            guardian_phone=(guardian_phone or "").strip(),
            guardian_email=(guardian_email or "").strip(),
            address=(address or "").strip(),
            notes=(notes or "").strip(),
        ),
        "Could not save the applicant.",
    )
    record(
        request, "admissions.applicant_created", target=applicant,
        reference=applicant.reference,
        class_name=target_class.name if target_class else None,
    )
    return applicant


def _advance(request, applicant, *, allowed_status, new_status, action, details):
    """Shared guard, save and audit block for the workflow steps."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, applicant)
    if applicant.status != allowed_status:
        raise ValidationError(
            f"An applicant who is {applicant.status} cannot move to {new_status}."
        )
    applicant.status = new_status
    save_or_explain(applicant, "Could not save the applicant.")
    record(request, action, target=applicant, **details)
    return applicant


@transaction.atomic
def review_applicant(request, applicant, *, notes=None):
    """Mark the application as reviewed (applied -> reviewed)."""
    if notes:
        applicant.notes = notes.strip()
    return _advance(
        request, applicant,
        allowed_status=Applicant.Status.APPLIED,
        new_status=Applicant.Status.REVIEWED,
        action="admissions.applicant_reviewed",
        details={"note_added": bool(notes)},
    )


@transaction.atomic
def decide_applicant(request, applicant, *, decision, notes=None):
    """Admit or decline a reviewed applicant."""
    decisions = {
        "admit": Applicant.Status.ADMITTED,
        "decline": Applicant.Status.DECLINED,
    }
    if decision not in decisions:
        raise ValidationError("The decision must be admit or decline.")
    if notes:
        applicant.notes = notes.strip()
    return _advance(
        request, applicant,
        allowed_status=Applicant.Status.REVIEWED,
        new_status=decisions[decision],
        action="admissions.applicant_decided",
        details={"decision": decision},
    )


@transaction.atomic
def convert_applicant(request, applicant, *, admission_number, section=None):
    """Turn an admitted applicant into a real Student record."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, applicant, *([section] if section else []))
    if applicant.status != Applicant.Status.ADMITTED:
        raise ValidationError("Only an admitted applicant can be converted.")
    if not applicant.target_class:
        raise ValidationError("Choose the class the applicant was admitted into first.")
    if not applicant.date_of_birth:
        raise ValidationError("Add the applicant's date of birth before converting.")
    if section and section.school_class_id != applicant.target_class_id:
        raise ValidationError("The section does not belong to the target class.")

    from apps.students.services import create_student

    student = create_student(
        request,
        first_name=applicant.first_name,
        last_name=applicant.last_name,
        middle_name=applicant.middle_name,
        sex=applicant.sex,
        date_of_birth=applicant.date_of_birth,
        admission_number=admission_number,
        address=applicant.address,
        current_class=applicant.target_class,
        current_section=section,
    )
    applicant.status = Applicant.Status.CONVERTED
    applicant.converted_student = student
    save_or_explain(applicant, "Could not finish the conversion.")
    record(
        request, "admissions.applicant_converted", target=applicant,
        reference=applicant.reference, student=student.admission_number,
    )
    return student
