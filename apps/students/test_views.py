import pytest
from datetime import date
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass, Section
from apps.schools.models import Membership

from .models import GuardianLink, Student, StudentClassHistory
from .services import create_student

Role = Membership.Role


@pytest.fixture
def level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_three(school_a, level):
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 3", order=3)


@pytest.fixture
def section_a(school_a, primary_three):
    return Section.objects.create(school=school_a, school_class=primary_three, name="A")


@pytest.fixture
def student(school_a, primary_three):
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three,
    )


def test_student_list_requires_login(client):
    response = client.get(reverse("students:list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_a_teacher_cannot_open_the_student_list(client, school_a, login_as):
    login_as(school_a, Role.TEACHER)
    assert client.get(reverse("students:list")).status_code == 403


@pytest.mark.django_db
def test_admin_cannot_open_another_schools_student(
    client, school_a, school_b, login_as, student
):
    login_as(school_b)
    assert client.get(reverse("students:detail", args=[student.pk])).status_code == 404
    assert not Student.objects.for_school(school_b).exists()


@pytest.mark.django_db
def test_admin_enrols_a_student(
    client, school_a, level, primary_three, section_a, login_as, make_session
):
    make_session(school_a, current=True)
    login_as(school_a)
    response = client.post(
        reverse("students:create"),
        {
            "first_name": "Blessing", "last_name": "Ige", "sex": "female",
            "date_of_birth": "2019-01-10", "admission_number": "FSS/2026/002",
            "address": "1 Isale Taba Road",
            "current_class": primary_three.pk,
            "current_section": section_a.pk,
        },
    )
    created = Student.objects.get(admission_number="FSS/2026/002")
    assert response.status_code == 302
    assert response.url == reverse("students:detail", args=[created.pk])
    assert AuditLog.objects.filter(action="student.created").exists()
    assert StudentClassHistory.objects.filter(student=created).exists()


@pytest.mark.django_db
def test_duplicate_admission_number_shows_a_friendly_message(
    client, school_a, level, primary_three, login_as, student
):
    login_as(school_a)
    response = client.post(
        reverse("students:create"),
        {
            "first_name": "Tobi", "last_name": "Raji", "sex": "male",
            "date_of_birth": "2019-02-02", "admission_number": "FSS/2026/001",
        },
    )
    assert response.status_code == 200
    assert b"already" in response.content
    assert Student.objects.count() == 1


@pytest.mark.django_db
def test_foreign_class_is_rejected_on_create(
    client, school_a, school_b, login_as
):
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Cheeky", order=1)
    login_as(school_a)
    client.post(
        reverse("students:create"),
        {
            "first_name": "Nope", "last_name": "Nguyen", "sex": "male",
            "date_of_birth": "2018-01-01", "admission_number": "TRY/001",
            "current_class": class_b.pk,
        },
    )
    assert not Student.objects.for_school(school_a).filter(first_name="Nope").exists()


@pytest.mark.django_db
def test_status_change_needs_post(client, school_a, login_as, student):
    login_as(school_a)
    assert client.get(reverse("students:status", args=[student.pk])).status_code == 405


@pytest.mark.django_db
def test_admin_changes_status(client, school_a, login_as, student):
    login_as(school_a)
    client.post(reverse("students:status", args=[student.pk]), {"status": "suspended"})
    student.refresh_from_db()
    assert student.status == "suspended"


@pytest.mark.django_db
def test_admin_moves_a_student(
    client, school_a, level, primary_three, login_as, student, make_session
):
    make_session(school_a, current=True)
    primary_four = SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)
    login_as(school_a)
    client.post(
        reverse("students:move", args=[student.pk]),
        {"school_class": primary_four.pk, "section": ""},
    )
    student.refresh_from_db()
    assert student.current_class == primary_four
    history = StudentClassHistory.objects.get(student=student)
    assert history.school_class == primary_four


@pytest.mark.django_db
def test_link_guardian_only_to_a_parent(
    client, school_a, level, primary_three, student, login_as, make_member
):
    login_as(school_a)
    teacher = make_member(school_a)
    client.post(
        reverse("students:guardian_add", args=[student.pk]),
        {"guardian": teacher.pk, "relationship": "guardian"},
    )
    assert not GuardianLink.objects.exists()


@pytest.mark.django_db
def test_admin_links_a_parent(
    client, school_a, level, primary_three, student, login_as, make_member
):
    login_as(school_a)
    parent = make_member(school_a, role=Role.PARENT)
    client.post(
        reverse("students:guardian_add", args=[student.pk]),
        {"guardian": parent.pk, "relationship": "father", "is_primary": "on"},
    )
    link = GuardianLink.objects.get()
    assert link.guardian == parent and link.is_primary


@pytest.mark.django_db
def test_guardian_is_removed(client, school_a, level, primary_three, student, login_as, make_member):
    login_as(school_a)
    parent = make_member(school_a, role=Role.PARENT)
    link = GuardianLink.objects.create(school=school_a, student=student, guardian=parent)
    client.post(reverse("students:guardian_remove", args=[student.pk, link.pk]))
    assert not GuardianLink.objects.exists()


@pytest.mark.django_db
def test_nav_shows_students_to_managers(client, school_a, login_as):
    login_as(school_a)
    assert reverse("students:list").encode() in client.get(reverse("core:dashboard")).content
    client.logout()
    login_as(school_a, Role.TEACHER)
    assert reverse("students:list").encode() not in client.get(reverse("core:dashboard")).content
