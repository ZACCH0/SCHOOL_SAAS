import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError

from apps.academics.models import AcademicPeriod, AcademicSession
from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass, Section
from apps.classes.models import ClassTeacher
from apps.schools.models import Membership
from apps.students.models import Student
from apps.subjects.models import ClassSubject, Subject, TeacherAssignment

from .models import (
    AssessmentComponent,
    GradeBoundary,
    GradeScale,
    ResultSheet,
    Score,
    SubjectResult,
)
from .services import (
    approve_sheet,
    publish_sheet,
    review_sheet,
    save_score,
    send_back,
    submit_sheet,
)

Role = Membership.Role
pytestmark = pytest.mark.django_db


@pytest.fixture
def level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_three(school_a, level):
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 3", order=3)


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
def maths(school_a, primary_three):
    subject = Subject.objects.create(school=school_a, name="Mathematics")
    ClassSubject.objects.create(school=school_a, school_class=primary_three, subject=subject)
    return subject


@pytest.fixture
def sheet(school_a, primary_three, section_a, period, maths):
    return ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section_a, subject=maths,
    )


@pytest.fixture
def pupil(school_a, primary_three, section_a):
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three, current_section=section_a,
    )


@pytest.fixture
def pupil_two(school_a, primary_three, section_a):
    return Student.objects.create(
        school=school_a, first_name="Bisi", last_name="Adeyi", sex="female",
        date_of_birth=date(2018, 1, 20), admission_number="FSS/2026/002",
        current_class=primary_three, current_section=section_a,
    )


@pytest.fixture
def components(school_a, session):
    made = []
    for name, max_score in (("First Test", 20), ("Second Test", 20), ("Examination", 60)):
        made.append(
            AssessmentComponent.objects.create(
                school=school_a, session=session, name=name,
                max_score=Decimal(max_score), weight=Decimal(max_score),
            )
        )
    return made


@pytest.fixture
def scale(school_a, session):
    made = GradeScale.objects.create(school=school_a, session=session, name="Primary A-F")
    for grade, min_percent, remark in [
        ("A", 70, "Excellent"),
        ("B", 60, "Very Good"),
        ("C", 50, "Good"),
        ("D", 45, "Fair"),
        ("F", 0, "Needs improvement"),
    ]:
        GradeBoundary.objects.create(
            school=school_a, scale=made,
            grade=grade, min_percent=Decimal(min_percent), remark=remark,
        )
    return made


def _assignment(school, session, primary_three, section_a, maths, member, section=True):
    TeacherAssignment.objects.create(
        school=school, session=session, school_class=primary_three,
        section=section_a if section else None, subject=maths, teacher=member,
    )


@pytest.fixture
def assigned_teacher(school_a, session, primary_three, section_a, maths, make_member):
    teacher = make_member(school_a, role=Role.TEACHER)
    _assignment(school_a, session, primary_three, section_a, maths, teacher)
    return teacher


@pytest.fixture
def other_teacher(school_a, make_member):
    return make_member(school_a, role=Role.TEACHER)


def _score(school_a, sheet, pupil, components, first=12, second=15, exam=48):
    for component, value in zip(components, (first, second, exam)):
        Score.objects.create(
            school=school_a, sheet=sheet, student=pupil,
            component=component, value=Decimal(value),
        )


# --- permission to enter scores ---


