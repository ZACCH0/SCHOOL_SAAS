import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from apps.schools.models import Membership
from .models import ClassTeacher, Level, SchoolClass, Section
from .services import seed_standard_structure

Role = Membership.Role

def make_level(school, name="Primary", order=1):
    return Level.objects.create(school=school, name=name, order=order)

def make_class(school, name="Primary 4", order=4, level=None):
    return SchoolClass.objects.create(
        school=school, level=level or make_level(school), name=name, order=order
    )

@pytest.mark.django_db
def test_level_names_are_unique_ignoring_case(school_a):
    make_level(school_a, "Primary", 1)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_level(school_a, "primary", 2)

@pytest.mark.django_db
def test_class_order_is_unique_per_school_only(school_a, school_b):
    level_a = make_level(school_a)
    make_class(school_a, "Primary 1", 1, level_a)
    make_class(school_b, "Primary 1", 1)  # another school may reuse it
    with pytest.raises(IntegrityError), transaction.atomic():
        make_class(school_a, "Primary 2", 1, level_a)

@pytest.mark.django_db
def test_class_names_unique_ignoring_case_but_not_across_schools(school_a, school_b):
    level_a = make_level(school_a)
    make_class(school_a, "Primary 4", 4, level_a)
    make_class(school_b, "Primary 4", 4)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_class(school_a, "primary 4", 5, level_a)

@pytest.mark.django_db
def test_class_level_must_belong_to_the_same_school(school_a, school_b):
    foreign_level = make_level(school_b)
    with pytest.raises(ValidationError):
        SchoolClass.objects.create(school=school_a, level=foreign_level, name="X", order=1)

@pytest.mark.django_db
def test_classes_are_isolated_between_schools(school_a, school_b):
    mine = make_class(school_a)
    make_class(school_b)
    assert list(SchoolClass.objects.for_school(school_a)) == [mine]
    with pytest.raises(SchoolClass.DoesNotExist):
        SchoolClass.objects.for_school(school_b).get(pk=mine.pk)

@pytest.mark.django_db
def test_section_names_are_unique_within_a_class(school_a):
    primary_six = make_class(school_a, "Primary 6", 6)
    Section.objects.create(school=school_a, school_class=primary_six, name="A")
    with pytest.raises(IntegrityError), transaction.atomic():
        Section.objects.create(school=school_a, school_class=primary_six, name="a")

@pytest.mark.django_db
def test_section_class_must_belong_to_the_same_school(school_a, school_b):
    foreign_class = make_class(school_b)
    with pytest.raises(ValidationError):
        Section.objects.create(school=school_a, school_class=foreign_class, name="A")

@pytest.mark.django_db
def test_class_with_sections_cannot_be_deleted(school_a):
    primary_six = make_class(school_a, "Primary 6", 6)
    Section.objects.create(school=school_a, school_class=primary_six, name="A")
    with pytest.raises(ProtectedError):
        primary_six.delete()

@pytest.mark.django_db
def test_class_teacher_must_have_the_teacher_role(school_a, make_member, make_session):
    bursar = make_member(school_a, Role.BURSAR)
    with pytest.raises(ValidationError):
        ClassTeacher.objects.create(
            school=school_a, school_class=make_class(school_a),
            session=make_session(school_a), teacher=bursar,
        )

@pytest.mark.django_db
def test_class_teacher_must_belong_to_the_same_school(
    school_a, school_b, make_member, make_session
):
    foreign_teacher = make_member(school_b)
    with pytest.raises(ValidationError):
        ClassTeacher.objects.create(
            school=school_a, school_class=make_class(school_a),
            session=make_session(school_a), teacher=foreign_teacher,
        )

@pytest.mark.django_db
def test_one_class_teacher_per_class_per_session(school_a, make_member, make_session):
    session = make_session(school_a)
    primary_four = make_class(school_a)
    ClassTeacher.objects.create(
        school=school_a, school_class=primary_four, session=session,
        teacher=make_member(school_a),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ClassTeacher.objects.create(
            school=school_a, school_class=primary_four, session=session,
            teacher=make_member(school_a),
        )

@pytest.mark.django_db
def test_class_teacher_section_must_belong_to_the_class(school_a, make_member, make_session):
    level = make_level(school_a)
    primary_four = make_class(school_a, "Primary 4", 4, level)
    primary_six = make_class(school_a, "Primary 6", 6, level)
    section = Section.objects.create(school=school_a, school_class=primary_six, name="A")
    with pytest.raises(ValidationError):
        ClassTeacher.objects.create(
            school=school_a, school_class=primary_four, section=section,
            session=make_session(school_a), teacher=make_member(school_a),
        )


@pytest.mark.django_db
def test_seed_creates_the_standard_structure(school_a):
    assert seed_standard_structure(school_a) is True
    assert Level.objects.for_school(school_a).count() == 3
    assert SchoolClass.objects.for_school(school_a).count() == 12
    active_levels = Level.objects.for_school(school_a).filter(is_active=True)
    assert [level.name for level in active_levels] == ["Primary"]
    assert SchoolClass.objects.for_school(school_a).filter(is_active=True).count() == 6

@pytest.mark.django_db
def test_seed_skips_schools_that_already_have_classes(school_a, school_b):
    make_class(school_a)
    assert seed_standard_structure(school_a) is False
    assert SchoolClass.objects.for_school(school_a).count() == 1
    assert seed_standard_structure(school_b) is True
    assert SchoolClass.objects.for_school(school_b).count() == 12