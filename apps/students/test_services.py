import pytest
from datetime import date
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass, Section
from apps.schools.models import Membership

from .models import GuardianLink, Student, StudentClassHistory
from .services import (
    add_guardian, create_student, move_student, remove_guardian,
    set_student_status, update_student,
)

Role = Membership.Role


@pytest.fixture
def level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_three(school_a, level):
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 3", order=3)


@pytest.fixture
def primary_four(school_a, level):
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)


@pytest.fixture
def section_a(school_a, primary_three):
    return Section.objects.create(school=school_a, school_class=primary_three, name="A")


@pytest.fixture
def make_student(school_a, primary_three):
    def make(**overrides):
        data = dict(
            school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
            date_of_birth=date(2018, 3, 5), admission_number="FSS/2025/001",
            current_class=primary_three,
        )
        data.update(overrides)
        return Student.objects.create(**data)

    return make


@pytest.fixture
def parent(school_a, make_member):
    return make_member(school_a, role=Role.PARENT)


@pytest.mark.django_db
def test_admin_creates_student_with_history_and_it_is_audited(
    school_a, level, primary_four, make_request, make_session
):
    session = make_session(school_a, current=True)
    request = make_request(school_a)
    student = create_student(
        request, first_name="  Blessing ", last_name="Ige", sex="female",
        date_of_birth=date(2019, 1, 10), admission_number="FSS/2026/001",
        address="1 Isale Taba Road", current_class=primary_four,
    )
    assert student.first_name == "Blessing" and student.school == school_a
    assert StudentClassHistory.objects.filter(
        student=student, session=session, school_class=primary_four
    ).exists()
    entry = AuditLog.objects.get(action="student.created")
    assert entry.school == school_a
    assert entry.metadata["admission_number"] == "FSS/2026/001"


@pytest.mark.django_db
def test_teacher_cannot_create_a_student(school_a, level, make_request):
    with pytest.raises(PermissionDenied):
        create_student(
            make_request(school_a, Role.TEACHER), first_name="X", last_name="Y",
            sex="male", date_of_birth=date(2019, 1, 1), admission_number="A/1",
        )
    assert not Student.objects.exists() and not AuditLog.objects.exists()


@pytest.mark.django_db
def test_duplicate_admission_number_gives_friendly_error(school_a, make_student, make_request):
    make_student()
    with pytest.raises(ValidationError) as exc:
        create_student(
            make_request(school_a), first_name="Tobi", last_name="Raji", sex="male",
            date_of_birth=date(2019, 2, 2), admission_number="FSS/2025/001",
        )
    assert "admission number" in str(exc.value)


@pytest.mark.django_db
def test_a_student_of_another_school_is_refused(school_b, make_student, make_request):
    student = make_student()
    with pytest.raises(PermissionDenied):
        update_student(
            make_request(school_b), student, fields={"first_name": "Chineme"}
        )


@pytest.mark.django_db
def test_update_writes_changes_to_the_log(school_a, make_student, make_request):
    student = make_student()
    update_student(make_request(school_a), student, fields={"address": "2 Koso Area", "first_name": "Oluwaseun"})
    student.refresh_from_db()
    assert student.first_name == "Oluwaseun" and student.address == "2 Koso Area"
    entry = AuditLog.objects.get(action="student.updated")
    assert entry.metadata["changes"]["first_name"] == ["Ade", "Oluwaseun"]


@pytest.mark.django_db
def test_status_change_is_audited(school_a, make_student, make_request):
    student = make_student()
    set_student_status(make_request(school_a), student, Student.Status.SUSPENDED)
    student.refresh_from_db()
    assert student.status == Student.Status.SUSPENDED
    entry = AuditLog.objects.get(action="student.status_changed")
    assert entry.metadata["previous"] == "active" and entry.metadata["new"] == "suspended"


@pytest.mark.django_db
def test_move_student_updates_current_class_and_history(
    school_a, level, primary_three, primary_four, section_a, make_student, make_request
):
    history_details = school_a.academics_academicsession_set.create(
        name="2026/2027", start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
        is_current=True,
    )
    student = make_student(current_class=primary_three, current_section=section_a)
    StudentClassHistory.objects.create(
        school=school_a, student=student, session=history_details,
        school_class=primary_three, section=section_a,
    )
    move_student(make_request(school_a), student, school_class=primary_four)
    student.refresh_from_db()
    assert student.current_class == primary_four
    assert student.current_section is None
    row = StudentClassHistory.objects.get(student=student, session=history_details)
    assert row.school_class == primary_four
    assert AuditLog.objects.filter(action="student.moved").exists()


@pytest.mark.django_db
def test_guardian_must_be_a_parent(
    school_a, make_student, make_request, parent, make_member
):
    student = make_student()
    teacher = make_member(school_a, role=Role.TEACHER)
    with pytest.raises(ValidationError):
        add_guardian(
            make_request(school_a), student, membership=teacher,
            relationship=GuardianLink.Relationship.MOTHER,
        )
    assert not GuardianLink.objects.exists()


@pytest.mark.django_db
def test_adding_a_primary_guardian_makes_it_the_only_one(
    school_a, make_student, parent, make_request
):
    student = make_student()
    from apps.accounts.models import User
    other_user = User.objects.create_user("second-parent", password="S3cure-pass!")
    parent_two, _ = Membership.objects.get_or_create(
        user=other_user, school=school_a, defaults={"role": Role.PARENT},
    )
    request = make_request(school_a)
    first = add_guardian(
        request, student, membership=parent,
        relationship=GuardianLink.Relationship.FATHER, is_primary=True,
    )
    second = add_guardian(
        request, student, membership=parent_two,
        relationship=GuardianLink.Relationship.MOTHER, is_primary=True,
    )
    first.refresh_from_db()
    assert second.is_primary and not first.is_primary


@pytest.mark.django_db
def test_remove_guardian_records_the_action(school_a, make_student, parent, make_request):
    student = make_student()
    link = add_guardian(
        make_request(school_a), student, membership=parent,
        relationship=GuardianLink.Relationship.FATHER,
    )
    user = remove_guardian(make_request(school_a), link)
    assert user == parent.user.get_username()
    assert not GuardianLink.objects.exists()
