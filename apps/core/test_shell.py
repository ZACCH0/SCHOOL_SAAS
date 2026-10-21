from datetime import date
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.academics.models import AcademicPeriod, AcademicSession
from apps.schools.models import Membership, School

User = get_user_model()
Role = Membership.Role


def make_current_period(school, name="First Term"):
    session = AcademicSession.objects.create(
        school=school, name="2026/2027",
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    return AcademicPeriod.objects.create(
        school=school, session=session, name=name, order=1,
        start_date=date(2026, 9, 1), end_date=date(2026, 12, 18), is_current=True,
    )

@pytest.fixture
def school():
    return School.objects.create(name="Alpha School", slug="alpha")

@pytest.fixture
def teacher(school):
    user = User.objects.create_user("teacher1", password="S3cure-pass!")
    Membership.objects.create(user=user, school=school, role=Role.TEACHER)
    return user

@pytest.mark.django_db
def test_anonymous_visitor_sees_no_sidebar(client):
    response = client.get("/")
    assert b'aria-label="Main"' not in response.content

@pytest.mark.django_db
def test_member_sees_sidebar_with_active_page(client, teacher):
    client.force_login(teacher)
    response = client.get(reverse("core:dashboard"))
    assert b'aria-label="Main"' in response.content
    assert b'aria-current="page"' in response.content

@pytest.mark.django_db
def test_current_period_is_shown_in_top_bar(client, teacher, school):
    make_current_period(school, "First Term")
    client.force_login(teacher)
    response = client.get(reverse("core:dashboard"))
    assert b"First Term" in response.content


@pytest.mark.django_db
def test_other_schools_period_is_never_shown(client, teacher):
    other = School.objects.create(name="Beta School", slug="beta")
    make_current_period(other, "Secret Beta Term")
    client.force_login(teacher)
    response = client.get(reverse("core:dashboard"))
    assert b"Secret Beta Term" not in response.content

@pytest.mark.django_db
def test_nav_items_respect_roles(client, teacher, school, monkeypatch):
    monkeypatch.setattr(
        "apps.core.navigation.NAV_ITEMS",
        [
            ("Dashboard", "core:dashboard", None),
            ("Money page", "core:home", [Role.BURSAR]),
        ],
    )
    client.force_login(teacher)
    assert b"Money page" not in client.get(reverse("core:dashboard")).content
    bursar = User.objects.create_user("bursar1", password="S3cure-pass!")
    Membership.objects.create(user=bursar, school=school, role=Role.BURSAR)
    client.force_login(bursar)
    assert b"Money page" in client.get(reverse("core:dashboard")).content