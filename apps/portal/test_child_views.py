from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from apps.classes.models import Level, SchoolClass, Section
from apps.fees.models import Invoice, InvoiceItem, Payment
from apps.schools.models import Membership
from apps.students.models import GuardianLink, Student
from apps.subjects.models import ClassSubject, Subject, TeacherAssignment

from apps.results.models import (
    AssessmentComponent,
    GradeBoundary,
    GradeScale,
    ResultSheet,
)
from apps.results.services import (
    approve_sheet, publish_sheet, review_sheet, save_score, submit_sheet,
)

Role = Membership.Role
pytestmark = pytest.mark.django_db


# --- shared setup helpers (mirroring the results tests' fixtures) ---


def make_structure(school):
    level = Level.objects.create(school=school, name="Primary", order=1)
    klass = SchoolClass.objects.create(school=school, level=level, name="Primary 3", order=3)
    section = Section.objects.create(school=school, school_class=klass, name="A")
    return level, klass, section


def make_pupil(school, klass, section, number="PRT/001"):
    return Student.objects.create(
        school=school, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number=number,
        current_class=klass, current_section=section,
    )


@pytest.fixture
def session(school_a):
    from apps.academics.models import AcademicSession

    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", is_current=True,
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )


@pytest.fixture
def period(school_a, session):
    from apps.academics.models import AcademicPeriod

    return session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )


@pytest.fixture
def structure(school_a):
    return make_structure(school_a)


@pytest.fixture
def pupil(school_a, structure):
    _, klass, section = structure
    return make_pupil(school_a, klass, section)


@pytest.fixture
def parent_linked(school_a, pupil, login_as):
    parent = login_as(school_a, Role.PARENT)
    GuardianLink.objects.create(
        school=school_a, student=pupil, guardian=parent,
    )
    return parent


# --- published result through the real workflow ---


def _publish_maths(school_a, structure, pupil, session, period, make_member, make_request):
    _, klass, section = structure
    maths = Subject.objects.create(school=school_a, name="Mathematics")
    ClassSubject.objects.create(school=school_a, school_class=klass, subject=maths)
    sheet = ResultSheet.objects.create(
        school=school_a, period=period, school_class=klass, section=section,
        subject=maths,
    )
    for name, max_score in (("First Test", 20), ("Second Test", 20), ("Examination", 60)):
        AssessmentComponent.objects.create(
            school=school_a, session=session, name=name,
            max_score=Decimal(max_score), weight=Decimal(max_score),
        )
    GradeScale.objects.create(school=school_a, session=session, name="Scale")
    GradeBoundary.objects.create(
        school=school_a, scale=GradeScale.objects.get(school=school_a),
        grade="A", min_percent=Decimal(70), remark="Excellent",
    )
    teacher = make_member(school_a, Role.TEACHER)
    TeacherAssignment.objects.create(
        school=school_a, teacher=teacher, session=session,
        school_class=klass, subject=maths, section=section,
    )
    t_request = make_request(school_a, Role.TEACHER, member=teacher)
    for component, value in zip(
        AssessmentComponent.objects.order_by("id"), (12, 15, 48),
    ):
        save_score(t_request, sheet, pupil, component, value)
    submit_sheet(t_request, sheet)
    admin = make_request(school_a, Role.ADMIN)
    review_sheet(admin, sheet)
    approve_sheet(admin, sheet)
    publish_sheet(admin, sheet)
    return sheet


@pytest.fixture
def published(school_a, structure, pupil, session, period, make_member, make_request):
    return _publish_maths(
        school_a, structure, pupil, session, period, make_member, make_request
    )


# --- fees ---


@pytest.fixture
def invoice(school_a, pupil, session, period, make_member):
    from apps.fees.models import FeeItem

    fee_item = FeeItem.objects.create(
        school=school_a, session=session, name="Tuition",
        charged=FeeItem.Charged.PER_TERM, is_active=True,
    )
    inv = Invoice.objects.create(
        school=school_a, student=pupil, session=session, period=period,
        number="INV-P001", issue_date=date(2026, 9, 15),
        due_date=date(2026, 10, 15),
    )
    InvoiceItem.objects.create(
        school=school_a, invoice=inv, fee_item=fee_item, description="Tuition",
        amount=Decimal("50000"),
    )
    bursar = make_member(school_a, Role.BURSAR)
    Payment.objects.create(
        school=school_a, invoice=inv, amount=Decimal("20000"),
        reference="PAY-001", paid_on=date(2026, 10, 1),
        received_by=bursar,
    )
    return inv