def test_assigned_teacher_saves_a_score_and_the_result_is_computed(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    score = save_score(request, sheet, pupil, components[0], "12")
    assert score.value == Decimal("12.00")
    result = SubjectResult.objects.get(sheet=sheet, student=pupil)
    assert result.total == Decimal("12.00")
    assert result.percentage == Decimal("60.0")
    assert result.grade == "B" and result.grade_remark == "Very Good"
    assert result.scale_snapshot[0]["grade"] == "A"
    assert AuditLog.objects.filter(action="results.score_saved").exists()


def test_teacher_without_the_assignment_is_refused(
    school_a, sheet, pupil, components, scale, other_teacher, make_request
):
    with pytest.raises(PermissionDenied):
        save_score(
            make_request(school_a, Role.TEACHER, member=other_teacher),
            sheet, pupil, components[0], "12",
        )
    assert not Score.objects.exists()


def test_teacher_assigned_to_a_different_subject_is_refused(
    school_a, primary_three, section_a, session, sheet, pupil, components, scale, make_member, make_request
):
    english = Subject.objects.create(school=school_a, name="English Studies")
    ClassSubject.objects.create(school=school_a, school_class=primary_three, subject=english)
    teacher = make_member(school_a, role=Role.TEACHER)
    _assignment(school_a, session, primary_three, section_a, english, teacher)
    with pytest.raises(PermissionDenied):
        save_score(
            make_request(school_a, Role.TEACHER, member=teacher),
            sheet, pupil, components[0], "12",
        )


def test_class_wide_assignment_covers_a_section_sheet(
    school_a, session, primary_three, section_a, maths, sheet, pupil, components, scale, make_member, make_request
):
    teacher = make_member(school_a, role=Role.TEACHER)
    _assignment(school_a, session, primary_three, section_a, maths, teacher, section=False)
    score = save_score(
        make_request(school_a, Role.TEACHER, member=teacher),
        sheet, pupil, components[0], "12",
    )
    assert score.value == Decimal("12.00")


def test_parents_and_bursars_cannot_enter_scores(
    school_a, sheet, pupil, components, scale, make_request
):
    for role in (Role.PARENT, Role.BURSAR):
        with pytest.raises(PermissionDenied):
            save_score(make_request(school_a, role), sheet, pupil, components[0], "12")


def test_owner_and_admin_score_any_sheet(school_a, sheet, pupil, components, scale, make_request):
    for role in (Role.OWNER, Role.ADMIN):
        save_score(make_request(school_a, role), sheet, pupil, components[0], "12")
    assert Score.objects.count() == 1


def test_records_from_another_school_are_refused(
    school_a, school_b, sheet, components, scale, make_request
):
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    stranger = Student.objects.create(
        school=school_b, first_name="Tunde", last_name="Elsewhere", sex="male",
        date_of_birth=date(2018, 2, 2), admission_number="BET/2026/001",
        current_class=class_b,
    )
    with pytest.raises(PermissionDenied):
        save_score(make_request(school_a, Role.ADMIN), sheet, stranger, components[0], "12")


def test_score_above_the_component_maximum_is_refused(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    with pytest.raises(ValidationError) as info:
        save_score(
            make_request(school_a, Role.TEACHER, member=assigned_teacher),
            sheet, pupil, components[0], "25",
        )
    assert "maximum" in str(info.value)
    assert not Score.objects.exists()
    assert not AuditLog.objects.filter(action="results.score_saved").exists()


def test_component_from_another_level_is_refused(
    school_a, session, sheet, pupil, scale, assigned_teacher, make_request
):
    jss = Level.objects.create(school=school_a, name="JSS", order=2)
    component = AssessmentComponent.objects.create(
        school=school_a, session=session, level=jss, name="JSS Exam",
        max_score=Decimal("60"), weight=Decimal("60"),
    )
    with pytest.raises(ValidationError):
        save_score(
            make_request(school_a, Role.TEACHER, member=assigned_teacher),
            sheet, pupil, component, "50",
        )


def test_resaving_updates_the_score_and_the_grade(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    save_score(request, sheet, pupil, components[2], "40")
    assert SubjectResult.objects.get(sheet=sheet, student=pupil).grade == "B"
    save_score(request, sheet, pupil, components[2], "58")
    result = SubjectResult.objects.get(sheet=sheet, student=pupil)
    assert result.percentage == Decimal("96.7") and result.grade == "A"
    entry = AuditLog.objects.filter(action="results.score_saved").order_by("-id").first()
    assert entry.metadata["previous"] == "40.00" and entry.metadata["value"] == "58.00"


# --- the workflow ---


def test_submit_snapshots_weights_and_records_the_submitter(
    school_a, sheet, pupil, pupil_two, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for student in (pupil, pupil_two):
        for component, value in zip(components, (12, 15, 48)):
            save_score(request, sheet, student, component, value)
    submitted = submit_sheet(request, sheet)
    assert submitted.status == ResultSheet.Status.SUBMITTED
    assert submitted.submitted_by == assigned_teacher
    assert sorted(c["name"] for c in submitted.weights_snapshot) == [
        "Examination", "First Test", "Second Test",
    ]
    assert AuditLog.objects.filter(action="results.sheet_submitted").exists()


def test_submit_refuses_an_empty_sheet(sheet, components, assigned_teacher, make_request, school_a):
    with pytest.raises(ValidationError) as info:
        submit_sheet(make_request(school_a, Role.TEACHER, member=assigned_teacher), sheet)
    assert "at least one score" in str(info.value)


def test_submit_grades_pupils_whose_scores_were_created_directly(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    for component, value in zip(components, ("12", "15", "48")):
        Score.objects.create(
            school=school_a, sheet=sheet, student=pupil,
            component=component, value=Decimal(value),
        )
    submitted = submit_sheet(
        make_request(school_a, Role.TEACHER, member=assigned_teacher), sheet
    )
    result = SubjectResult.objects.get(sheet=sheet, student=pupil)
    assert submitted.status == ResultSheet.Status.SUBMITTED
    assert result.percentage == Decimal("75.0") and result.grade == "A"


def test_submit_refuses_an_incomplete_pupil(
    school_a, sheet, pupil, pupil_two, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for component, value in zip(components, (12, 15, 48)):
        save_score(request, sheet, pupil, component, value)
    save_score(request, sheet, pupil_two, components[0], "10")
    save_score(request, sheet, pupil_two, components[1], "10")
    with pytest.raises(ValidationError) as info:
        submit_sheet(request, sheet)
    assert "missing" in str(info.value)
    assert sheet.status == ResultSheet.Status.DRAFT


def test_unassigned_teacher_cannot_submit(sheet, other_teacher, make_request, school_a):
    with pytest.raises(PermissionDenied):
        submit_sheet(make_request(school_a, Role.TEACHER, member=other_teacher), sheet)


def test_scores_cannot_be_edited_after_submission(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for component, value in zip(components, (12, 15, 48)):
        save_score(request, sheet, pupil, component, value)
    submit_sheet(request, sheet)
    with pytest.raises(ValidationError):
        save_score(request, sheet, pupil, components[0], "15")


def test_owner_and_admin_walk_the_workflow(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for component, value in zip(components, (12, 15, 48)):
        save_score(request, sheet, pupil, component, value)
    submit_sheet(request, sheet)
    admin = lambda: make_request(school_a, Role.ADMIN)  # noqa: E731
    review_sheet(admin(), sheet)
    assert sheet.status == ResultSheet.Status.REVIEWED
    assert sheet.reviewed_by.role == Role.ADMIN
    approve_sheet(admin(), sheet)
    assert sheet.status == ResultSheet.Status.APPROVED
    publish_sheet(admin(), sheet)
    assert sheet.status == ResultSheet.Status.PUBLISHED
    assert AuditLog.objects.filter(action="results.sheet_reviewed").exists()
    assert AuditLog.objects.filter(action="results.sheet_approved").exists()
    assert AuditLog.objects.filter(action="results.sheet_published").exists()


def test_workflow_order_is_enforced(sheet, make_request, school_a):
    admin = make_request(school_a, Role.ADMIN)
    with pytest.raises(ValidationError):
        review_sheet(admin, sheet)
    with pytest.raises(ValidationError):
        approve_sheet(admin, sheet)
    with pytest.raises(ValidationError):
        publish_sheet(admin, sheet)


def test_teacher_cannot_review_or_publish(sheet, make_request, school_a):
    teacher = make_request(school_a, Role.TEACHER)
    with pytest.raises(PermissionDenied):
        review_sheet(teacher, sheet)
    with pytest.raises(PermissionDenied):
        approve_sheet(teacher, sheet)
    with pytest.raises(PermissionDenied):
        publish_sheet(teacher, sheet)


def test_send_back_returns_to_draft_and_clears_the_submitter(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for component, value in zip(components, (12, 15, 48)):
        save_score(request, sheet, pupil, component, value)
    submit_sheet(request, sheet)
    send_back(make_request(school_a, Role.ADMIN), sheet)
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.DRAFT
    assert sheet.submitted_by is None and sheet.weights_snapshot is None
    assert AuditLog.objects.filter(action="results.sheet_sent_back").exists()


def test_an_approved_sheet_cannot_be_sent_back(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for component, value in zip(components, (12, 15, 48)):
        save_score(request, sheet, pupil, component, value)
    submit_sheet(request, sheet)
    admin = make_request(school_a, Role.ADMIN)
    review_sheet(admin, sheet)
    approve_sheet(admin, sheet)
    with pytest.raises(ValidationError):
        send_back(admin, sheet)


def test_grading_uses_the_active_scale_boundaries(
    school_a, sheet, pupil, components, scale, assigned_teacher, make_request
):
    request = make_request(school_a, Role.TEACHER, member=assigned_teacher)
    for component, value in zip(components, (14, 17, 55)):
        save_score(request, sheet, pupil, component, value)
    result = SubjectResult.objects.get(sheet=sheet, student=pupil)
    assert result.total == Decimal("86.00")
    assert result.percentage == Decimal("86.0")
    assert result.grade == "A" and result.grade_remark == "Excellent"
    assert result.scale_snapshot[-1]["min_percent"] == "0.0"
