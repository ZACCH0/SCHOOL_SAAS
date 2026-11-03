import pytest
from datetime import time
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.schools.models import Membership
from apps.subjects.models import ClassSubject, TeacherAssignment
from apps.timetable.models import TimetableSlot

from .tests import make_class, make_subject, maths, slot

Role = Membership.Role
MONDAY = 1


def class_takes(klass, *subjects):
    for subject in subjects:
        ClassSubject.objects.create(school=klass.school, school_class=klass, subject=subject)


def assign(subject, klass, teacher, session, section=None):
    return TeacherAssignment.objects.create(
        school=klass.school, school_class=klass, subject=subject,
        teacher=teacher, session=session, section=section,
    )


def add_slot(cls, klass, subject=None, section=None, label="", times=None):
    data = {
        "subject": subject.pk if subject else "",
        "section": section.pk if section else "",
        "label": label,
        "day": MONDAY,
        "starts_at": "09:00" if times else "09:00",
        "ends_at": "09:40",
    }
    data.update(times or {})
    return cls.post(reverse("timetable:add", args=[klass.pk]), data)


@pytest.mark.django_db
def test_anonymous_is_sent_to_login(client, school_a, make_session):
    make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    for url in (
        reverse("timetable:home"),
        reverse("timetable:grid", args=[klass.pk]),
        reverse("timetable:add", args=[klass.pk]),
    ):
        response = client.get(url)
        assert response.status_code == 302 and "/accounts/login/" in response.url


@pytest.mark.django_db
def test_bursar_and_parent_are_refused(client, school_a, make_session, login_as):
    make_session(school_a, name="2026/2027", current=True)
    class_object = make_class(school_a)
    for role in (Role.BURSAR, Role.PARENT):
        login_as(school_a, role)
        home = client.get(reverse("timetable:home"))
        grid = client.get(reverse("timetable:grid", args=[class_object.pk]))
        add = client.get(reverse("timetable:add", args=[class_object.pk]))
        assert home.status_code == 403 and grid.status_code == 403
        assert add.status_code == 403


@pytest.mark.django_db
def test_owner_home_lists_classes_with_period_counts(
    client, school_a, make_session, login_as, make_member, maths
):
    session = make_session(school_a, name="2026/2027", current=True)
    primary_four = make_class(school_a)
    other = make_class(school_a, "Primary 5", order=5)
    class_takes(primary_four, maths)
    owner = login_as(school_a, Role.OWNER)
    assign(maths, primary_four, make_member(school_a), session)
    slot(school_a, session, primary_four, subject=maths)
    response = client.get(reverse("timetable:home"))
    assert response.status_code == 200
    content = response.content.decode()
    assert str(primary_four) in content and str(other) in content


@pytest.mark.django_db
def test_teacher_sees_only_the_classes_they_teach(client, school_a, make_session, login_as, maths):
    session = make_session(school_a, name="2026/2027", current=True)
    own = make_class(school_a)
    untaken = make_class(school_a, "Primary 5", order=5)
    class_takes(own, maths)
    teacher = login_as(school_a, Role.TEACHER)
    assign(maths, own, teacher, session)

    response = client.get(reverse("timetable:home"))
    content = response.content.decode()
    assert str(own) in content and str(untaken) not in content
    # But the taught class's grid opens; the untaken one is refused.
    assert client.get(reverse("timetable:grid", args=[own.pk])).status_code == 200
    assert client.get(reverse("timetable:grid", args=[untaken.pk])).status_code == 403


@pytest.mark.django_db
def test_teacher_reads_the_grid_but_cannot_build_it(client, school_a, make_session, login_as, maths):
    session = make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    class_takes(klass, maths)
    teacher = login_as(school_a, Role.TEACHER)
    assign(maths, klass, teacher, session)
    lesson = slot(school_a, session, klass, subject=maths)

    response = client.get(reverse("timetable:grid", args=[klass.pk]))
    content = response.content.decode()
    assert "Mathematics" in content
    assert "Take off" not in content  # read-only for teachers
    assert "Add a period" not in content

    response = client.post(reverse("timetable:archive", args=[lesson.pk]))
    assert response.status_code == 403
    lesson.refresh_from_db()
    assert lesson.is_active


@pytest.mark.django_db
def test_grid_is_school_scoped(client, school_a, school_b, make_session, login_as):
    make_session(school_a, name="2026/2027", current=True)
    make_session(school_b)
    beta = make_class(school_b, "Beta Primary 2")
    login_as(school_a, Role.OWNER)
    assert client.get(reverse("timetable:grid", args=[beta.pk])).status_code == 404


@pytest.mark.django_db
def test_owner_places_a_lesson_and_a_break(client, school_a, make_session, login_as, maths):
    session = make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    class_takes(klass, maths)
    login_as(school_a, Role.OWNER)

    pretty = make_subject(school_a, "English")
    class_takes(klass, pretty)
    add_slot(client, klass, subject=maths)
    add_slot(client, klass, label="Long break", times={"starts_at": "11:00", "ends_at": "11:40"})
    # A lesson must not post a label; a break without one is refused.
    add_slot(client, klass, subject=maths, label="Pop quiz")
    add_slot(client, klass, label="")
    lessons = TimetableSlot.objects.filter(subject__isnull=False)
    breaks = TimetableSlot.objects.filter(subject__isnull=True)
    assert lessons.count() == 1 and breaks.count() == 1
    assert breaks.get().label == "Long break"
    assert AuditLog.objects.filter(action="timetable.slot_created").count() == 2


