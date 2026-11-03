from datetime import time

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.classes.models import Section
from apps.timetable.models import TimetableSlot
from apps.timetable.services import copy_slot_to_session, create_slot, set_slot_active

from .tests import make_class, make_subject, slot  # reuse the model helpers


def actions():
    return list(AuditLog.objects.order_by("id").values_list("action", flat=True))


MONDAY, TUESDAY, FRIDAY, SUNDAY = 1, 2, 5, 7
NINE_TO = dict(starts_at=time(9, 0), ends_at=time(9, 40))


@pytest.fixture
def maths(school_a):
    return make_subject(school_a, "Mathematics")


@pytest.fixture
def full(school_a, make_session, maths):
    session = make_session(school_a, "2026/2027", current=True)
    klass = make_class(school_a)
    return session, klass, maths


@pytest.mark.django_db
def test_owner_places_a_period_and_it_is_audited(school_a, make_request, full):
    session, klass, maths = full
    slot_obj = create_slot(
        make_request(school_a, role="owner"), session=session, school_class=klass,
        subject=maths, day=MONDAY, **NINE_TO,
    )
    assert slot_obj.title == "Mathematics" and slot_obj.is_active
    assert actions() == ["timetable.slot_created"]


@pytest.mark.django_db
def test_teacher_or_bursar_cannot_build_the_timetable(school_a, make_request, full):
    session, klass, maths = full
    for role in ("teacher", "bursar", "parent"):
        with pytest.raises(PermissionDenied):
            create_slot(
                make_request(school_a, role=role), session=session, school_class=klass,
                subject=maths, day=MONDAY, **NINE_TO,
            )
    assert TimetableSlot.objects.count() == 0


@pytest.mark.django_db
def test_overlap_gives_a_friendly_message(school_a, make_request, full):
    session, klass, maths = full
    request = make_request(school_a)
    create_slot(request, session=session, school_class=klass, subject=maths, day=MONDAY, **NINE_TO)
    with pytest.raises(ValidationError, match="already runs"):
        create_slot(
            request, session=session, school_class=klass,
            subject=make_subject(school_a, "English"),
            day=MONDAY, starts_at=time(9, 30), ends_at=time(10, 10),
        )


@pytest.mark.django_db
def test_sections_may_differ_and_stray_sections_are_refused(school_a, make_request, full):
    session, klass, maths = full
    a = Section.objects.create(school=school_a, school_class=klass, name="A")
    b = Section.objects.create(school=school_a, school_class=klass, name="B")
    request = make_request(school_a)
    create_slot(request, session=session, school_class=klass,
                subject=maths, section=a, day=TUESDAY, **NINE_TO)
    create_slot(request, session=session, school_class=klass,
                subject=make_subject(school_a, "English"), section=b, day=TUESDAY, **NINE_TO)
    stray = Section.objects.create(
        school=school_a, school_class=make_class(school_a, "Primary 5", order=5), name="A",
    )
    with pytest.raises(ValidationError, match="does not belong"):
        create_slot(request, session=session, school_class=klass,
                    subject=maths, section=stray, day=MONDAY, **NINE_TO)


@pytest.mark.django_db
def test_break_needs_a_label_even_through_the_service(school_a, make_request, full):
    session, klass, maths = full
    with pytest.raises(ValidationError, match="label"):
        create_slot(make_request(school_a), session=session, school_class=klass,
                    label="", day=MONDAY, **NINE_TO)


@pytest.mark.django_db
def test_foreign_class_is_refused(school_a, school_b, make_request, make_session, maths):
    beta = make_class(school_b, "Beta Primary 7")
    session = make_session(school_a)
    with pytest.raises(ValidationError, match="your school"):
        create_slot(
            make_request(school_a), session=session, school_class=beta,
            subject=maths, day=MONDAY, **NINE_TO,
        )
    assert TimetableSlot.objects.count() == 0


@pytest.mark.django_db
def test_a_slot_from_another_school_cannot_be_archived(school_a, school_b, make_request, make_session):
    session = make_session(school_a)
    beta = make_class(school_b, "Beta Primary 2")
    foreign = slot(school_b, make_session(school_b), beta, label="Break", **NINE_TO)
    with pytest.raises(PermissionDenied):
        set_slot_active(make_request(school_a), foreign, False)
    foreign.refresh_from_db()
    assert foreign.is_active


@pytest.mark.django_db
def test_archiving_then_restoring_keeps_history(school_a, make_request, full):
    session, klass, maths = full
    request = make_request(school_a, role="owner")
    period = create_slot(request, session=session, school_class=klass,
                         subject=maths, day=FRIDAY, **NINE_TO)
    set_slot_active(request, period, False)
    period.refresh_from_db()
    assert not period.is_active
    assert TimetableSlot.objects.count() == 1  # archived, never deleted
    set_slot_active(request, period, True)
    assert actions() == ["timetable.slot_created", "timetable.slot_archived", "timetable.slot_restored"]
    assert len(actions()) == 3


@pytest.mark.django_db
def test_archived_slot_frees_its_time(school_a, make_request, full):
    session, klass, maths = full
    request = make_request(school_a)
    period = create_slot(request, session=session, school_class=klass,
                         subject=maths, day=SUNDAY, **NINE_TO)
    set_slot_active(request, period, False)
    new = create_slot(request, session=session, school_class=klass,
                      subject=make_subject(school_a, "English"), day=SUNDAY, **NINE_TO)
    assert new.starts_at == period.starts_at


@pytest.mark.django_db
def test_a_slot_copies_to_the_next_session(school_a, make_request, full, make_session):
    session, klass, maths = full
    request = make_request(school_a, role="owner")
    period = create_slot(request, session=session, school_class=klass,
                         subject=maths, day=MONDAY, **NINE_TO)
    next_session = make_session(school_a, "2027/2028")
    twin = copy_slot_to_session(request, period, session=next_session)
    assert twin.id != period.id and twin.session_id == next_session.id
    assert twin.subject_id == maths.id and twin.day == MONDAY


@pytest.mark.django_db
def test_copy_refuses_a_foreign_session(school_a, school_b, make_request, full, make_session):
    session, klass, maths = full
    request = make_request(school_a, role="owner")
    period = create_slot(request, session=session, school_class=klass,
                         subject=maths, day=MONDAY, **NINE_TO)
    beta_session = make_session(school_b)
    with pytest.raises(PermissionDenied):
        copy_slot_to_session(request, period, session=beta_session)
    assert actions().count("timetable.slot_created") == 1
