import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.academics.models import AcademicSession
from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass, Section
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

Role = Membership.Role
pytestmark = pytest.mark.django_db

# First Test /20, Second Test /20, Examination /60: 12 + 15 + 48 = 75 weighted.
VALUES = (12, 15, 48)


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
def english(school_a, primary_three):
    subject = Subject.objects.create(school=school_a, name="English Studies")
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
        made.boundaries.create(
            school=school_a, scale=made,
            grade=grade, min_percent=Decimal(min_percent), remark=remark,
        )
    return made


@pytest.fixture
def assigned_teacher(school_a, session, primary_three, section_a, maths, make_member):
    teacher = make_member(school_a, role=Role.TEACHER)
    TeacherAssignment.objects.create(
        school=school_a, session=session, school_class=primary_three,
        section=section_a, subject=maths, teacher=teacher,
    )
    return teacher


def _score_row(pupil, components):
    data = {"student": pupil.pk}
    for component, value in zip(components, VALUES):
        data[f"score_{component.pk}"] = str(value)
    return data


def _fill(client, sheet, pupils, components):
    for pupil in pupils:
        client.post(reverse("results:score", args=[sheet.pk]), _score_row(pupil, components))


def _fill_and_submit(client, sheet, pupils, components):
    _fill(client, sheet, pupils, components)
    client.post(reverse("results:submit", args=[sheet.pk]))


def _manager_member(school_a, role=Role.ADMIN):
    user = get_user_model().objects.create_user(
        f"{role}-views-{get_user_model().objects.count()}", password="S3cure-pass!"
    )
    return Membership.objects.create(user=user, school=school_a, role=role)


def _manager_client(school_a, role=Role.ADMIN):
    client = Client()
    client.force_login(_manager_member(school_a, role).user)
    return client


def _publish(client, school_a, pupils, sheet, components):
    """With the assigned teacher logged in: fill, submit, then walk the review workflow as an admin."""
    _fill_and_submit(client, sheet, pupils, components)
    admin = _manager_client(school_a)
    admin.post(reverse("results:review", args=[sheet.pk]))
    admin.post(reverse("results:approve", args=[sheet.pk]))
    admin.post(reverse("results:publish", args=[sheet.pk]))
    sheet.refresh_from_db()
    return admin


# --- access to the results home ---


def test_results_requires_login(client):
    assert client.get(reverse("results:home")).status_code == 302


def test_a_parent_and_bursar_cannot_open_results(client, school_a, login_as):
    for role in (Role.PARENT, Role.BURSAR):
        login_as(school_a, role)
        assert client.get(reverse("results:home")).status_code == 403


def test_admin_sees_the_sheets_for_the_term(
    client, school_a, session, period, primary_three, section_a, maths, sheet, login_as,
):
    login_as(school_a)
    content = client.get(reverse("results:home")).content
    assert b"Mathematics" in content
    assert b"Primary 3" in content
    assert b"Draft" in content


def test_teacher_sees_only_their_own_subject_sheets(
    client, school_a, session, period, primary_three, section_a, maths, english, sheet, login_as,
):
    ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section_a, subject=english,
    )
    member = login_as(school_a, Role.TEACHER)
    TeacherAssignment.objects.create(
        school=school_a, session=session, school_class=primary_three,
        section=section_a, subject=maths, teacher=member,
    )
    content = client.get(reverse("results:home")).content
    assert b"Mathematics" in content
    assert b"English Studies" not in content


def test_class_wide_assignment_covers_a_section_sheet(
    client, school_a, session, period, primary_three, section_a, maths, sheet, login_as,
):
    member = login_as(school_a, Role.TEACHER)
    TeacherAssignment.objects.create(
        school=school_a, session=session, school_class=primary_three,
        section=None, subject=maths, teacher=member,
    )
    assert b"Mathematics" in client.get(reverse("results:home")).content


# --- opening one sheet ---


def test_teacher_cannot_open_a_sheet_they_do_not_teach(
    client, school_a, session, period, primary_three, section_a, maths, sheet, login_as,
):
    login_as(school_a, Role.TEACHER)
    assert client.get(reverse("results:sheet", args=[sheet.pk])).status_code == 403


