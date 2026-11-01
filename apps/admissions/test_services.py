from datetime import date

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.classes.models import SchoolClass, Level
from apps.students.models import Student

from .models import Applicant
from .services import (
    convert_applicant,
    create_applicant,
    decide_applicant,
    review_applicant,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def class_a(school_a):
    level = Level.objects.create(school=school_a, name="Primary", order=1)
    return SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 1", order=1
    )


@pytest.fixture
def current_session(school_a):
    from apps.academics.models import AcademicSession

    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", start_date=date(2026, 9, 1),
        end_date=date(2027, 7, 31), is_current=True,
    )


def make_applicant(school, **kwargs):
    fields = {
        "school": school,
        "reference": "APP-0001",
        "first_name": "Bola",
        "last_name": "Ade",
        "sex": "male",
    }
    fields.update(kwargs)
    return Applicant.objects.create(**fields)


def test_create_marks_audited_starts_applied(make_request, school_a, class_a):
    request = make_request(school_a)
    applicant = create_applicant(
        request,
        first_name="Bola", last_name="Ade", sex="male",
        middle_name="Tunde", date_of_birth=date(2018, 5, 10),
        target_class=class_a, guardian_name="Mama Bola",
        guardian_phone="0803 000 0000", guardian_email="bola@example.com",
        address="12 Isale Taba", notes="Saw poster",
    )
    assert applicant.status == Applicant.Status.APPLIED
    assert applicant.reference == "APP-0001"

    second = create_applicant(
        request, first_name="Chike", last_name="Oke", sex="male"
    )
    assert second.reference == "APP-0002"

    entry = AuditLog.objects.filter(
        action="admissions.applicant_created", metadata__reference="APP-0001",
    ).latest("id")
    assert entry.metadata["class_name"] == "Primary 1"


def test_reference_number_skips_non_numeric_tail(make_request, school_a):
    make_applicant(school_a, reference="APP-special")
    request = make_request(school_a)
    applicant = create_applicant(
        request, first_name="Bola", last_name="Ade", sex="male"
    )
    assert applicant.reference == f"APP-{Applicant.objects.count():04d}"


def test_teacher_bursar_cannot_create(make_request, school_a, class_a):
    for role in ("teacher", "bursar"):
        request = make_request(school_a, role=role)
        with pytest.raises(PermissionDenied):
            create_applicant(
                request, first_name="Bola", last_name="Ade", sex="male"
            )


def test_applicant_of_another_school_is_refused(make_request, school_a, school_b):
    foreign = make_applicant(school_b)
    request = make_request(school_a)
    with pytest.raises(PermissionDenied):
        review_applicant(request, foreign)


def test_full_pipeline_reviewed_decided_converted(
    make_request, school_a, class_a, current_session
):
    request = make_request(school_a)
    applicant = make_applicant(school_a, target_class=class_a)
    review_applicant(request, applicant)
    assert applicant.status == Applicant.Status.REVIEWED

    decide_applicant(request, applicant, decision="admit")
    assert applicant.status == Applicant.Status.ADMITTED
    entry = AuditLog.objects.filter(action="admissions.applicant_decided").latest("id")
    assert entry.metadata["decision"] == "admit"

    applicant.date_of_birth = date(2018, 5, 10)
    applicant.save(update_fields=["date_of_birth"])
    student = convert_applicant(
        request, applicant, admission_number="FSS/2026/201"
    )
    assert isinstance(student, Student)
    assert student.current_class == class_a
    assert student.class_history.exists()
    assert Student.objects.filter(admission_number="FSS/2026/201").exists()

    applicant.refresh_from_db()
    assert applicant.status == Applicant.Status.CONVERTED
    assert applicant.converted_student == student
    assert AuditLog.objects.filter(
        action="admissions.applicant_converted"
    ).exists()


def test_workflow_order_is_enforced(make_request, school_a):
    request = make_request(school_a)
    applicant = make_applicant(school_a)

    with pytest.raises(ValidationError):
        decide_applicant(request, applicant, decision="admit")
    with pytest.raises(ValidationError):
        convert_applicant(
            request, applicant, admission_number="FSS/2026/202"
        )


def test_declined_applicant_never_converts(make_request, school_a):
    request = make_request(school_a)
    applicant = make_applicant(school_a)
    review_applicant(request, applicant)
    decide_applicant(request, applicant, decision="decline")

    with pytest.raises(ValidationError):
        convert_applicant(request, applicant, admission_number="FSS/2026/203")


def test_conversion_requires_class_and_birth_date(make_request, school_a, class_a):
    request = make_request(school_a)
    applicant = make_applicant(school_a, target_class=class_a, date_of_birth=None)
    review_applicant(request, applicant)
    decide_applicant(request, applicant, decision="admit")

    with pytest.raises(ValidationError, match="date of birth"):
        convert_applicant(request, applicant, admission_number="FSS/2026/204")

    applicant.target_class = None
    applicant.date_of_birth = date(2018, 5, 10)
    applicant.save()
    with pytest.raises(ValidationError, match="class"):
        convert_applicant(
            request, applicant, admission_number="FSS/2026/204"
        )


def test_duplicate_admission_number_changes_nothing(make_request, school_a, class_a):
    Student.objects.create(
        school=school_a, first_name="Ada", last_name="Obi", sex="female",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/888",
    )
    request = make_request(school_a)
    applicant = make_applicant(
        school_a, target_class=class_a, date_of_birth=date(2018, 5, 10)
    )
    review_applicant(request, applicant)
    decide_applicant(request, applicant, decision="admit")

    with pytest.raises(ValidationError, match="admission number"):
        convert_applicant(request, applicant, admission_number="FSS/2026/888")
    applicant.refresh_from_db()
    assert applicant.status == Applicant.Status.ADMITTED
    assert applicant.converted_student is None


def test_review_and_decide_accept_notes(make_request, school_a):
    request = make_request(school_a)
    applicant = make_applicant(school_a, notes="")
    review_applicant(request, applicant, notes="Interview book: 12 Nov")
    applicant.refresh_from_db()
    assert applicant.notes == "Interview book: 12 Nov"

    decide_applicant(request, applicant, decision="decline", notes="No placement")
    applicant.refresh_from_db()
    assert applicant.notes == "No placement"
