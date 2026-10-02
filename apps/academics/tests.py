from datetime import date
import pytest
from django.db import IntegrityError, transaction
from apps.schools.models import School
from .models import AcademicSession
# Create your tests here.
@pytest.fixture
def school_a():
    return School.objects.create(name="Alpha School", slug="alpha")

@pytest.fixture
def school_b():
    return School.objects.create(name="Beta School", slug="beta")

def make_session(school, name="2026/2027", current=False, start=date(2026, 9, 1), end=date(2027, 7, 31)):
    return AcademicSession.objects.create(
        school=school, name=name, start_date=start, end_date=end, is_current=current
    )

@pytest.mark.django_db
def test_for_school_returns_only_that_schools_sessions(school_a, school_b):
    a = make_session(school_a)
    make_session(school_b)
    assert list(AcademicSession.objects.for_school(school_a)) == [a]

@pytest.mark.django_db
def test_other_school_cannot_fetch_session_by_id(school_a, school_b):
    session_a = make_session(school_a)
    with pytest.raises(AcademicSession.DoesNotExist):
        AcademicSession.objects.for_school(school_b).get(pk=session_a.pk)

@pytest.mark.django_db
def test_same_session_name_allowed_in_different_schools(school_a, school_b):
    make_session(school_a)
    make_session(school_b)
    assert AcademicSession.objects.count() == 2

@pytest.mark.django_db
def test_duplicate_session_name_in_same_school_rejected(school_a):
    make_session(school_a)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_session(school_a)

@pytest.mark.django_db
def test_only_one_current_session_per_school(school_a, school_b):
    make_session(school_a, "2026/2027", current=True)
    make_session(school_b, "2026/2027", current=True)  # other school is fine
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_session(school_a, "2027/2028", current=True,
                         start=date(2027, 9, 1), end=date(2028, 7, 31))

@pytest.mark.django_db
def test_end_date_must_be_after_start_date(school_a):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_session(school_a, start=date(2027, 7, 31), end=date(2026, 9, 1))