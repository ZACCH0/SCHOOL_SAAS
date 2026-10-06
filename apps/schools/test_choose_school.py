import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.schools.models import Membership, School

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user("teacher1", password="S3cure-pass!")

@pytest.fixture
def school():
    return School.objects.create(name="Alpha School", slug="alpha")

@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"School Management Platform" in response.content

@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))

@pytest.mark.django_db
def test_user_without_membership_is_denied(client, user):
    client.force_login(user)
    assert client.get(reverse("core:dashboard")).status_code == 403

@pytest.mark.django_db
def test_user_with_one_membership_sees_dashboard(client, user, school):
    Membership.objects.create(user=user, school=school, role=Membership.Role.TEACHER)
    client.force_login(user)
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 200
    assert b"Alpha School" in response.content
    assert b"Teacher" in response.content

@pytest.mark.django_db
def test_user_with_several_memberships_is_sent_to_chooser(client, user, school):
    other = School.objects.create(name="Beta School", slug="beta")
    Membership.objects.create(user=user, school=school, role=Membership.Role.TEACHER)
    Membership.objects.create(user=user, school=other, role=Membership.Role.PARENT)
    client.force_login(user)
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("schools:choose")

@pytest.mark.django_db
def test_superuser_without_membership_goes_to_admin(client):
    root = User.objects.create_superuser("root", password="S3cure-pass!")
    client.force_login(root)
    response = client.get(reverse("core:dashboard"))
    assert response.status_code == 302
    assert response.url == reverse("admin:index")