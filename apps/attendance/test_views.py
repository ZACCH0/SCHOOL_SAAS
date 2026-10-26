import pytest
from datetime import date
from django.urls import reverse

from apps.academics.models import AcademicSession
from apps.audit.models import AuditLog
from apps.classes.models import ClassTeacher, Level, SchoolClass, Section
from apps.schools.models import Membership
from apps.students.models import Student

from .models import AttendanceRecord, AttendanceSession

Role = Membership.Role
DAY = date(2026, 10, 26)


@pytest.fixture
def school_level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_three(school_a, school_level):
    return SchoolClass.objects.create(school=school_a, level=school_level, name="Primary 3", order=3)


@pytest.fixture
def section_a(school_a, primary_three):
    return Section.objects.create(school=school_a, school_class=primary_three, name="A")


@pytest.fixture
def session(school_a):
    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", is_current=True,
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )


@pytest.fixture
def period(session, school_a):
    return session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )


@pytest.fixture
def pupil(school_a, primary_three, section_a):
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three, current_section=section_a,
    )


def test_attendance_requires_login(client):
    assert client.get(reverse("attendance:home")).status_code == 302


@pytest.mark.django_db
def test_a_parent_cannot_open_attendance(client, school_a, login_as):
    login_as(school_a, Role.PARENT)
    assert client.get(reverse("attendance:home")).status_code == 403


@pytest.mark.django_db
def test_admin_sees_every_class_and_a_fresh_day_is_not_marked(
    client, school_a, session, primary_three, section_a, login_as
):
    login_as(school_a)
    content = client.get(reverse("attendance:home"), {"day": DAY.isoformat()}).content
    assert b"Primary 3" in content
    assert b"Not taken" in content


@pytest.mark.django_db
def test_admin_opens_a_register_from_home(
    client, school_a, session, period, primary_three, section_a, pupil, login_as
):
    login_as(school_a)
    response = client.post(
        reverse("attendance:open"),
        {"school_class": primary_three.pk, "section": section_a.pk, "day": DAY.isoformat()},
    )
    register = AttendanceSession.objects.get()
    assert response.url == reverse("attendance:register", args=[register.pk])
    assert AttendanceRecord.objects.filter(register=register).count() == 1
    assert AuditLog.objects.filter(action="attendance.register_opened").exists()


@pytest.mark.django_db
def test_teacher_sees_only_their_own_classes(
    client, school_a, session, primary_three, section_a, login_as
):
    other = SchoolClass.objects.create(
        school=school_a, level=primary_three.level, name="Primary 4", order=4
    )
    member = login_as(school_a, Role.TEACHER)
    ClassTeacher.objects.create(
        school=school_a, session=session, school_class=other, teacher=member, section=None,
    )
    content = client.get(reverse("attendance:home"), {"day": DAY.isoformat()}).content
    assert b"Primary 4" in content
    assert b"Primary 3" not in content


@pytest.mark.django_db
def test_marked_absent_with_a_remark(
    client, school_a, session, period, primary_three, section_a, pupil, login_as
):
    login_as(school_a)
    client.post(
        reverse("attendance:open"),
        {"school_class": primary_three.pk, "section": section_a.pk, "day": DAY.isoformat()},
    )
    register = AttendanceSession.objects.get()
    response = client.post(
        reverse("attendance:mark", args=[register.pk]),
        {"student": pupil.pk, "status": "absent", "remark": "No reason given"},
    )
    assert response.status_code == 302
    line = AttendanceRecord.objects.get(register=register)
    assert line.status == "absent"
    assert line.remark == "No reason given"
    assert AuditLog.objects.filter(action="attendance.marked").exists()


@pytest.mark.django_db
def test_a_pupil_of_another_school_is_refused(
    client, school_a, school_b, session, period, primary_three, section_a, login_as
):
    login_as(school_a)
    outsider = Student.objects.create(
        school=school_b, first_name="Neto", last_name="Stranger", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="BJ/2026/001",
    )
    register = AttendanceSession.objects.create(
        school=school_a, school_class=primary_three, section=section_a,
        date=DAY, session=session,
    )
    client.post(
        reverse("attendance:mark", args=[register.pk]),
        {"student": outsider.pk, "status": "present"},
    )
    assert not AttendanceRecord.objects.exists()


@pytest.mark.django_db
def test_a_future_day_cannot_be_opened(
    client, school_a, session, period, primary_three, section_a, login_as
):
    login_as(school_a)
    response = client.post(
        reverse("attendance:open"),
        {
            "school_class": primary_three.pk, "section": section_a.pk,
            "day": date(2030, 1, 1).isoformat(),
        },
        follow=True,
    )
    assert b"future day" in response.content
    assert not AttendanceSession.objects.exists()


@pytest.mark.django_db
def test_read_only_after_the_term(
    session, school_a, primary_three, section_a, client, login_as
):
    old_session = AcademicSession.objects.create(
        school=school_a, name="2025/2026",
        start_date=date(2025, 9, 1), end_date=date(2026, 7, 31),
    )
    reg = AttendanceSession.objects.create(
        school=school_a, school_class=primary_three, section=section_a,
        date=date(2026, 3, 5), session=old_session,
    )
    login_as(school_a, Role.ADMIN)
    content = client.get(reverse("attendance:register", args=[reg.pk])).content
    assert b"Read-only" in content
