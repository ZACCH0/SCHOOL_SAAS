from datetime import date

import pytest
from django.db import IntegrityError, transaction
from django.db.models.functions import Lower

from apps.classes.models import Level, SchoolClass, Section
from apps.students.models import Student

from .models import Applicant

pytestmark = pytest.mark.django_db


def make_class(school, name="Primary 1", order=1):
    level = Level.objects.create(school=school, name=name.split()[0], order=order)
    return SchoolClass.objects.create(school=school, level=level, name=name, order=order)


def make_student(school, number="FSS/2026/101"):
    return Student.objects.create(
        school=school,
        first_name="Ada",
        last_name="Obi",
        sex="female",
        date_of_birth=date(2018, 3, 5),
        admission_number=number,
    )


@pytest.fixture
def class_a(school_a):
    return make_class(school_a)


def test_new_applicant_starts_applied(school_a):
    applicant = Applicant.objects.create(
        school=school_a,
        reference="APP-0001",
        first_name="Bola",
        last_name="Ade",
        sex="male",
    )
    assert applicant.status == Applicant.Status.APPLIED
    assert applicant.converted_student is None
    assert str(applicant) == "Ade Bola (APP-0001)"


def test_reference_is_case_insensitive_unique_per_school(school_a, school_b):
    Applicant.objects.create(
        school=school_a,
        reference="APP-0001",
        first_name="Bola",
        last_name="Ade",
        sex="male",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Applicant.objects.create(
                school=school_a,
                reference="app-0001",
                first_name="Bola",
                last_name="Ade",
                sex="male",
            )
    Applicant.objects.create(
        school=school_b,
        reference="APP-0001",
        first_name="Chike",
        last_name="Oke",
        sex="male",
    )


def test_school_a_cannot_read_school_b_applicant_by_id(school_a, school_b):
    applicant = Applicant.objects.create(
        school=school_a,
        reference="APP-0002",
        first_name="Bola",
        last_name="Ade",
        sex="male",
    )
    assert applicant not in Applicant.objects.for_school(school_b)

    with pytest.raises(Applicant.DoesNotExist):
        Applicant.objects.for_school(school_b).get(pk=applicant.pk)


def test_target_class_from_another_school_is_rejected(school_a, school_b, class_a):
    with pytest.raises(Exception, match="school"):
        Applicant.objects.create(
            school=school_b,
            reference="APP-0003",
            first_name="Chike",
            last_name="Oke",
            sex="male",
            target_class=class_a,
        )


def test_converted_student_from_another_school_is_rejected(school_a, school_b):
    foreign = make_student(school_b)
    with pytest.raises(Exception, match="school"):
        Applicant.objects.create(
            school=school_a,
            reference="APP-0004",
            first_name="Bola",
            last_name="Ade",
            sex="male",
            status=Applicant.Status.CONVERTED,
            converted_student=foreign,
        )


def test_converted_applicant_needs_a_student(school_a, class_a):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Applicant.objects.create(
                school=school_a,
                reference="APP-0005",
                first_name="Bola",
                last_name="Ade",
                sex="male",
                status=Applicant.Status.CONVERTED,
            )


def test_converted_applicant_keeps_its_student(school_a, class_a):
    student = make_student(school_a)
    applicant = Applicant.objects.create(
        school=school_a,
        reference="APP-0006",
        first_name="Bola",
        last_name="Ade",
        sex="male",
        status=Applicant.Status.CONVERTED,
        converted_student=student,
    )
    refreshed = Applicant.objects.for_school(school_a).get(pk=applicant.pk)
    assert refreshed.converted_student == student