# --- tests ---


def test_parent_opens_own_child_page(
    client, pupil, parent_linked, period, published
):
    response = client.get(reverse("portal:child", args=[pupil.pk]))

    assert response.status_code == 200
    assert response.context["results"][0].percentage == Decimal("75.00")
    assert response.context["average"] == Decimal("75.0")
    assert response.context["invoices"] == []
    # the grade letter must be rendered, not just stored (regression: the
    # template once used a wrong field name so the column stayed empty)
    assert b">A<" in response.content


def test_child_page_shows_real_fee_balance(
    client, pupil, parent_linked, period, published, invoice
):
    response = client.get(reverse("portal:child", args=[pupil.pk]))

    invoices = response.context["invoices"]
    assert len(invoices) == 1
    assert invoices[0].item_total == Decimal("50000")
    assert invoices[0].paid_total == Decimal("20000")
    assert invoices[0].balance_due == Decimal("30000")
    assert response.context["owed"] == Decimal("30000")


def test_unpublished_results_are_hidden(
    client, pupil, parent_linked, period, structure
):
    """A draft/submitted sheet must not reach the parent page."""
    response = client.get(reverse("portal:child", args=[pupil.pk]))

    assert response.context["results"] == []


def test_another_parents_child_is_denied(
    client, school_a, structure, period, published, login_as
):
    _, klass, section = structure
    other_pupil = make_pupil(school_a, klass, section, number="PRT/002")
    login_as(school_a, Role.PARENT)

    response = client.get(reverse("portal:child", args=[other_pupil.pk]))

    assert response.status_code == 403


def test_child_in_the_other_school_is_404(
    client, school_a, school_b, login_as
):
    """Foreign student IDs never resolve, even through a guardian link."""
    login_as(school_a, Role.PARENT)
    _, klass, section = make_structure(school_b)
    foreign_pupil = make_pupil(school_b, klass, section, number="BS/001")

    response = client.get(reverse("portal:child", args=[foreign_pupil.pk]))

    assert response.status_code == 404


@pytest.mark.parametrize("role", [Role.TEACHER, Role.BURSAR])
def test_non_parents_cannot_open_a_child_page(
    client, school_a, login_as, pupil, published, role
):
    login_as(school_a, role)

    response = client.get(reverse("portal:child", args=[pupil.pk]))

    assert response.status_code == 403


def test_children_page_without_links_still_ok(client, school_a, login_as):
    login_as(school_a, Role.PARENT)
    response = client.get(reverse("portal:children"))
    assert response.status_code == 200


# --- step 3: parents open the report card ---


def test_parent_opens_the_report_card(
    client, pupil, parent_linked, period, published
):
    response = client.get(
        reverse("results:report_card", args=[pupil.pk, period.pk])
    )

    assert response.status_code == 200
    assert response.context["average"] == Decimal("75.0")


def test_parent_downloads_the_report_card_pdf(
    client, pupil, parent_linked, period, published
):
    response = client.get(
        reverse("results:report_card_pdf", args=[pupil.pk, period.pk])
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


def test_report_card_denied_without_guardian_link(
    client, school_a, structure, period, published, login_as
):
    login_as(school_a, Role.PARENT)
    _, klass, section = structure
    other_pupil = make_pupil(school_a, klass, section, number="PRT/009")

    response = client.get(
        reverse("results:report_card", args=[other_pupil.pk, period.pk])
    )

    assert response.status_code == 403


def test_foreign_school_report_card_is_404(
    client, school_a, school_b, login_as, structure, period
):
    """A pupil ID from another school can never be reached, even if a pupil
    with that ID exists in this school and the parent knows the period."""
    login_as(school_a, Role.PARENT)
    _, klass, section = make_structure(school_b)
    foreign_pupil = make_pupil(school_b, klass, section, number="BS/007")

    response = client.get(
        reverse("results:report_card", args=[foreign_pupil.pk, period.pk])
    )

    assert response.status_code == 404
