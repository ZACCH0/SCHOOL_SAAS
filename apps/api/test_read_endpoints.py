from datetime import date, time
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token

from apps.announcements.models import Announcement
from apps.classes.models import Level, SchoolClass, Section
from apps.fees.models import FeeItem, Invoice, InvoiceItem, Payment
from apps.results.models import ResultSheet, SubjectResult
from apps.schools.models import Membership
from apps.students.models import GuardianLink, Student
from apps.subjects.models import ClassSubject, Subject, TeacherAssignment
from apps.timetable.models import TimetableSlot

pytestmark = pytest.mark.django_db

Role = Membership.Role


@pytest.fixture
def structure(school_a):
    level = Level.objects.create(school=school_a, name="Primary", order=1)
    klass = SchoolClass.objects.create(school=school_a, level=level, name="Primary 3", order=3)
    section = Section.objects.create(school=school_a, school_class=klass, name="A")
    return level, klass, section


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
def pupil(school_a, structure):
    _, klass, section = structure
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="PRT/001",
        current_class=klass, current_section=section,
    )


@pytest.fixture
def parent_token(school_a, pupil, session, period, login_as):
    """A parent membership of school A, linked to the pupil, with a token."""
    parent = login_as(school_a, Role.PARENT)
    GuardianLink.objects.create(school=school_a, student=pupil, guardian=parent)
    return parent, Token.objects.create(user=parent.user)


def api_get(client, token, name, path_kwargs=None, **extra):
    return client.get(
        reverse(f"api:{name}", kwargs=path_kwargs or {}),
        HTTP_AUTHORIZATION=f"Token {token.key}",
        **extra,
    )


def publish_subject(school_a, structure, pupil, session, period, member, name="Mathematics"):
    """A published sheet + result row, the light way (no full workflow)."""
    _, klass, section = structure
    subject = Subject.objects.create(school=school_a, name=name)
    ClassSubject.objects.create(school=school_a, school_class=klass, subject=subject)
    sheet = ResultSheet.objects.create(
        school=school_a, period=period, school_class=klass, section=section,
        subject=subject, status=ResultSheet.Status.PUBLISHED, submitted_by=member,
    )
    return SubjectResult.objects.create(
        school=school_a, sheet=sheet, student=pupil,
        total=Decimal("75"), percentage=Decimal("75.0"),
        grade="A", grade_remark="Excellent",
    )


def add_invoice(
    school_a, pupil, session, period, received_by,
    items=Decimal("15000"), paid=Decimal("0"),
):
    invoice = Invoice.objects.create(
        school=school_a, student=pupil, session=session, period=period,
        number=f"INV/{Invoice.objects.count() + 1:04d}",
        issue_date=date(2026, 9, 14), due_date=date(2026, 10, 14),
    )
    fee_item = FeeItem.objects.create(school=school_a, session=session, name="Tuition")
    InvoiceItem.objects.create(
        school=school_a, invoice=invoice, fee_item=fee_item,
        description="Tuition", amount=items,
    )
    if paid:
        Payment.objects.create(
            school=school_a, invoice=invoice, amount=paid,
            method=Payment.Method.CASH, reference=f"PAY/{invoice.number}",
            paid_on=date(2026, 9, 20), received_by=received_by,
        )
    return invoice


# --- me ---


def test_me_reports_school_role_session_and_period(client, parent_token, session, period):
    _, token = parent_token

    response = api_get(client, token, "me")

    assert response.status_code == 200
    body = response.json()
    assert body["school"] == "Alpha School"
    assert body["role"] == Role.PARENT
    assert body["session"] == "2026/2027"
    assert body["period"] == "First Term"


def test_me_refuses_a_user_without_membership(client, db, school_a, make_member):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user("bare1", password="S3cure-pass!")
    token = Token.objects.create(user=user)

    assert api_get(client, token, "me").status_code == 403


def test_me_refuses_a_multi_school_user_until_they_choose(client, db, school_a, school_b, make_member):
    """A device cannot choose a school; the API acts for single-membership users only."""
    member = make_member(school_a, Role.PARENT)
    user = member.user
    Membership.objects.create(user=user, school=school_b, role=Role.PARENT)
    token = Token.objects.create(user=user)

    assert api_get(client, token, "me").status_code == 403


def test_anonymous_requests_are_unauthorized(client, db):
    response = client.get(reverse("api:me"))

    assert response.status_code == 401


@pytest.mark.parametrize("role", [Role.OWNER, Role.ADMIN, Role.TEACHER, Role.BURSAR])
def test_children_endpoints_refuse_wrong_roles(client, school_a, pupil, login_as, role):
    member = login_as(school_a, role)
    token = Token.objects.create(user=member.user)

    assert api_get(client, token, "children").status_code == 403
    assert api_get(
        client, token, "child-results", path_kwargs={"pk": pupil.pk}
    ).status_code == 403


