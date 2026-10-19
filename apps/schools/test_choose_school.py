import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from .middleware import SESSION_KEY
from .models import Membership, School

User = get_user_model()
Role = Membership.Role


@pytest.fixture
def user():
    return User.objects.create_user("teacher1", password="S3cure-pass!")


@pytest.fixture
def two_schools():
    return (
        School.objects.create(name="Alpha School", slug="alpha"),
        School.objects.create(name="Beta School", slug="beta"),
    )


@pytest.mark.django_db
def test_choose_requires_login(client):
    response = client.get(reverse("schools:choose"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))

@pytest.mark.django_db
def test_chooser_lists_only_own_memberships(client, user, two_schools):
    alpha, beta = two_schools
    Membership.objects.create(user=user, school=alpha, role=Role.TEACHER)
    other = User.objects.create_user("other", password="S3cure-pass!")
    Membership.objects.create(user=other, school=beta, role=Role.TEACHER)
    client.force_login(user)
    response = client.get(reverse("schools:choose"))
    assert b"Alpha School" in response.content
    assert b"Beta School" not in response.content

@pytest.mark.django_db
def test_choosing_own_membership_sets_session(client, user, two_schools):
    alpha, beta = two_schools
    Membership.objects.create(user=user, school=alpha, role=Role.TEACHER)
    chosen = Membership.objects.create(user=user, school=beta, role=Role.PARENT)
    client.force_login(user)
    response = client.post(reverse("schools:choose"), {"membership_id": chosen.pk})
    assert response.status_code == 302
    assert client.session[SESSION_KEY] == chosen.pk

@pytest.mark.django_db
def test_cannot_choose_another_users_membership(client, user, two_schools):
    alpha, beta = two_schools
    Membership.objects.create(user=user, school=alpha, role=Role.TEACHER)
    Membership.objects.create(user=user, school=alpha, role=Role.PARENT)
    other = User.objects.create_user("other", password="S3cure-pass!")
    foreign = Membership.objects.create(user=other, school=beta, role=Role.ADMIN)
    client.force_login(user)
    response = client.post(reverse("schools:choose"), {"membership_id": foreign.pk})
    assert response.status_code == 200
    assert SESSION_KEY not in client.session

@pytest.mark.django_db
def test_non_numeric_membership_id_does_not_crash(client, user, two_schools):
    alpha, beta = two_schools
    Membership.objects.create(user=user, school=alpha, role=Role.TEACHER)
    Membership.objects.create(user=user, school=beta, role=Role.PARENT)
    client.force_login(user)
    response = client.post(reverse("schools:choose"), {"membership_id": "abc"})
    assert response.status_code == 200