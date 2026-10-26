from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.academics.models import AcademicSession
from apps.schools.models import Membership, School


@pytest.fixture
def school_a():
    return School.objects.create(name="Alpha School", slug="alpha")


@pytest.fixture
def school_b():
    return School.objects.create(name="Beta School", slug="beta")


@pytest.fixture
def make_member():
    def make(school, role=Membership.Role.TEACHER):
        username = f"{role}-{school.slug}-{Membership.objects.count()}"
        user = get_user_model().objects.create_user(username, password="S3cure-pass!")
        return Membership.objects.create(user=user, school=school, role=role)

    return make


@pytest.fixture
def make_session():
    def make(school, name="2026/2027", current=False):
        return AcademicSession.objects.create(
            school=school, name=name, start_date=date(2026, 9, 1),
            end_date=date(2027, 7, 31), is_current=current,
        )

    return make


@pytest.fixture
def make_request(make_member):
    def make(school, role=Membership.Role.ADMIN):
        member = make_member(school, role)
        request = RequestFactory().get("/")
        request.user = member.user
        request.membership = member
        request.school = school
        return request

    return make


@pytest.fixture
def login_as(client, make_member):
    """Log the test client in as a new member of the school and return the membership."""

    def login(school, role=Membership.Role.ADMIN):
        member = make_member(school, role)
        client.force_login(member.user)
        return member

    return login