@pytest.mark.parametrize(
    "role", [Role.OWNER, Role.ADMIN, Role.BURSAR, Role.PARENT]
)
def test_my_timetable_refuses_non_teachers(client, school_a, login_as, role):
    member = login_as(school_a, role)
    token = Token.objects.create(user=member.user)

    assert api_get(client, token, "my-timetable").status_code == 403


# --- children ---


def test_children_lists_linked_children_with_owed_and_published(
    client, school_a, parent_token, session, period, structure, pupil, make_member
):
    parent, token = parent_token
    add_invoice(
        school_a, pupil, session, period, received_by=parent,
        items=Decimal("15000"), paid=Decimal("5000"),
    )
    member = make_member(school_a, Role.TEACHER)
    publish_subject(school_a, structure, pupil, session, period, member)

    response = api_get(client, token, "children")

    assert response.status_code == 200
    body = response.json()
    assert len(body["children"]) == 1
    child = body["children"][0]
    assert child["first_name"] == "Ade"
    assert child["class"].startswith("Primary 3")
    assert child["owed"] == "10000.00"
    assert child["published_results"] == 1


def test_children_never_show_an_unlinked_pupil(client, parent_token, structure, pupil):
    parent, token = parent_token
    _, klass, section = structure
    other = Student.objects.create(
        school=pupil.school, first_name="Bola", last_name="Bello", sex="female",
        date_of_birth=date(2018, 4, 4), admission_number="PRT/002",
        current_class=klass, current_section=section,
    )

    response = api_get(client, token, "children")

    ids = [c["id"] for c in response.json()["children"]]
    assert pupil.pk in ids
    assert other.pk not in ids


def test_children_tenant_isolation(client, school_a, school_b, parent_token, pupil, structure):
    """Children of a school B membership must never appear while acting for school A."""
    parent, token = parent_token
    _, klass, section = structure
    child_b = Student.objects.create(
        school=school_b, first_name="Bisi", last_name="Balogun", sex="female",
        date_of_birth=date(2018, 5, 5), admission_number="BS/001",
        current_class=None,
    )
    Membership.objects.filter(pk=parent.pk).update(school=school_b)  # keep parent in A
    assert child_b.school_id != pupil.school_id

    response = api_get(client, token, "children")

    ids = [c["id"] for c in response.json()["children"]]
    assert child_b.pk not in ids


# --- child results ---


def test_child_results_returns_published_rows_with_average(
    client, school_a, parent_token, session, period, structure, pupil, make_member
):
    _, token = parent_token
    member = make_member(school_a, Role.TEACHER)
    publish_subject(school_a, structure, pupil, session, period, member)

    response = api_get(client, token, "child-results", path_kwargs={"pk": pupil.pk})

    assert response.status_code == 200
    body = response.json()
    assert body["student"]["first_name"] == "Ade"
    assert body["period"] == "First Term"
    assert body["average"] == "75.0"
    assert body["results"][0]["subject"] == "Mathematics"
    assert body["results"][0]["grade"] == "A"


def test_child_results_hide_unpublished_sheets(
    client, school_a, parent_token, session, period, structure, pupil, make_member
):
    _, token = parent_token
    member = make_member(school_a, Role.TEACHER)
    _, klass, section = structure
    subject = Subject.objects.create(school=school_a, name="English")
    ClassSubject.objects.create(school=school_a, school_class=klass, subject=subject)
    ResultSheet.objects.create(
        school=school_a, period=period, school_class=klass, section=section,
        subject=subject, status=ResultSheet.Status.APPROVED, submitted_by=member,
    )

    response = api_get(client, token, "child-results", path_kwargs={"pk": pupil.pk})

    assert response.json()["results"] == []
    assert response.json()["average"] is None


def test_child_results_404_for_an_unlinked_pupil(client, parent_token, structure, pupil):
    _, token = parent_token
    _, klass, section = structure
    other = Student.objects.create(
        school=pupil.school, first_name="Bola", last_name="Bello", sex="female",
        date_of_birth=date(2018, 4, 4), admission_number="PRT/002",
        current_class=klass, current_section=section,
    )

    response = api_get(client, token, "child-results", path_kwargs={"pk": other.pk})

    assert response.status_code == 404


def test_child_results_404_for_another_schools_pupil_by_id(
    client, school_b, parent_token, pupil, structure
):
    _, token = parent_token
    child_b = Student.objects.create(
        school=school_b, first_name="Bisi", last_name="Balogun", sex="female",
        date_of_birth=date(2018, 5, 5), admission_number="BS/001",
        current_class=None,
    )

    response = api_get(client, token, "child-results", path_kwargs={"pk": child_b.pk})

    assert response.status_code == 404


