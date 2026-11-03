from datetime import time

import pytest
from django.core.exceptions import ValidationError

from apps.classes.models import Level, Section, SchoolClass
from apps.subjects.models import Subject
from apps.timetable.models import TimetableSlot

MONDAY, FRIDAY = 1, 5


def make_class(school, name="Primary 4", order=None, **kw):
    level, _ = Level.objects.get_or_create(school=school, name="Primary", defaults={"order": 1})
    if order is None:
        order = level.classes.count() + 1
    return SchoolClass.objects.create(school=school, level=level, name=name, order=order, **kw)


def make_subject(school, name="Mathematics", **kw):
    return Subject.objects.create(school=school, name=name, **kw)


@pytest.fixture
def maths(school_a):
    return make_subject(school_a)


def slot(school, session, klass, **kw):
    defaults = {"day": MONDAY, "starts_at": time(8, 0), "ends_at": time(8, 40)}
    defaults.update(kw)
    return TimetableSlot.objects.create(school=school, session=session, school_class=klass, **defaults)


@pytest.mark.django_db
def test_lesson_slot_saves_with_subject(school_a, make_session):
    klass = make_class(school_a)
    s = slot(school_a, make_session(school_a), klass, subject=make_subject(school_a, "Mathematics"))
    assert s.title == "Mathematics"


@pytest.mark.django_db
def test_break_needs_a_label_and_a_lesson_cannot_have_one(school_a, make_session, maths):
    klass = make_class(school_a)
    session = make_session(school_a)
    with pytest.raises(ValidationError, match="label"):
        slot(school_a, session, klass)
    assert slot(school_a, session, klass, label="Long break").title == "Long break"
    with pytest.raises(ValidationError, match="no extra label"):
        slot(school_a, session, klass, subject=maths, label="Pop quiz")


@pytest.mark.django_db
def test_end_time_must_be_after_start(school_a, make_session, maths):
    klass = make_class(school_a)
    with pytest.raises(ValidationError, match="after the start"):
        slot(school_a, make_session(school_a), klass, subject=maths,
             starts_at=time(9, 0), ends_at=time(8, 0))


@pytest.mark.django_db
def test_a_second_slot_at_occupied_times_is_refused(school_a, make_session, maths):
    klass = make_class(school_a)
    session = make_session(school_a)
    slot(school_a, session, klass, subject=maths)
    with pytest.raises(ValidationError, match="already runs"):
        slot(school_a, session, klass, subject=make_subject(school_a, "English"))


@pytest.mark.django_db
def test_overlapping_period_is_refused_for_the_class(school_a, make_session, maths):
    klass = make_class(school_a)
    session = make_session(school_a)
    slot(school_a, session, klass, subject=maths, starts_at=time(8, 0), ends_at=time(8, 40))
    with pytest.raises(ValidationError, match="already runs"):
        slot(school_a, session, klass, subject=make_subject(school_a, "English"),
             starts_at=time(8, 30), ends_at=time(9, 10))


@pytest.mark.django_db
def test_the_same_times_are_fine_in_another_school_or_day_or_session(
    school_a, school_b, make_session, maths
):
    klass = make_class(school_a)
    session_a, session_b = make_session(school_a), make_session(school_b)
    hours = dict(starts_at=time(8, 0), ends_at=time(8, 40))
    slot(school_a, session_a, klass, subject=maths, **hours)
    other = make_class(school_b, "Nursery 1")
    slot(school_b, session_b, other, subject=make_subject(school_b, "Numbers"), **hours)  # other school
    slot(school_a, session_a, klass, subject=maths, day=FRIDAY, **hours)  # other day


@pytest.mark.django_db
def test_inactive_slots_do_not_block_new_ones(school_a, make_session, maths):
    klass = make_class(school_a)
    session = make_session(school_a)
    hour = dict(starts_at=time(8, 0), ends_at=time(8, 40))
    slot(school_a, session, klass, subject=maths, is_active=False, **hour)
    new = slot(school_a, session, klass, subject=make_subject(school_a, "English"), **hour)
    assert new.ends_at == hour["ends_at"]


@pytest.mark.django_db
def test_foreign_records_are_refused_field_by_field(school_a, school_b, make_session, maths):
    klass = make_class(school_a)
    session_a, session_b = make_session(school_a), make_session(school_b)
    foreign_class = make_class(school_b, "Beta Primary 1")
    foreign_subject = make_subject(school_b, "Beta Maths")
    for kw in (
        {"session": session_b},
        {"school_class": foreign_class},
        {"subject": foreign_subject},
    ):
        fixed = dict(session=session_a, school_class=klass, subject=maths)
        fixed.update(kw)
        with pytest.raises(ValidationError, match="different school"):
            TimetableSlot.objects.create(school=school_a, **fixed,
                                         day=MONDAY, starts_at=time(10, 0), ends_at=time(10, 40))


@pytest.mark.django_db
def test_tenant_isolation_by_id(school_a, school_b, make_session, maths):
    """School B cannot read school A's slot by id and its slots never leak."""
    klass = make_class(school_a)
    session = make_session(school_a)
    s = slot(school_a, session, klass, subject=maths)
    assert TimetableSlot.objects.for_school(school_b).count() == 0
    foreign = slot(school_b, make_session(school_b), make_class(school_b, "B/1"),
                   subject=make_subject(school_b, "B Maths"))
    assert TimetableSlot.objects.for_school(school_b).first() == foreign
    assert TimetableSlot.objects.for_school(school_a).first() == s


@pytest.mark.django_db
def test_section_must_belong_to_the_class(school_a, make_session, maths):
    klass = make_class(school_a)
    other = make_class(school_a, "Primary 5", order=5)
    stranger = Section.objects.create(school=school_a, school_class=other, name="A")
    with pytest.raises(ValidationError, match="does not belong"):
        slot(school_a, make_session(school_a), klass, subject=maths, section=stranger)


@pytest.mark.django_db
def test_sections_may_differ_but_must_respect_the_class_wide_grid(school_a, make_session, maths):
    klass = make_class(school_a)
    session = make_session(school_a)
    a = Section.objects.create(school=school_a, school_class=klass, name="A")
    b = Section.objects.create(school=school_a, school_class=klass, name="B")
    hour = dict(starts_at=time(8, 0), ends_at=time(8, 40))

    # Different sections may take different subjects at the same time.
    slot(school_a, session, klass, subject=maths, section=a, **hour)
    slot(school_a, session, klass, subject=make_subject(school_a, "Agric"), section=b, **hour)

    # But a class-wide slot cannot overlap a section slot.
    with pytest.raises(ValidationError, match="already runs"):
        slot(school_a, session, klass, subject=make_subject(school_a, "English"), **hour)

    # And a class-wide slot blocks a new section slot at the same time.
    blocking = slot(school_a, session, klass, subject=maths, day=FRIDAY, **hour)
    replacing = TimetableSlot(
        school=school_a, session=session, school_class=klass, day=FRIDAY,
        **hour, subject=blocking.subject,
    )
    replacing.section_id = a.id
    with pytest.raises(ValidationError, match="already runs"):
        replacing.save()
