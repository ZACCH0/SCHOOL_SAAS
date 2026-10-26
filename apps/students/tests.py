import pytest
from datetime import date
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academics.models import AcademicSession
from apps.classes.models import Level, SchoolClass, Section
from apps.schools.models import Membership
from .models import GuardianLink, Student, StudentClassHistory

Role = Membership.Role


def make_class(school, name="Primary 3", order=3):
    level, _ = Level.objects.get_or_create(
        school=school, name="Primary", defaults={"order": 1}
    )
    return SchoolClass.objects.create(school=school, level=level, name=name, order=order)


def make_section(school_class, name="A"):
    return Section.objects.create(
        school=school_class.school, school_class=school_class, name=name
    )


def make_student(school, admission_number, school_class=None, section=None, **kwargs):
    defaults = dict(
        school=school,
        first_name="Ade",
        last_name="Ogunlesi",
        sex="male",
        date_of_birth=date(2018, 3, 5),
        admission_number=admission_number,
        current_class=school_class,
        current_section=section,
    )
    defaults.update(kwargs)
    return Student.objects.create(**defaults)


@pytest.mark.django_db
def test_admission_numbers_unique_within_school_school_a(school_a):
    make_student(school_a, "FSS/2025/001")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_student(school_a, "fss/2025/001")


@pytest.mark.django_db
def test_two_schools_may_use_the_same_admission_number(school_a, school_b):
    make_student(school_a, "FSS/2025/001")
    make_student(school_b, "FSS/2025/001")
    assert Student.objects.count() == 2


@pytest.mark.django_db
def test_student_section_must_belong_to_current_class(school_a):
    school_class = make_class(school_a)
    other_class = make_class(school_a, "Primary 4", order=4)
    section = make_section(other_class)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class)
    student.current_section = section
    with pytest.raises(ValidationError):
        student.save()


@pytest.mark.django_db
def test_student_cannot_point_to_another_schools_class(school_a, school_b):
    other_class = make_class(school_b)
    student = make_student(school_a, "FSS/2025/001")
    student.current_class = other_class
    with pytest.raises(ValidationError):
        student.save()


@pytest.mark.django_db
def test_teacher_cannot_be_a_guardian(school_a, make_member):
    school_class = make_class(school_a)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class)
    teacher = make_member(school_a, role=Role.TEACHER)
    link = GuardianLink(school=school_a, student=student, guardian=teacher)
    with pytest.raises(ValidationError):
        link.save()


@pytest.mark.django_db
def test_guardian_link_accepts_parent_membership(school_a, make_member):
    school_class = make_class(school_a)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class)
    parent = make_member(school_a, role=Role.PARENT)
    link = GuardianLink.objects.create(
        school=school_a, student=student, guardian=parent
    )
    assert link.school == school_a
    assert student.guardian_links.count() == 1


@pytest.mark.django_db
def test_same_guardian_cannot_be_linked_twice(school_a, make_member):
    school_class = make_class(school_a)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class)
    parent = make_member(school_a, role=Role.PARENT)
    GuardianLink.objects.create(school=school_a, student=student, guardian=parent)
    with pytest.raises(IntegrityError), transaction.atomic():
        GuardianLink.objects.create(school=school_a, student=student, guardian=parent)


@pytest.mark.django_db
def test_guardian_from_another_school_is_refused(
    school_a, school_b, make_member
):
    school_class = make_class(school_a)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class)
    parent_b = make_member(school_b, role=Role.PARENT)
    link = GuardianLink(
        school=school_a, student=student, guardian=parent_b
    )
    with pytest.raises(ValidationError):
        link.save()


@pytest.mark.django_db
def test_class_history_one_row_per_session(school_a, make_session):
    school_class = make_class(school_a)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class)
    session = make_session(school_a)
    StudentClassHistory.objects.create(
        school=school_a, student=student, session=session, school_class=school_class
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        StudentClassHistory.objects.create(
            school=school_a, student=student, session=session, school_class=school_class
        )


@pytest.mark.django_db
def test_class_history_cannot_mix_two_schools(
    school_a, school_b, make_session
):
    school_class_a = make_class(school_a)
    school_class_b = make_class(school_b, "Primary 5", order=5)
    student = make_student(school_a, "FSS/2025/001", school_class=school_class_a)
    session = make_session(school_a)
    history = StudentClassHistory(
        school=school_a,
        student=student,
        session=session,
        school_class=school_class_b,
    )
    with pytest.raises(ValidationError):
        history.save()


@pytest.mark.django_db
def test_school_a_cannot_see_school_b_students(school_a, school_b, make_session):
    make_student(school_a, "FSS/2025/001")
    make_student(school_b, "BET/2025/001")
    assert Student.objects.for_school(school_a).count() == 1
    assert Student.objects.for_school(school_b).count() == 1