@pytest.mark.django_db
def test_owner_cannot_place_a_subject_the_class_does_not_take(
    client, school_a, make_session, login_as, maths
):
    make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    login_as(school_a, Role.OWNER)

    add_slot(client, klass, subject=maths)
    assert TimetableSlot.objects.count() == 0  # never offered in the form

    untaught = make_subject(school_a, "Yoruba")
    add_slot(client, klass, subject=untaught)
    assert TimetableSlot.objects.count() == 0
    assert not AuditLog.objects.filter(action="timetable.slot_created").exists()


@pytest.mark.django_db
def test_overlap_replies_with_a_friendly_message(client, school_a, make_session, login_as, maths):
    session = make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    class_takes(klass, maths)
    login_as(school_a, Role.OWNER)
    slot(school_a, session, klass, subject=maths,
         starts_at=time(9, 0), ends_at=time(9, 40))

    English = make_subject(school_a, "English")
    class_takes(klass, English)
    response = add_slot(client, klass, subject=English)
    assert TimetableSlot.objects.count() == 1
    assert "already runs" in response.content.decode()


@pytest.mark.django_db
def test_archiving_takes_the_period_off_but_keeps_it(
    client, school_a, make_session, login_as, maths
):
    session = make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    class_takes(klass, maths)
    login_as(school_a, Role.OWNER)
    lesson = slot(school_a, session, klass, subject=maths)

    client.post(reverse("timetable:archive", args=[lesson.pk]))
    lesson.refresh_from_db()
    assert not lesson.is_active and TimetableSlot.objects.count() == 1
    empty_grid = client.get(reverse("timetable:grid", args=[klass.pk])).content.decode()
    assert "Nothing on the timetable yet" in empty_grid

    client.post(reverse("timetable:restore", args=[lesson.pk]))
    lesson.refresh_from_db()
    assert lesson.is_active
    actions = list(
        AuditLog.objects.order_by("id")
        .filter(action__startswith="timetable.")
        .values_list("action", flat=True)
    )
    assert actions == ["timetable.slot_archived", "timetable.slot_restored"]


@pytest.mark.django_db
def test_a_foreign_slot_cannot_be_touched(
    client, school_a, school_b, make_session, login_as
):
    make_session(school_a, name="2026/2027", current=True)
    beta_session = make_session(school_b)
    beta = make_class(school_b, "Beta Primary 2")
    foreign = slot(school_b, beta_session, beta, label="Break")
    login_as(school_a, Role.OWNER)
    for url in (
        reverse("timetable:archive", args=[foreign.pk]),
        reverse("timetable:restore", args=[foreign.pk]),
    ):
        assert client.post(url).status_code == 404
    foreign.refresh_from_db()
    assert foreign.is_active and not AuditLog.objects.filter(
        action__startswith="timetable."
    ).exists()


@pytest.mark.django_db
def test_my_timetable_lists_only_the_teacher_covered_lessons(
    client, school_a, make_session, login_as, make_member, maths
):
    session = make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    class_takes(klass, maths)
    english = make_subject(school_a, "English")
    class_takes(klass, english)
    teacher = login_as(school_a, Role.TEACHER)
    assign(maths, klass, teacher, session)  # class-wide
    colleague = make_member(school_a)
    assign(english, klass, colleague, session)

    slot(school_a, session, klass, subject=maths)
    slot(school_a, session, klass, subject=english, day=5,
         starts_at=time(9, 0), ends_at=time(9, 40))
    slot(school_a, session, klass, label="Long break", day=5,
         starts_at=time(11, 0), ends_at=time(11, 40))

    response = client.get(reverse("timetable:my"))
    content = response.content.decode()
    assert "Mathematics" in content
    assert "English" not in content    # colleague's lesson, not mine
    assert "Long break" not in content  # a break is nobody's lesson

    # The next school's manager gets 403 and sees nothing of this list.
    login_as(school_a, Role.BURSAR)
    assert client.get(reverse("timetable:my")).status_code == 403


@pytest.mark.django_db
def test_my_timetable_section_assignment_covers_only_its_sections(
    client, school_a, make_session, login_as, maths
):
    from apps.classes.models import Section

    session = make_session(school_a, name="2026/2027", current=True)
    klass = make_class(school_a)
    class_takes(klass, maths)
    teacher = login_as(school_a, Role.TEACHER)
    a = Section.objects.create(school=school_a, school_class=klass, name="A")
    b = Section.objects.create(school=school_a, school_class=klass, name="B")
    assign(maths, klass, teacher, session, section=a)  # exact section, no class-wide

    slot(school_a, session, klass, subject=maths, section=a)
    slot(school_a, session, klass, subject=maths, section=b, day=5,
         starts_at=time(9, 0), ends_at=time(9, 40))

    content = client.get(reverse("timetable:my")).content.decode()
    assert f"{a}" in content and f"{b}" not in content
    assert "Primary 4 A" in content and "Primary 4 B" not in content


@pytest.mark.django_db
def test_another_schools_never_appear_in_a_teacher_schedule(
    client, school_a, school_b, make_session, login_as, maths
):
    session = make_session(school_a, name="2026/2027", current=True)
    beta_session = make_session(school_b)
    klass = make_class(school_a)
    class_takes(klass, maths)
    teacher = login_as(school_a, Role.TEACHER)
    assign(maths, klass, teacher, session)
    slot(school_a, session, klass, subject=maths)

    beta = make_class(school_b, "Beta Primary 2")
    beta_maths = make_subject(school_b, "Beta Mathematics")
    ClassSubject.objects.create(school=school_b, school_class=beta, subject=beta_maths)
    slot(school_b, beta_session, beta, subject=beta_maths,
         starts_at=time(9, 0), ends_at=time(9, 40))

    content = client.get(reverse("timetable:my")).content.decode()
    assert "Mathematics" in content
    assert "Beta Primary 2" not in content
