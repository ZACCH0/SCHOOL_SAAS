from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.schools.models import Membership
from apps.students.models import GuardianLink, Student
from apps.students.services import create_parent

pytestmark = pytest.mark.django_db

ROLE = Membership.Role
User = get_user_model()


def add_link(school, parent_membership, number):
    student = Student.objects.create(
        school=school, first_name="Child", last_name=f"Of{number}", sex="male",
        date_of_birth=date(2018, 1, 5), admission_number=f"PL/{number}",
    )
    return GuardianLink.objects.create(
        school=school, student=student, guardian=parent_membership,
    )


def test_office_lists_parent_accounts_with_children_count(
    client, school_a, make_member, login_as
):
    admin = login_as(school_a, ROLE.ADMIN)
    parent = make_member(school_a, ROLE.PARENT)
    make_member(school_a, ROLE.TEACHER)
    add_link(school_a, parent, 1)
    add_link(school_a, parent, 2)

    response = client.get(reverse("students:parent_list"))

    assert response.status_code == 200
    rows = [(p.user.username, p.child_count) for p in response.context["parents"]]
    usernames = [pk for pk, _ in rows]
    assert usernames == [parent.user.username]
    assert rows[0][1] == 2


def test_create_parent_creates_user_membership_and_audit(client, school_a, login_as):
    login_as(school_a, ROLE.ADMIN)

    response = client.post(
        reverse("students:parent_create"),
        {
            "username": "newparent",
            "password": "S3cure-pass!",
            "first_name": "Kola",
            "last_name": "Adeyemi",
            "email": "kola@example.com",
            "phone": "08012345678",
        },
    )
    if response.status_code != 302:
        print(response.context["form"].errors)

    assert response.status_code == 302
    user = User.objects.get(username="newparent")
    assert user.first_name == "Kola"
    assert user.check_password("S3cure-pass!")
    assert user.email == "kola@example.com"
    assert user.phone == "08012345678"
    assert Membership.objects.filter(
        school=school_a, user=user, role=ROLE.PARENT
    ).exists()
    membership = Membership.objects.get(school=school_a, user=user)
    assert AuditLog.objects.filter(
        school=school_a, action="parent.account_created",
        target_type=Membership._meta.label, target_id=membership.pk,
    ).exists()


def test_create_parent_rejects_duplicate_username(
    client, school_a, school_b, login_as, make_member
):
    login_as(school_a, ROLE.ADMIN)
    parent_b = make_member(school_b, ROLE.PARENT)  # same username must clash

    response = client.post(
        reverse("students:parent_create"),
        {
            "username": parent_b.user.username,
            "password": "S3cure-pass!",
            "first_name": "Kola",
            "last_name": "Adeyemi",
        },
    )

    assert response.status_code == 200
    assert "already taken" in str(response.context["form"].errors)


def test_create_parent_rejects_weak_password(client, school_a, login_as):
    login_as(school_a, ROLE.ADMIN)

    response = client.post(
        reverse("students:parent_create"),
        {
            "username": "weakpw",
            "password": "123",
            "first_name": "Kola",
            "last_name": "Adeyemi",
        },
    )

    assert response.status_code == 200
    assert not User.objects.filter(username="weakpw").exists()


@pytest.mark.parametrize("url_name", ["students:parent_list", "students:parent_create"])
@pytest.mark.parametrize("role", [ROLE.TEACHER, ROLE.BURSAR, ROLE.PARENT])
def test_non_managers_cannot_manage_parents(client, school_a, login_as, role, url_name):
    login_as(school_a, role)

    response = client.get(reverse(url_name))

    assert response.status_code == 403


def test_service_validates_username_rule(make_request, school_a):
    request = make_request(school_a, ROLE.ADMIN)
    with pytest.raises(Exception):
        create_parent(
            request, username="bad name!", password="S3cure-pass!",
            first_name="Kola", last_name="Adeyemi",
        )
    assert not User.objects.filter(username="bad name!").exists()
