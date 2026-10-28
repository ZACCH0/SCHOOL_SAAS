import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academics.models import AcademicPeriod, AcademicSession
from apps.classes.models import Level, SchoolClass, Section
from apps.subjects.models import ClassSubject, Subject
from apps.schools.models import Membership
from apps.students.models import Student
from apps.subjects.models import Subject

from .models import (
    AssessmentComponent,
    GradeBoundary,
    GradeScale,
    ResultSheet,
    Score,
    SubjectResult,
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
def session(school_a):
    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", is_current=True,
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )


@pytest.fixture
def period(session, school_a):
    return AcademicPeriod.objects.create(
        school=school_a, session=session, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18), is_current=True,
    )


@pytest.fixture
def english(school_a, primary_three):
    subject = Subject.objects.create(school=school_a, name="English Studies")
    ClassSubject.objects.create(school=school_a, school_class=primary_three, subject=subject)
    return subject


@pytest.fixture
def sheet(school_a, primary_three, period, english):
    return ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three, subject=english,
    )


@pytest.fixture
def pupil(school_a, primary_three):
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three,
    )


@pytest.fixture
def exam(school_a, session):
    return AssessmentComponent.objects.create(
        school=school_a, session=session, name="Exam",
        max_score=Decimal("60"), weight=Decimal("60"),
    )


# --- grade scales and boundaries ---


def test_grade_scale_belongs_to_a_session(school_a, session):
    scale = GradeScale.objects.create(school=school_a, session=session, name="Primary A-F")
    assert scale.is_active is True


def test_same_scale_name_twice_in_one_session_rejected(school_a, session):
    GradeScale.objects.create(school=school_a, session=session, name="A-F")
    with pytest.raises(IntegrityError), transaction.atomic():
        GradeScale.objects.create(school=school_a, session=session, name="a-f")


def test_same_scale_name_in_two_sessions_allowed(school_a, session):
    GradeScale.objects.create(school=school_a, session=session, name="A-F")
    second = AcademicSession.objects.create(
        school=school_a, name="2027/2028",
        start_date=date(2027, 9, 1), end_date=date(2028, 7, 31),
    )
    scale = GradeScale.objects.create(school=school_a, session=second, name="A-F")
    assert scale.session == second


