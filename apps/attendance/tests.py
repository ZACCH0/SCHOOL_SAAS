import pytest
from datetime import date
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academics.models import AcademicSession
from apps.classes.models import Level, SchoolClass, Section
from apps.schools.models import Membership
from apps.students.models import Student

from .models import AttendanceRecord, AttendanceSession

Role = Membership.Role


def make_class(school, name="Primary 3", order=3):
    level, _ = Level.objects.get_or_create(
        school=school, name="Primary", defaults={"order": 1}
    )
    return SchoolClass.objects.create(school=school, level=level, name=name, order=order)


def make_section(school_class, name="A"):
    return Section.objects.create(school=school_class.school, school_class=school_class, name=name)


def make_register(school, school_class, day=date(2026, 10, 26), session=None, **kwargs):
    if session is None:
        session = AcademicSession.objects.get_or_create(
            school=school, name="2026/2027",
            defaults={"start_date": date(2026, 9, 1), "end_date": date(2027, 7, 31)},
        )[0]
    return AttendanceSession(
        school=school, school_class=school_class, date=day, session=session, **kwargs
    )


@pytest.mark.django_db
def test_two_registers_cannot_mark_one_class_twice_same_day(school_a):
    school_class = make_class(school_a)
    make_register(school_a, school_class).save()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_register(school_a, school_class).save()


@pytest.mark.django_db
def test_same_day_is_fine_for_different_sections(school_a):
    school_class = make_class(school_a)
    a, b = make_section(school_class, "A"), make_section(school_class, "B")
    make_register(school_a, school_class, section=a).save()
    make_register(school_a, school_class, section=b).save()
    assert AttendanceSession.objects.count() == 2


@pytest.mark.django_db
def test_two_schools_may_mark_the_same_day_independently(school_a, school_b):
    make_register(school_a, make_class(school_a)).save()
    make_register(school_b, make_class(school_b, "Beta Class", 1)).save()
    assert AttendanceSession.objects.for_school(school_a).count() == 1
    assert AttendanceSession.objects.for_school(school_b).count() == 1


@pytest.mark.django_db
def test_one_line_per_student_per_register(school_a, make_member):
    school_class = make_class(school_a)
    register = make_register(school_a, school_class)
    register.save()
    student = Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=school_class,
    )
    AttendanceRecord.objects.create(
        school=school_a, register=register, student=student, status=AttendanceRecord.Status.PRESENT
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        AttendanceRecord.objects.create(
            school=school_a, register=register, student=student, status=AttendanceRecord.Status.LATE
        )


@pytest.mark.django_db
def test_a_student_of_another_school_cannot_join_the_register(school_a, school_b):
    foreign_student = Student.objects.create(
        school=school_b, first_name="Neto", last_name="Stranger", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="BJ/2026/001",
    )
    register = make_register(school_a, make_class(school_a))
    register.save()
    line = AttendanceRecord(
        school=school_a, register=register, student=foreign_student,
        status=AttendanceRecord.Status.PRESENT,
    )
    with pytest.raises(ValidationError):
        line.save()


@pytest.mark.django_db
def test_register_date_must_be_inside_the_session(school_a):
    session = AcademicSession.objects.create(
        school=school_a, name="2026/2027",
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    register = make_register(school_a, make_class(school_a), day=date(2028, 1, 1), session=session)
    with pytest.raises(ValidationError):
        register.save()


@pytest.mark.django_db
def test_register_date_must_be_inside_the_term(school_a, make_member):
    session = AcademicSession.objects.create(
        school=school_a, name="2026/2027",
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    period = session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )
    register = make_register(
        school_a, make_class(school_a), day=date(2027, 2, 1), session=session, period=period
    )
    with pytest.raises(ValidationError):
        register.save()


@pytest.mark.django_db
def test_section_must_belong_to_the_class(school_a):
    school_class = make_class(school_a)
    other = make_class(school_a, "Primary 4", order=4)
    register = make_register(school_a, school_class, section=make_section(other))
    with pytest.raises(ValidationError):
        register.save()


@pytest.mark.django_db
def test_every_status_is_accepted(school_a):
    school_class = make_class(school_a)
    register = make_register(school_a, school_class)
    register.save()
    student = Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=school_class,
    )
    for status in AttendanceRecord.Status.values:
        line = AttendanceRecord(
            school=school_a, register=register, student=student, status=status
        )
        line.clean()
