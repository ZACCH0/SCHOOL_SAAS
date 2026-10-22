from datetime import date
import pytest
from django.contrib.auth import get_user_model
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
    def make(school, name="2026/2027"):
        return AcademicSession.objects.create(
            school=school, name=name, start_date=date(2026, 9, 1), end_date=date(2027, 7, 31)
        )

    return make