def test_child_results_404_for_a_non_numeric_id(client, parent_token):
    _, token = parent_token

    response = client.get(
        "/api/v1/children/not-a-number/results/",
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    assert response.status_code == 404


# --- announcements ---


def _notice(school, title, audience, publisher):
    return Announcement.objects.create(
        school=school, title=title, body=f"Body of {title}",
        audience=audience, published_by=publisher,
    )


def test_announcements_follow_the_audience_rule(
    client, school_a, parent_token, session, make_member
):
    manager = make_member(school_a, Role.ADMIN)
    staff_only = _notice(school_a, "Staff only", Announcement.Audience.STAFF, manager)
    everyone = _notice(school_a, "Everyone", Announcement.Audience.EVERYONE, manager)
    parents = _notice(school_a, "Parents", Announcement.Audience.PARENTS, manager)
    teachers = _notice(school_a, "Teachers", Announcement.Audience.TEACHERS, manager)
    _, token = parent_token

    response = api_get(client, token, "announcements")

    titles = [a["title"] for a in response.json()["announcements"]]
    assert everyone.title in titles
    assert parents.title in titles
    assert staff_only.title not in titles
    assert teachers.title not in titles


def test_announcements_managers_see_every_audience(client, school_a, session, make_member):
    manager = make_member(school_a, Role.ADMIN)
    _notice(school_a, "Staff only", Announcement.Audience.STAFF, manager)
    _notice(school_a, "Teachers", Announcement.Audience.TEACHERS, manager)
    token = Token.objects.create(user=manager.user)

    response = api_get(client, token, "announcements")

    assert len(response.json()["announcements"]) == 2


def test_announcements_archived_never_shown(
    client, school_a, parent_token, session, make_member
):
    manager = make_member(school_a, Role.ADMIN)
    live = _notice(school_a, "Live", Announcement.Audience.EVERYONE, manager)
    gone = _notice(school_a, "Gone", Announcement.Audience.EVERYONE, manager)
    gone.is_active = False
    gone.save()
    _, token = parent_token

    response = api_get(client, token, "announcements")

    titles = [a["title"] for a in response.json()["announcements"]]
    assert titles == [live.title]


def test_announcements_tenant_isolation(client, school_a, school_b, parent_token, session, make_member):
    manager_b = make_member(school_b, Role.ADMIN)
    _notice(school_b, "Beta only", Announcement.Audience.EVERYONE, manager_b)
    _, token = parent_token

    response = api_get(client, token, "announcements")

    titles = [a["title"] for a in response.json()["announcements"]]
    assert "Beta only" not in titles


# --- my timetable ---


def _slot(school, session, klass, section, subject, day, starts, ends, label=None):
    return TimetableSlot.objects.create(
        school=school, session=session, school_class=klass, section=section,
        subject=subject, day=day, starts_at=starts, ends_at=ends, label=label or "",
    )


def test_my_timetable_lists_only_the_teachers_own_lessons(
    client, school_a, session, structure, make_member
):
    _, klass, section = structure
    teacher = make_member(school_a, Role.TEACHER)
    maths = Subject.objects.create(school=school_a, name="Mathematics")
    ClassSubject.objects.create(school=school_a, school_class=klass, subject=maths)
    english = Subject.objects.create(school=school_a, name="English")
    ClassSubject.objects.create(school=school_a, school_class=klass, subject=english)
    TeacherAssignment.objects.create(
        school=school_a, teacher=teacher, session=session,
        school_class=klass, subject=maths, section=section,
    )
    mine = _slot(school_a, session, klass, section, maths, 1, time(9, 0), time(9, 40))
    _slot(school_a, session, klass, section, english, 1, time(9, 40), time(10, 20))
    _slot(
        school_a, session, klass, section, None, 1,
        time(10, 20), time(10, 40), label="Long break",
    )
    token = Token.objects.create(user=teacher.user)

    response = api_get(client, token, "my-timetable")

    body = response.json()
    assert body["session"] == "2026/2027"
    assert len(body["days"]) == 1
    slots = body["days"][0]["slots"]
    assert [s["subject"] for s in slots] == ["Mathematics"]
    assert slots[0]["class"].startswith("Primary 3")


def test_my_timetable_403_for_non_teachers(client, school_a, session, login_as):
    member = login_as(school_a, Role.PARENT)
    token = Token.objects.create(user=member.user)

    assert api_get(client, token, "my-timetable").status_code == 403


def test_my_timetable_empty_without_a_current_session(client, school_a, login_as):
    teacher = login_as(school_a, Role.TEACHER)
    token = Token.objects.create(user=teacher.user)

    response = api_get(client, token, "my-timetable")

    assert response.status_code == 200
    assert response.json() == {"session": None, "days": []}