def test_admin_opens_a_sheet_and_sees_its_pupils(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, pupil_two, sheet, components, login_as,
):
    login_as(school_a)
    response = client.get(reverse("results:sheet", args=[sheet.pk]))
    assert response.status_code == 200
    content = response.content
    assert b"Ogunlesi" in content and b"Adeyi" in content
    assert b"Open for entry" in content
    assert b"name=\"score_" in content


def test_a_submitted_sheet_shows_no_score_inputs(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    _fill_and_submit(client, sheet, [pupil], components)
    response = client.get(reverse("results:sheet", args=[sheet.pk]))
    assert b"name=\"score_" not in response.content
    assert b"not open for entry" in response.content


# --- entering scores ---


def test_admin_saves_a_row_of_scores(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, login_as,
):
    login_as(school_a)
    response = client.post(
        reverse("results:score", args=[sheet.pk]), _score_row(pupil, components), follow=True,
    )
    assert response.status_code == 200
    score = Score.objects.get(sheet=sheet, student=pupil, component=components[0])
    assert score.value == Decimal("12.00")
    result = SubjectResult.objects.get(sheet=sheet, student=pupil)
    assert result.grade == "A"
    assert AuditLog.objects.filter(action="results.score_saved").exists()


def test_a_score_above_the_maximum_is_refused_with_a_friendly_message(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, login_as,
):
    login_as(school_a)
    response = client.post(
        reverse("results:score", args=[sheet.pk]),
        {"student": pupil.pk, f"score_{components[0].pk}": "25"},
        follow=True,
    )
    messages = [str(m.message) for m in response.context["messages"]]
    assert any("maximum" in text for text in messages)
    assert not Score.objects.exists()


def test_scores_for_a_pupil_from_another_school_are_refused(
    client, school_a, school_b, session, period, primary_three, section_a,
    maths, sheet, components, scale, login_as,
):
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    stranger = Student.objects.create(
        school=school_b, first_name="Tunde", last_name="Elsewhere", sex="male",
        date_of_birth=date(2018, 2, 2), admission_number="BET/2026/001",
        current_class=class_b,
    )
    login_as(school_a)
    response = client.post(
        reverse("results:score", args=[sheet.pk]),
        {"student": stranger.pk, f"score_{components[0].pk}": "12"},
        follow=True,
    )
    messages = [str(m.message) for m in response.context["messages"]]
    assert any("not in this school" in text for text in messages)
    assert not Score.objects.exists()


def test_assigned_teacher_enters_scores_and_submits_the_sheet(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, pupil_two, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    _fill_and_submit(client, sheet, [pupil, pupil_two], components)
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.SUBMITTED
    assert AuditLog.objects.filter(action="results.sheet_submitted").exists()


def test_scores_cannot_be_changed_after_submission(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    _fill_and_submit(client, sheet, [pupil], components)
    before = Score.objects.get(sheet=sheet, student=pupil, component=components[0]).value
    response = client.post(
        reverse("results:score", args=[sheet.pk]),
        {"student": pupil.pk, f"score_{components[0].pk}": "19"},
        follow=True,
    )
    messages = [str(m.message) for m in response.context["messages"]]
    assert any("draft sheet can be edited" in text for text in messages)
    assert Score.objects.get(sheet=sheet, student=pupil, component=components[0]).value == before


# --- the workflow buttons ---


def test_teacher_cannot_review_approve_or_publish(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    _fill_and_submit(client, sheet, [pupil], components)
    for action in ("review", "approve", "publish"):
        assert client.post(reverse(f"results:{action}", args=[sheet.pk])).status_code == 403
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.SUBMITTED


def test_admin_walks_the_workflow_to_published(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, pupil_two, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    _fill_and_submit(client, sheet, [pupil, pupil_two], components)
    admin = _manager_client(school_a)
    assert admin.post(reverse("results:review", args=[sheet.pk])).status_code == 302
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.REVIEWED
    admin.post(reverse("results:approve", args=[sheet.pk]))
    admin.post(reverse("results:publish", args=[sheet.pk]))
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.PUBLISHED
    assert AuditLog.objects.filter(action="results.sheet_published").exists()


def test_an_approved_sheet_cannot_be_sent_back(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    admin = _publish(client, school_a, [pupil], sheet, components)
    assert sheet.status == ResultSheet.Status.PUBLISHED
    response = admin.post(reverse("results:send_back", args=[sheet.pk]), follow=True)
    messages = [str(m.message) for m in response.context["messages"]]
    assert any("submitted or reviewed" in text.lower() for text in messages)
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.PUBLISHED


def test_a_published_sheet_links_to_report_cards(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    admin = _publish(client, school_a, [pupil], sheet, components)
    content = admin.get(reverse("results:sheet", args=[sheet.pk])).content
    assert b"Report card" in content


# --- the report card ---


def test_a_published_sheet_fills_the_report_card(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    admin = _publish(client, school_a, [pupil], sheet, components)
    url = reverse("results:report_card", args=[pupil.pk, period.pk])
    response = admin.get(url)
    assert response.status_code == 200
    content = response.content
    assert b"Mathematics" in content
    assert b"75.0" in content
    assert b"Needs improvement" in content  # grading scale legend


def test_the_report_card_ignores_unpublished_sheets(
    client, school_a, session, period, primary_three, section_a,
    maths, english, pupil, sheet, components, scale, assigned_teacher, login_as,
):
    login_as(school_a)
    url = reverse("results:report_card", args=[pupil.pk, period.pk])
    content = client.get(url).content
    assert b"Mathematics" not in content
    assert b"No results have been published" in content


def test_the_report_card_is_school_scoped(
    client, school_a, school_b, session, period, login_as,
):
    login_as(school_a)
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    session_b = AcademicSession.objects.create(
        school=school_b, name="2026/2027", is_current=True,
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    period_b = session_b.periods.create(
        school=school_b, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )
    foreign_pupil = Student.objects.create(
        school=school_b, first_name="Ngozi", last_name="Faraway", sex="female",
        date_of_birth=date(2018, 4, 4), admission_number="BET/2026/001",
        current_class=class_b,
    )
    assert client.get(
        reverse("results:report_card", args=[foreign_pupil.pk, period_b.pk])
    ).status_code == 404


def test_a_report_card_for_a_parent_is_refused(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, login_as,
):
    login_as(school_a, Role.PARENT)
    url = reverse("results:report_card", args=[pupil.pk, period.pk])
    assert client.get(url).status_code == 403


# --- the PDF report card ---


def test_the_published_report_card_downloads_as_a_pdf(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, scale, assigned_teacher,
):
    client.force_login(assigned_teacher.user)
    admin = _publish(client, school_a, [pupil], sheet, components)
    response = admin.get(reverse("results:report_card_pdf", args=[pupil.pk, period.pk]))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")  # a real PDF, not an error page
    assert ".pdf" in response["Content-Disposition"]
    assert response["Content-Disposition"].startswith("attachment")


def test_the_pdf_report_card_ignores_unpublished_results(
    client, school_a, session, period, primary_three, section_a,
    maths, pupil, sheet, components, login_as,
):
    login_as(school_a)
    response = client.get(reverse("results:report_card_pdf", args=[pupil.pk, period.pk]))
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_the_pdf_report_card_follows_the_same_access_rules(
    client, school_a, school_b, session, period, primary_three, section_a,
    maths, pupil, sheet, components, login_as,
):
    # a parent is refused
    login_as(school_a, Role.PARENT)
    assert client.get(
        reverse("results:report_card_pdf", args=[pupil.pk, period.pk])
    ).status_code == 403

    # a pupil from another school is never reached
    login_as(school_a)
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    stranger = Student.objects.create(
        school=school_b, first_name="Ngozi", last_name="Faraway", sex="female",
        date_of_birth=date(2018, 4, 4), admission_number="BET/2026/001",
        current_class=class_b,
    )
    assert client.get(
        reverse("results:report_card_pdf", args=[stranger.pk, period.pk])
    ).status_code == 404


# --- ranking, totals, attendance on the report card ---


def _fill_custom(client, sheet, values_by_pupil, components):
    """Save one row of scores per pupil with given component values."""
    for pupil, values in values_by_pupil.items():
        data = {"student": pupil.pk}
        for component, value in zip(components, values):
            data[f"score_{component.pk}"] = str(value)
        client.post(reverse("results:score", args=[sheet.pk]), data)


def _publish_custom(school_a, sheet, values_by_pupil, components):
    """As an admin: save the given scores and walk the workflow to published."""
    admin = _manager_client(school_a)
    _fill_custom(admin, sheet, values_by_pupil, components)
    admin.post(reverse("results:submit", args=[sheet.pk]))
    admin.post(reverse("results:review", args=[sheet.pk]))
    admin.post(reverse("results:approve", args=[sheet.pk]))
    admin.post(reverse("results:publish", args=[sheet.pk]))
    sheet.refresh_from_db()
    assert sheet.status == ResultSheet.Status.PUBLISHED
    return admin


def _published_context(school_a, make_request, pupil, period):
    from .views import _report_card_context

    request = make_request(school_a)
    return _report_card_context(request, pupil.pk, period.pk)


def test_ranking_ranks_subjects_by_percentage(
    client, school_a, session, period, scale, make_request,
):
    from .views import _report_card_context

    level = Level.objects.create(school=school_a, name="Primary", order=1)
    primary_three = SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 3", order=3,
    )
    section_a = Section.objects.create(
        school=school_a, school_class=primary_three, name="A",
    )
    subject = Subject.objects.create(school=school_a, name="Mathematics")
    ClassSubject.objects.create(
        school=school_a, school_class=primary_three, subject=subject,
    )
    sheet = ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section_a, subject=subject,
    )
    components = [
        AssessmentComponent.objects.create(
            school=school_a, session=session, name=name,
            max_score=Decimal(max_score), weight=Decimal(max_score),
        )
        for name, max_score in (("First Test", 20), ("Second Test", 20), ("Examination", 60))
    ]
    pupils = []
    for number, (first, last, values) in enumerate([
        ("Ada", "Top", (18, 18, 54)),      # 90, 1st
        ("Bisi", "Bold", (12, 15, 48)),    # 75, joint 2nd
        ("Chika", "Bold", (10, 20, 45)),   # 75, joint 2nd
        ("Dada", "Last", (10, 11, 40)),    # 61, 4th (ties share 2nd)
    ], start=1):
        pupils.append(
            Student.objects.create(
                school=school_a, first_name=first, last_name=last,
                sex="female", date_of_birth=date(2018, 3, 5),
                admission_number=f"FSS/2026/{number:03d}",
                current_class=primary_three, current_section=section_a,
            )
        )
    values_by_pupil = dict(zip(pupils, [(18, 18, 54), (12, 15, 48), (10, 20, 45), (10, 11, 40)]))
    school_a.show_ranking = True
    school_a.save()
    _publish_custom(school_a, sheet, values_by_pupil, components)

    for pupil, expected in zip(pupils, ["1st", "2nd", "2nd", "4th"]):
        context = _published_context(school_a, make_request, pupil, period)
        assert context["subject_rows"][0]["position"] == expected
        # with one subject the class position equals the subject position
        assert context["class_position"] == f"{expected} of 4"


def test_ranking_stays_hidden_when_the_school_has_it_off(
    client, school_a, session, period, scale, make_request,
):
    from .views import _report_card_context

    level = Level.objects.create(school=school_a, name="Primary", order=1)
    primary_three = SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 3", order=3,
    )
    section_a = Section.objects.create(
        school=school_a, school_class=primary_three, name="A",
    )
    subject = Subject.objects.create(school=school_a, name="Mathematics")
    ClassSubject.objects.create(
        school=school_a, school_class=primary_three, subject=subject,
    )
    sheet = ResultSheet.objects.create(
        school=school_a, period=period, school_class=primary_three,
        section=section_a, subject=subject,
    )
    components = [
        AssessmentComponent.objects.create(
            school=school_a, session=session, name=name,
            max_score=Decimal(max_score), weight=Decimal(max_score),
        )
        for name, max_score in (("First Test", 20), ("Second Test", 20), ("Examination", 60))
    ]
    pupils = [
        Student.objects.create(
            school=school_a, first_name=first, last_name=last,
            sex="female", date_of_birth=date(2018, 3, 5),
            admission_number=f"FSS/2026/{number:03d}",
            current_class=primary_three, current_section=section_a,
        )
        for number, (first, last) in enumerate(
            [("Ada", "Top"), ("Bisi", "Bold")], start=1
        )
    ]
    values_by_pupil = {
        pupils[0]: (18, 18, 54),
        pupils[1]: (12, 15, 48),
    }
    _publish_custom(school_a, sheet, values_by_pupil, components)

    context = _published_context(school_a, make_request, pupils[1], period)
    assert context["show_ranking"] is False
    assert all("position" not in row for row in context["subject_rows"])
    assert context["class_position"] is None


def test_report_card_totals_scores_per_published_subject(
    client, school_a, session, period, scale, make_request,
):
    from .views import _report_card_context

    level = Level.objects.create(school=school_a, name="Primary", order=1)
    primary_three = SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 3", order=3,
    )
    section_a = Section.objects.create(
        school=school_a, school_class=primary_three, name="A",
    )
    pupils = [
        Student.objects.create(
            school=school_a, first_name="Ada", last_name="Top", sex="female",
            date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
            current_class=primary_three, current_section=section_a,
        )
    ]
    components = [
        AssessmentComponent.objects.create(
            school=school_a, session=session, name=name,
            max_score=Decimal(max_score), weight=Decimal(max_score),
        )
        for name, max_score in (("First Test", 20), ("Second Test", 20), ("Examination", 60))
    ]
    made = []
    for name, values in (("Mathematics", (12, 15, 48)), ("English Studies", (14, 16, 55))):
        subject = Subject.objects.create(school=school_a, name=name)
        ClassSubject.objects.create(
            school=school_a, school_class=primary_three, subject=subject,
        )
        sheet = ResultSheet.objects.create(
            school=school_a, period=period, school_class=primary_three,
            section=section_a, subject=subject,
        )
        _publish_custom(
            school_a, sheet,
            {pupils[0]: (12, 15, 48) if name == "Mathematics" else (14, 16, 55)},
            components,
        )
        made.append(sheet)

    context = _published_context(school_a, make_request, pupils[0], period)
    # scoreboard math: 75 + 85 = 160 out of 100 + 100, average 80.0
    assert context["total_score"] == Decimal("160.00")
    assert context["total_max"] == Decimal("200")
    assert context["average"] == Decimal("80.0")


def test_report_card_counts_attendance_for_the_pupil(
    client, school_a, session, period, scale, make_request,
):
    from apps.attendance.models import AttendanceRecord, AttendanceSession
    from .views import _report_card_context

    level = Level.objects.create(school=school_a, name="Primary", order=1)
    primary_three = SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 3", order=3,
    )
    section_a = Section.objects.create(
        school=school_a, school_class=primary_three, name="A",
    )
    pupil = Student.objects.create(
        school=school_a, first_name="Ada", last_name="Top", sex="female",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three, current_section=section_a,
    )
    marked_by = make_request(school_a).membership
    attended = AttendanceRecord.Status.PRESENT
    absent = AttendanceRecord.Status.ABSENT
    for number, status in [(15, attended), (16, absent)]:
        register = AttendanceSession.objects.create(
            school=school_a, school_class=primary_three, section=section_a,
            date=date(2026, 9, number), session=period.session, period=period,
            marked_by=marked_by,
        )
        AttendanceRecord.objects.create(
            school=school_a, register=register, student=pupil, status=status,
        )
    # a register for another class never counts for this pupil
    other_class = SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 1", order=1,
    )
    AttendanceSession.objects.create(
        school=school_a, school_class=other_class,
        date=date(2026, 9, 17), session=period.session, period=period,
        marked_by=marked_by,
    )

    context = _published_context(school_a, make_request, pupil, period)
    assert context["attendance"] == {"present": 1, "days": 2}


def test_report_card_prefills_the_next_term_start_date(
    client, school_a, session, period, scale, make_request,
):
    from .views import _report_card_context

    level = Level.objects.create(school=school_a, name="Primary", order=1)
    primary_three = SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 3", order=3,
    )
    pupil = Student.objects.create(
        school=school_a, first_name="Ada", last_name="Top", sex="female",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three,
    )
    second_term = session.periods.create(
        school=school_a, name="Second Term", order=2,
        start_date=date(2027, 1, 11), end_date=date(2027, 4, 2),
    )
    context = _published_context(school_a, make_request, pupil, period)
    assert context["next_term"] == second_term
    assert context["next_term"].start_date == date(2027, 1, 11)
