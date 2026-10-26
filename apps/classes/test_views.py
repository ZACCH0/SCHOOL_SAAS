import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.schools.models import Membership
from apps.subjects.models import ClassSubject, Subject, TeacherAssignment

from .models import ClassTeacher, Level, SchoolClass, Section

Role = Membership.Role


@pytest.fixture
def level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_four(school_a, level):
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)


def test_class_list_requires_login(client):
    response = client.get(reverse("classes:list"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


@pytest.mark.django_db
def test_a_teacher_cannot_open_the_class_list(client, school_a, login_as):
    login_as(school_a, Role.TEACHER)
    assert client.get(reverse("classes:list")).status_code == 403


@pytest.mark.django_db
def test_admin_sees_only_their_own_schools_classes(
    client, school_a, school_b, login_as, primary_four
):
    other_level = Level.objects.create(school=school_b, name="Primary", order=1)
    SchoolClass.objects.create(school=school_b, level=other_level, name="Secret Class", order=1)
    login_as(school_a)
    content = client.get(reverse("classes:list")).content
    assert b"Primary 4" in content
    assert b"Secret Class" not in content


@pytest.mark.django_db
def test_admin_creates_a_class(client, school_a, level, login_as):
    login_as(school_a)
    response = client.post(
        reverse("classes:create"), {"level": level.pk, "name": "Primary 5", "order": 5}
    )
    created = SchoolClass.objects.get(name="Primary 5")
    assert response.status_code == 302
    assert response.url == reverse("classes:detail", args=[created.pk])
    assert AuditLog.objects.filter(action="class.created").exists()


@pytest.mark.django_db
def test_duplicate_class_shows_a_friendly_message(client, school_a, level, login_as, primary_four):
    login_as(school_a)
    response = client.post(
        reverse("classes:create"), {"level": level.pk, "name": "primary 4", "order": 9}
    )
    assert response.status_code == 200
    assert b"already exists" in response.content
    assert SchoolClass.objects.count() == 1


@pytest.mark.django_db
def test_a_level_from_another_school_is_rejected(client, school_a, school_b, login_as):
    foreign_level = Level.objects.create(school=school_b, name="Primary", order=1)
    login_as(school_a)
    response = client.post(
        reverse("classes:create"), {"level": foreign_level.pk, "name": "Sneaky", "order": 1}
    )
    assert response.status_code == 200
    assert not SchoolClass.objects.filter(name="Sneaky").exists()


@pytest.mark.django_db
def test_another_schools_class_is_a_404(client, school_b, login_as, primary_four):
    login_as(school_b)
    assert client.get(reverse("classes:detail", args=[primary_four.pk])).status_code == 404


@pytest.mark.django_db
def test_toggle_needs_post_and_deactivates(client, school_a, login_as, primary_four):
    login_as(school_a)
    url = reverse("classes:toggle", args=[primary_four.pk])
    assert client.get(url).status_code == 405
    assert client.post(url).status_code == 302
    primary_four.refresh_from_db()
    assert primary_four.is_active is False


@pytest.mark.django_db
def test_admin_adds_a_section(client, school_a, login_as, primary_four):
    login_as(school_a)
    client.post(reverse("classes:section_add", args=[primary_four.pk]), {"name": "A"})
    assert Section.objects.filter(school_class=primary_four, name="A").exists()


@pytest.mark.django_db
def test_class_teacher_needs_a_current_session(
    client, school_a, login_as, primary_four, make_member
):
    login_as(school_a)
    teacher = make_member(school_a)
    response = client.post(
        reverse("classes:class_teacher", args=[primary_four.pk]),
        {"teacher": teacher.pk}, follow=True,
    )
    assert b"current academic session" in response.content
    assert not ClassTeacher.objects.exists()


@pytest.mark.django_db
def test_class_teacher_is_saved_with_a_current_session(
    client, school_a, login_as, primary_four, make_member, make_session
):
    login_as(school_a)
    make_session(school_a, current=True)
    teacher = make_member(school_a)
    client.post(
        reverse("classes:class_teacher", args=[primary_four.pk]), {"teacher": teacher.pk}
    )
    assert ClassTeacher.objects.get().teacher == teacher


@pytest.mark.django_db
def test_class_detail_shows_subjects_and_their_teacher(
    client, school_a, login_as, primary_four, make_member, make_session
):
    login_as(school_a)
    session = make_session(school_a, current=True)
    maths = Subject.objects.create(school=school_a, name="Mathematics")
    ClassSubject.objects.create(school=school_a, school_class=primary_four, subject=maths)
    teacher = make_member(school_a)
    TeacherAssignment.objects.create(
        school=school_a, school_class=primary_four, subject=maths,
        teacher=teacher, session=session,
    )
    response = client.get(reverse("classes:detail", args=[primary_four.pk]))
    assert response.status_code == 200
    assert b"Mathematics" in response.content
    assert teacher.user.get_username().encode() in response.content


@pytest.mark.django_db
def test_menu_shows_classes_only_to_managers(client, school_a, login_as):
    login_as(school_a, Role.ADMIN)
    assert reverse("classes:list").encode() in client.get(reverse("core:dashboard")).content
    client.logout()
    login_as(school_a, Role.TEACHER)
    assert reverse("classes:list").encode() not in client.get(reverse("core:dashboard")).content