def test_scale_rejects_session_of_another_school(school_a, school_b, session):
    other_session = AcademicSession.objects.create(
        school=school_b, name="2026/2027",
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    with pytest.raises(ValidationError):
        GradeScale.objects.create(school=school_a, session=other_session, name="A-F")


def test_component_rejects_session_of_another_school(school_a, school_b, session):
    other_session = AcademicSession.objects.create(
        school=school_b, name="2026/2027",
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    with pytest.raises(ValidationError):
        AssessmentComponent.objects.create(
            school=school_a, session=other_session, name="Exam",
            max_score=Decimal("60"), weight=Decimal("60"),
        )


def test_boundary_min_percent_must_be_0_to_100(school_a, session):
    scale = GradeScale.objects.create(school=school_a, session=session, name="A-F")
    with pytest.raises(ValidationError):
        GradeBoundary.objects.create(scale=scale, grade="A", min_percent=Decimal("101"))


def test_duplicate_grade_label_rejected(school_a, session):
    scale = GradeScale.objects.create(school=school_a, session=session, name="A-F")
    GradeBoundary.objects.create(
        school=school_a, scale=scale, grade="A", min_percent=Decimal("70"),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        GradeBoundary.objects.create(
            school=school_a, scale=scale, grade="a", min_percent=Decimal("60"),
        )


def test_two_boundaries_cannot_start_at_the_same_percent(school_a, session):
    scale = GradeScale.objects.create(school=school_a, session=session, name="A-F")
    GradeBoundary.objects.create(
        school=school_a, scale=scale, grade="A", min_percent=Decimal("70"),
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        GradeBoundary.objects.create(
            school=school_a, scale=scale, grade="B", min_percent=Decimal("70"),
        )


def test_same_label_in_two_scales_allowed(school_a, session):
    one = GradeScale.objects.create(school=school_a, session=session, name="Primary")
    two = GradeScale.objects.create(school=school_a, session=session, name="Secondary")
    GradeBoundary.objects.create(school=school_a, scale=one, grade="A", min_percent=Decimal("70"))
    boundary = GradeBoundary.objects.create(
        school=school_a, scale=two, grade="A", min_percent=Decimal("80"),
    )
    assert boundary.points is None


# --- assessment components ---


def test_school_wide_component_has_no_level(school_a, session):
    component = AssessmentComponent.objects.create(
        school=school_a, session=session, name="Exam",
        max_score=Decimal("60"), weight=Decimal("60"),
    )
    assert component.level is None


def test_level_scoped_component(school_a, session, level):
    component = AssessmentComponent.objects.create(
        school=school_a, session=session, level=level, name="Exam",
        max_score=Decimal("60"), weight=Decimal("60"),
    )
    assert component.level == level


def test_duplicate_school_wide_component_name_rejected(school_a, session):
    AssessmentComponent.objects.create(
        school=school_a, session=session, name="Exam",
        max_score=Decimal("60"), weight=Decimal("60"),
    )
    with pytest.raises(ValidationError):
        AssessmentComponent.objects.create(
            school=school_a, session=session, name="exam",
            max_score=Decimal("30"), weight=Decimal("30"),
        )


def test_components_max_score_and_weight_must_be_positive(school_a, session):
    with pytest.raises(IntegrityError), transaction.atomic():
        AssessmentComponent.objects.create(
            school=school_a, session=session, name="Exam",
            max_score=Decimal("0"), weight=Decimal("60"),
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        AssessmentComponent.objects.create(
            school=school_a, session=session, name="Exam",
            max_score=Decimal("60"), weight=Decimal("0"),
        )


# --- result sheets ---


def test_draft_sheet_may_record_who_entered_scores(sheet, make_member):
    sheet.submitted_by = make_member(sheet.school, role=Role.TEACHER)
    sheet.save()


def test_submitted_sheet_without_a_submitter_rejected(school_a, primary_three, period, english):
    sheet = ResultSheet(
        school=school_a, period=period, school_class=primary_three,
        subject=english, status=ResultSheet.Status.SUBMITTED,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        sheet.save()


def test_sheet_starts_in_draft_with_no_snapshot_yet(sheet):
    assert sheet.status == ResultSheet.Status.DRAFT
    assert sheet.weights_snapshot is None


def test_one_sheet_per_class_subject_period(school_a, primary_three, period, english):
    ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three, subject=english,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ResultSheet.objects.create(
            school=school_a, period=period, school_class=primary_three, subject=english,
        )


def test_one_sheet_per_section_subject_period(school_a, primary_three, period, english):
    section = Section.objects.create(school=school_a, school_class=primary_three, name="A")
    ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section, subject=english,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        ResultSheet.objects.create(
            school=school_a, period=period, school_class=primary_three,
            section=section, subject=english,
        )


def test_two_sections_can_each_have_a_sheet(school_a, primary_three, period, english):
    section_a = Section.objects.create(school=school_a, school_class=primary_three, name="A")
    section_b = Section.objects.create(school=school_a, school_class=primary_three, name="B")
    ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section_a, subject=english,
    )
    sheet_b = ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section_b, subject=english,
    )
    assert sheet_b.section == section_b


def test_sheet_rejects_record_from_another_school(school_a, school_b, period, english):
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    subject_b = Subject.objects.create(school=school_b, name="English Studies")
    ClassSubject.objects.create(school=school_b, school_class=class_b, subject=subject_b)
    session_b = AcademicSession.objects.create(
        school=school_b, name="2026/2027",
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    period_b = AcademicPeriod.objects.create(
        school=school_b, session=session_b, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )
    with pytest.raises(ValidationError):
        ResultSheet.objects.create(
            school=school_a, period=period_b, school_class=class_b, subject=subject_b,
        )
    with pytest.raises(ValidationError):
        ResultSheet.objects.create(
            school=school_a, period=period, school_class=class_b, subject=english,
        )


# --- scores ---


def test_score_stores_raw_value_against_a_component(sheet, pupil, exam):
    score = Score.objects.create(
        school=sheet.school, sheet=sheet, student=pupil, component=exam, value=Decimal("54"),
    )
    assert str(score.component.session_id) == str(sheet.period.session_id)


def test_score_rejected_for_pupil_of_another_class(sheet, school_a, level):
    other_class = SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)
    pupil = Student.objects.create(
        school=school_a, first_name="Bisi", last_name="Adeyi", sex="female",
        date_of_birth=date(2018, 1, 20), admission_number="FSS/2026/002",
        current_class=other_class,
    )
    exam = AssessmentComponent.objects.create(
        school=school_a, session=sheet.period.session, name="Exam",
        max_score=Decimal("60"), weight=Decimal("60"),
    )
    with pytest.raises(ValidationError):
        Score.objects.create(
            school=school_a, sheet=sheet, student=pupil, component=exam, value=Decimal("40"),
        )


def test_score_cannot_be_negative(sheet, pupil, exam):
    with pytest.raises(IntegrityError), transaction.atomic():
        Score.objects.create(
            school=sheet.school, sheet=sheet, student=pupil, component=exam, value=Decimal("-5"),
        )


def test_score_above_component_max_rejected(sheet, pupil, exam):
    with pytest.raises(ValidationError) as info:
        Score.objects.create(
            school=sheet.school, sheet=sheet, student=pupil, component=exam, value=Decimal("70"),
        )
    assert "maximum" in str(info.value)


def test_one_score_per_pupil_per_component(sheet, pupil, exam):
    school = sheet.school
    Score.objects.create(school=school, sheet=sheet, student=pupil, component=exam, value=Decimal("50"))
    with pytest.raises(IntegrityError), transaction.atomic():
        Score.objects.create(school=school, sheet=sheet, student=pupil, component=exam, value=Decimal("45"))


# --- subject results ---


def test_subject_result_keeps_the_grading_snapshot(sheet, pupil):
    result = SubjectResult.objects.create(
        school=sheet.school, sheet=sheet, student=pupil,
        total=Decimal("108"), percentage=Decimal("88.9"), grade="A",
        grade_remark="Excellent",
        scale_snapshot=[
            {"grade": "A", "min_percent": "70.0", "remark": "Excellent", "points": None},
            {"grade": "B", "min_percent": "60.0", "remark": "Very good", "points": None},
        ],
    )
    assert result.scale_snapshot[0]["min_percent"] == "70.0"
    assert result.grade == "A"


def test_one_subject_result_per_pupil_per_sheet(sheet, pupil):
    school = sheet.school
    payload = dict(total=Decimal("108"), percentage=Decimal("88.9"), grade="A")
    SubjectResult.objects.create(school=school, sheet=sheet, student=pupil, **payload)
    with pytest.raises(IntegrityError), transaction.atomic():
        SubjectResult.objects.create(school=school, sheet=sheet, student=pupil, **payload)
