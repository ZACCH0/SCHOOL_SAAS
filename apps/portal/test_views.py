from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.schools.models import Membership
from apps.students.models import GuardianLink, Student

pytestmark = pytest.mark.django_db

ROLE = Membership.Role


@pytest.fixture
def create_user():
    username = f"parent-portal-{get_user_model().objects.count()}"
    return get_user_model().objects.create_user(username, password="S3cure-pass!")


def make_student(school, first="Ada", last="Adebayo", number=None):
    number = number or f"ADM/{Student.objects.count() + 1:03d}"
    return Student.objects.create(
        school=school,
        first_name=first,
        last_name=last,
        sex="male",
        date_of_birth=date(2018, 1, 5),
        admission_number=number,
    )


def link(parent_membership, student):
    return GuardianLink.objects.create(
        school=parent_membership.school, guardian=parent_membership, student=student
    )


def test_parent_sees_linked_children(client, school_a, login_as):
    parent = login_as(school_a, ROLE.PARENT)
    linked = make_student(school_a, first="Ada", number="ADM/001")
    other = make_student(school_a, first="Bola", number="ADM/002")
    link(parent, linked)

    response = client.get(reverse("portal:children"))

    assert response.status_code == 200
    names = [c.first_name for c in response.context["children"]]
    assert names == ["Ada"]
    assert other not in response.context["children"]


def test_parent_with_no_links_sees_empty_page(client, school_a, school_b, login_as):
    login_as(school_a, ROLE.PARENT)
    make_student(school_b, number="BS/001")

    response = client.get(reverse("portal:children"))

    assert response.status_code == 200
    assert response.context["children"] == []


def test_link_in_the_other_school_does_not_leak(client, school_a, school_b, create_user):
    """One parent may belong to two schools. While acting in school A, the
    school B children of the same user must not appear."""
    membership_a = Membership.objects.create(
        user=create_user, school=school_a, role=ROLE.PARENT
    )
    membership_b = Membership.objects.create(
        user=create_user, school=school_b, role=ROLE.PARENT
    )
    child_b = make_student(school_b, number="BS/001")
    link(membership_b, child_b)
    client.force_login(create_user)
    client.session[apps_schools_session_key()] = membership_a.pk
    client.session.save()


def apps_schools_session_key():
    from apps.schools.middleware import SESSION_KEY

    return SESSION_KEY

    response = client.get(reverse("portal:children"))

    assert response.context["children"] == []


@pytest.mark.parametrize("role", [ROLE.OWNER, ROLE.ADMIN, ROLE.TEACHER, ROLE.BURSAR])
def test_non_parents_get_403(client, school_a, login_as, role):
    login_as(school_a, role)

    response = client.get(reverse("portal:children"))

    assert response.status_code == 403


def test_login_required(client, db):
    response = client.get(reverse("portal:children"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url
