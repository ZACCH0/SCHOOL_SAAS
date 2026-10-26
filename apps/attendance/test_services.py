import pytest
from datetime import date
from django.core.exceptions import PermissionDenied, ValidationError

from apps.academics.models import AcademicSession
from apps.classes.models import ClassTeacher, Level, SchoolClass, Section
from apps.audit.models import AuditLog
from apps.schools.models import Membership
from apps.subjects.models import TeacherAssignment
from apps.students.models import Student

from .models import AttendanceRecord, AttendanceSession
from .services import mark_student, open_register

Role = Membership.Role
DAY = date(2026, 10, 26)


@pytest.fixture
def school_level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_three(school_a, school_level):
    return SchoolClass.objects.create(school=school_a, level=school_level, name="Primary 3", order=3)


@pytest.fixture
def section_a(school_a, primary_three):
    return Section.objects.create(school=school_a, school_class=primary_three, name="A")


@pytest.fixture
def session(school_a):
    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", is_current=True,
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )


@pytest.fixture
def period(session, school_a):
    return session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )


@pytest.fixture
def pupil(school_a, primary_three, section_a):
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three, current_section=section_a,
    )


@pytest.fixture
def assigned_teacher(school_a, session, primary_three, section_a, make_member):
    teacher = make_member(school_a, role=Role.TEACHER)
    ClassTeacher.objects.create(
        school=school_a, session=session, school_class=primary_three,
        section=section_a, teacher=teacher,
    )
    return teacher


@pytest.fixture
def other_teacher(school_a, session, make_member):
    return make_member(school_a, role=Role.TEACHER)


@pytest.mark.django_db
def test_assigned_teacher_opens_the_register_and_pupils_start_present(
    school_a, primary_three, section_a, session, assigned_teacher, pupil, make_request
):
    register, opened = open_register(
        make_request(school_a, Role.TEACHER, member=assigned_teacher),
        school_class=primary_three, section=section_a, day=DAY,
    )
    assert opened and register.marked_by == assigned_teacher
    line = AttendanceRecord.objects.get(register=register, student=pupil)
    assert line.status == AttendanceRecord.Status.PRESENT
    assert AuditLog.objects.filter(action="attendance.register_opened").exists()


@pytest.mark.django_db
def test_opening_twice_returns_the_same_register_without_audit(
    school_a, primary_three, section_a, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    first, opened_first = open_register(request, school_class=primary_three, section=section_a, day=DAY)
    second, opened_second = open_register(request, school_class=primary_three, section=section_a, day=DAY)
    assert first == second
    assert opened_second is False


@pytest.mark.django_db
def test_a_teacher_not_assigned_to_the_class_is_refused(
    school_a, primary_three, section_a, other_teacher, make_request
):
    with pytest.raises(PermissionDenied):
        open_register(
            make_request(school_a, Role.TEACHER, member=other_teacher),
            school_class=primary_three, section=section_a, day=DAY,
        )
    assert not AttendanceSession.objects.exists()
    assert not AuditLog.objects.exists()


@pytest.mark.django_db
def test_parents_and_bursars_cannot_mark(
    school_a, primary_three, section_a, make_member, make_request
):
    for role in (Role.PARENT, Role.BURSAR):
        with pytest.raises(PermissionDenied):
            open_register(
                make_request(school_a, role), school_class=primary_three,
                section=section_a, day=DAY,
            )


@pytest.mark.django_db
def test_the_admin_may_open_any_class(
    school_a, primary_three, section_a, pupil, session, make_request
):
    register, opened = open_register(
        make_request(school_a, Role.ADMIN), school_class=primary_three, section=section_a, day=DAY
    )
    assert opened
    assert AttendanceRecord.objects.count() == 1


@pytest.mark.django_db
def test_a_teacher_of_another_school_is_refused(
    school_a, school_b, primary_three, section_a, make_request
):
    outsider = make_request(school_b, Role.TEACHER)
    with pytest.raises(PermissionDenied):
        open_register(outsider, school_class=primary_three, section=section_a, day=DAY)


@pytest.mark.django_db
def test_no_current_session_stops_the_register(school_a, primary_three, section_a, make_request):
    with pytest.raises(ValidationError):
        open_register(
            make_request(school_a, Role.ADMIN), school_class=primary_three,
            section=section_a, day=DAY,
        )


@pytest.mark.django_db
def test_marking_changes_a_line_and_records_the_change_correct_status(
    school_a, primary_three, section_a, session, assigned_teacher, pupil, make_request
):
    register, _ = open_register(
        make_request(school_a, Role.TEACHER, member=assigned_teacher),
        school_class=primary_three, section=section_a, day=DAY,
    )
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    mark_student(request, register, pupil, AttendanceRecord.Status.LATE, "Came after 8am")
    line = AttendanceRecord.objects.get(register=register)
    assert line.status == AttendanceRecord.Status.LATE
    entry = AuditLog.objects.get(action="attendance.marked")
    assert entry.metadata["previous"] == "present" and entry.metadata["new"] == "late"


@pytest.mark.django_db
def test_a_different_class_pupil_is_refused(
    school_a, school_level, primary_three, session, assigned_teacher, pupil, make_request
):
    register, _ = open_register(
        make_request(school_a, Role.TEACHER, member=assigned_teacher),
        school_class=pupil.current_class, section=pupil.current_section, day=DAY,
    )
    primary_five = SchoolClass.objects.create(
        school=school_a, level=school_level, name="Primary 5", order=5
    )
    stranger = Student.objects.create(
        school=school_a, first_name="Nope", last_name="Elsewhere", sex="female",
        date_of_birth=date(2018, 1, 1), admission_number="FSS/2026/099",
        current_class=primary_five,
    )
    with pytest.raises(ValidationError):
        mark_student(
            make_request(school_a, Role.TEACHER, member=assigned_teacher),
            register, stranger, AttendanceRecord.Status.PRESENT,
        )
    assert AttendanceRecord.objects.exclude(student=pupil).count() == 0


@pytest.mark.django_db
def test_marking_on_an_old_session_register_is_refused(
    school_a, primary_three, section_a, session, assigned_teacher, pupil, make_request
):
    old_session = AcademicSession.objects.create(
        school=school_a, name="2025/2026",
        start_date=date(2025, 9, 1), end_date=date(2026, 7, 31),
    )
    register = AttendanceSession.objects.create(
        school=school_a, school_class=primary_three, section=section_a,
        date=date(2026, 3, 5), session=old_session,
    )
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    request.attached_session = old_session
    with pytest.raises(PermissionDenied):
        mark_student(request, register, pupil, AttendanceRecord.Status.PRESENT)
