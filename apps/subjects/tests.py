import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from apps.classes.models import Level, SchoolClass, Section
from apps.schools.models import Membership
from .models import ClassSubject, Subject, TeacherAssignment

Role = Membership.Role

def make_class(school, name="Primary 4", order=4):
    level, _ = Level.objects.get_or_create(school=school, name="Primary", defaults={"order": 1})
    return SchoolClass.objects.create(school=school, level=level, name=name, order=order)

def make_subject(school, name="Mathematics"):
    return Subject.objects.create(school=school, name=name)

def setup_class_with_subject(school):
    school_class, subject = make_class(school), make_subject(school)
    ClassSubject.objects.create(school=school, school_class=school_class, subject=subject)
    return school_class, subject

def assign(school, school_class, subject, teacher, session, section=None):
    return TeacherAssignment.objects.create(
        school=school, school_class=school_class, subject=subject,
        teacher=teacher, session=session, section=section,
    )

@pytest.mark.django_db
def test_subject_names_unique_ignoring_case_per_school(school_a, school_b):
    make_subject(school_a, "Mathematics")
    make_subject(school_b, "Mathematics")  # another school may use the same name
    with pytest.raises(IntegrityError), transaction.atomic():
        make_subject(school_a, "mathematics")

@pytest.mark.django_db
def test_a_class_takes_a_subject_only_once(school_a):
    school_class, subject = setup_class_with_subject(school_a)
    with pytest.raises(IntegrityError), transaction.atomic():
        ClassSubject.objects.create(school=school_a, school_class=school_class, subject=subject)

@pytest.mark.django_db
def test_class_subject_cannot_mix_schools(school_a, school_b):
    with pytest.raises(ValidationError):
        ClassSubject.objects.create(
            school=school_a, school_class=make_class(school_a), subject=make_subject(school_b)
        )

@pytest.mark.django_db
def test_assignment_needs_the_class_to_take_the_subject(school_a, make_member, make_session):
    school_class, other_subject = make_class(school_a), make_subject(school_a, "Biology")
    with pytest.raises(ValidationError):
        assign(school_a, school_class, other_subject, make_member(school_a), make_session(school_a))

@pytest.mark.django_db
def test_valid_assignment_is_saved(school_a, make_member, make_session):
    school_class, subject = setup_class_with_subject(school_a)
    teacher, session = make_member(school_a), make_session(school_a)
    assignment = assign(school_a, school_class, subject, teacher, session)
    assert assignment.pk is not None

@pytest.mark.django_db
def test_only_teachers_can_be_assigned(school_a, make_member, make_session):
    school_class, subject = setup_class_with_subject(school_a)
    with pytest.raises(ValidationError):
        assign(school_a, school_class, subject, make_member(school_a, Role.PARENT),
               make_session(school_a))

@pytest.mark.django_db
def test_one_teacher_per_class_subject_per_session(school_a, make_member, make_session):
    school_class, subject = setup_class_with_subject(school_a)
    session = make_session(school_a)
    assign(school_a, school_class, subject, make_member(school_a), session)
    with pytest.raises(IntegrityError), transaction.atomic():
        assign(school_a, school_class, subject, make_member(school_a), session)

@pytest.mark.django_db
def test_next_session_can_have_a_different_teacher(school_a, make_member, make_session):
    school_class, subject = setup_class_with_subject(school_a)
    assign(school_a, school_class, subject, make_member(school_a), make_session(school_a))
    second = assign(
        school_a, school_class, subject, make_member(school_a),
        make_session(school_a, "2027/2028"),
    )
    assert second.pk is not None


@pytest.mark.django_db
def test_assignment_section_must_belong_to_the_class(school_a, make_member, make_session):
    school_class, subject = setup_class_with_subject(school_a)
    other_class = make_class(school_a, "Primary 6", 6)
    section = Section.objects.create(school=school_a, school_class=other_class, name="A")
    with pytest.raises(ValidationError):
        assign(school_a, school_class, subject, make_member(school_a), make_session(school_a),
               section=section)


@pytest.mark.django_db
def test_assignments_are_isolated_between_schools(
    school_a, school_b, make_member, make_session
):
    class_a, subject_a = setup_class_with_subject(school_a)
    mine = assign(school_a, class_a, subject_a, make_member(school_a), make_session(school_a))
    class_b, subject_b = setup_class_with_subject(school_b)
    assign(school_b, class_b, subject_b, make_member(school_b), make_session(school_b))
    assert list(TeacherAssignment.objects.for_school(school_a)) == [mine]