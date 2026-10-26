import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass
from apps.schools.models import Membership

from .models import ClassSubject, Subject, TeacherAssignment

Role = Membership.Role


@pytest.fixture
def primary_four(school_a):
    level = Level.objects.create(school=school_a, name="Primary", order=1)
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)


@pytest.fixture
def maths(school_a):
    return Subject.objects.create(school=school_a, name="Mathematics")


@pytest.fixture
def taught_class(primary_four, maths, school_a):
    ClassSubject.objects.create(school=school_a, school_class=primary_four, subject=maths)
    return primary_four


@pytest.mark.django_db
def test_a_teacher_cannot_open_the_subject_list(client, school_a, login_as):
    login_as(school_a, Role.TEACHER)
    assert client.get(reverse("subjects:list")).status_code == 403


@pytest.mark.django_db
def test_admin_creates_a_subject_and_sees_it_listed(client, school_a, login_as):
    login_as(school_a)
    response = client.post(reverse("subjects:create"), {"name": "Biology", "code": "BIO"})
    assert response.status_code == 302
    assert b"Biology" in client.get(reverse("subjects:list")).content
    assert AuditLog.objects.filter(action="subject.created").exists()


@pytest.mark.django_db
def test_duplicate_subject_shows_a_friendly_message(client, school_a, login_as, maths):
    login_as(school_a)
    response = client.post(reverse("subjects:create"), {"name": "mathematics", "code": ""})
    assert response.status_code == 200
    assert b"already exists" in response.content


@pytest.mark.django_db
def test_admin_adds_a_subject_to_a_class(client, school_a, login_as, primary_four, maths):
    login_as(school_a)
    client.post(reverse("subjects:class_add", args=[primary_four.pk]), {"subject": maths.pk})
    assert ClassSubject.objects.filter(school_class=primary_four, subject=maths).exists()
    assert AuditLog.objects.filter(action="class_subject.added").exists()


@pytest.mark.django_db
def test_admin_assigns_a_teacher_with_the_current_session(
    client, school_a, login_as, taught_class, maths, make_member, make_session
):
    login_as(school_a)
    make_session(school_a, current=True)
    teacher = make_member(school_a)
    client.post(
        reverse("subjects:assign_teacher", args=[taught_class.pk]),
        {"subject": maths.pk, "teacher": teacher.pk},
    )
    assert TeacherAssignment.objects.get().teacher == teacher


@pytest.mark.django_db
def test_a_teacher_from_another_school_cannot_be_assigned(
    client, school_a, school_b, login_as, taught_class, maths, make_member, make_session
):
    login_as(school_a)
    make_session(school_a, current=True)
    foreign = make_member(school_b)
    client.post(
        reverse("subjects:assign_teacher", args=[taught_class.pk]),
        {"subject": maths.pk, "teacher": foreign.pk},
    )
    assert not TeacherAssignment.objects.exists()


@pytest.mark.django_db
def test_removing_a_subject_with_a_teacher_shows_a_message(
    client, school_a, login_as, taught_class, maths, make_member, make_session
):
    login_as(school_a)
    TeacherAssignment.objects.create(
        school=school_a, school_class=taught_class, subject=maths,
        teacher=make_member(school_a), session=make_session(school_a),
    )
    response = client.post(
        reverse("subjects:class_remove", args=[taught_class.pk, maths.pk]), follow=True
    )
    assert b"teacher assignments" in response.content
    assert ClassSubject.objects.count() == 1


@pytest.mark.django_db
def test_another_schools_assignment_cannot_be_removed(
    client, school_a, school_b, login_as, taught_class, maths, make_member, make_session
):
    assignment = TeacherAssignment.objects.create(
        school=school_a, school_class=taught_class, subject=maths,
        teacher=make_member(school_a), session=make_session(school_a),
    )
    login_as(school_b)
    response = client.post(reverse("subjects:unassign_teacher", args=[assignment.pk]))
    assert response.status_code == 404
    assert TeacherAssignment.objects.count() == 1
