"""Tests for the role dashboards (T14c): real data only, per role, with
tenant isolation and empty-school behaviour."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import AcademicSession
from apps.admissions.models import Applicant
from apps.announcements.models import Announcement
from apps.classes.models import Level, SchoolClass, Section
from apps.fees.models import FeeItem, Invoice, InvoiceItem, Payment
from apps.results.models import ResultSheet
from apps.schools.models import Membership, School
from apps.students.models import GuardianLink, Student
from apps.subjects.models import ClassSubject, Subject, TeacherAssignment
from apps.timetable.models import TimetableSlot

User = get_user_model()
Role = Membership.Role
pytestmark = pytest.mark.django_db


def make_user(username):
    return User.objects.create_user(username, password="S3cure-pass!")


def membership(user, school, role):
    return Membership.objects.create(user=user, school=school, role=role)


@pytest.fixture
def school_a():
    return School.objects.create(name="Alpha School", slug="alpha")


@pytest.fixture
def school_b():
    return School.objects.create(name="Beta School", slug="beta")


@pytest.fixture
def level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def klass(school_a, level):
    return SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 1", order=1,
    )


@pytest.fixture
def section_a(school_a, klass):
    return Section.objects.create(school=school_a, school_class=klass, name="A")


@pytest.fixture
def session(school_a):
    today = timezone.localdate()
    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", is_current=True,
        start_date=today - timedelta(days=90), end_date=today + timedelta(days=90),
    )


@pytest.fixture
def period(session, school_a):
    """The current term: dates always wrap today, whatever calendar day the
    checks run on."""
    today = timezone.localdate()
    return session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=today - timedelta(days=60), end_date=today + timedelta(days=30),
    )


def dashboard_url():
    return reverse("core:dashboard")


class TestManagerDashboard:
    def test_counts_real_data_and_role_key(self, client, school_a, session, period):
        owner = membership(make_user("owner1"), school_a, Role.OWNER)
        membership(make_user("t1"), school_a, Role.TEACHER)  # one TEACHER member
        pupil = Student.objects.create(
            school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
            date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        )
        pupil_two = Student.objects.create(
            school=school_a, first_name="Bisi", last_name="Adeyi", sex="female",
            date_of_birth=date(2018, 1, 20), admission_number="FSS/2026/002",
            status=Student.Status.GRADUATED,  # never counted as active
        )
        Applicant.objects.create(school=school_a, reference="APP-0001",
                                 first_name="S", last_name="O", sex="male",
                                 status=Applicant.Status.APPLIED)
        Applicant.objects.create(school=school_a, reference="APP-0002",
                                 first_name="T", last_name="U", sex="male",
                                 status=Applicant.Status.ADMITTED)  # not waiting
        fee_item = FeeItem.objects.create(school=school_a, session=session, name="Tuition")
        invoice = Invoice.objects.create(
            school=school_a, student=pupil, session=session, period=period,
            number="INV-0001", issue_date=date(2026, 9, 14), due_date=date(2026, 10, 14),
        )
        InvoiceItem.objects.create(school=school_a, invoice=invoice, fee_item=fee_item,
                                   description="Tuition", amount=Decimal("50000"))
        bursar_member = membership(make_user("b1"), school_a, Role.BURSAR)
        Payment.objects.create(school=school_a, invoice=invoice, amount=Decimal("20000"),
                               reference="RCPT-001", paid_on=date(2026, 9, 15),
                               received_by=bursar_member)

        client.force_login(owner.user)
        response = client.get(dashboard_url())

        assert response.status_code == 200
        context = response.context
        assert context["role_key"] == "manager"
        assert context["students"] == 1  # graduated excluded
        assert context["teachers"] == 1
        assert context["admissions_waiting"] == 1  # admitted excluded
        assert context["fees"]["expected"] == Decimal("50000")
        assert context["fees"]["collected"] == Decimal("20000")
        assert context["fees"]["outstanding"] == Decimal("30000")
        assert context["fees"]["rate"] == 40

    def test_other_schools_numbers_never_leak(self, client, school_a, school_b, session):
        """Tenant isolation: Beta's people and money never change Alpha's page."""
        owner = membership(make_user("owner-iso"), school_a, Role.OWNER)
        Student.objects.create(
            school=school_b, first_name="B", last_name="B", sex="male",
            date_of_birth=date(2018, 1, 1), admission_number="B/001",
        )
        membership(make_user("b-teacher"), school_b, Role.TEACHER)
        Applicant.objects.create(school=school_b, reference="APP-9000",
                                 first_name="B", last_name="B", sex="male",
                                 status=Applicant.Status.APPLIED)

        client.force_login(owner.user)
        response = client.get(dashboard_url())
        context = response.context
        assert context["students"] == 0
        assert context["teachers"] == 0
        assert context["admissions_waiting"] == 0
        assert "Beta School" not in response.content.decode()

    def test_notice_board_audience_rule(self, client, school_a):
        owner = membership(make_user("owner-notice"), school_a, Role.OWNER)
        author = owner
        Announcement.objects.create(
            school=school_a, title="Welcome back", body="Term starts.",
            audience=Announcement.Audience.EVERYONE, published_by=author,
        )
        Announcement.objects.create(
            school=school_a, title="Parents meeting", body="Friday.",
            audience=Announcement.Audience.PARENTS, published_by=author,
        )
        Announcement.objects.create(
            school=school_a, title="Old notice", body="Gone.",
            audience=Announcement.Audience.EVERYONE, published_by=author,
            is_active=False,  # archived: never shown
        )
        client.force_login(owner.user)
        response = client.get(dashboard_url())
        assert "Welcome back" in response.content.decode()
        assert "Parents meeting" in response.content.decode()  # manager sees all
        assert "Old notice" not in response.content.decode()


class TestEmptySchool:
    def test_manager_without_session_still_renders(self, client, school_a):
        owner = membership(make_user("owner-empty"), school_a, Role.OWNER)
        client.force_login(owner.user)
        response = client.get(dashboard_url())
        assert response.status_code == 200
        context = response.context
        assert context["period"] is None
        assert context["students"] == 0
        assert context["fees"]["expected"] == Decimal("0")
        assert "No term is marked current" in response.content.decode()


class TestBursarDashboard:
    def test_money_and_recent_payments(self, client, school_a, session, period):
        bursar = membership(make_user("bursar1"), school_a, Role.BURSAR)
        level = Level.objects.create(school=school_a, name="Primary", order=1)
        klass = SchoolClass.objects.create(school=school_a, level=level, name="Primary 1", order=1)
        pupil = Student.objects.create(
            school=school_a, first_name="Ada", last_name="Eze", sex="female",
            date_of_birth=date(2018, 2, 2), admission_number="FSS/2026/010",
            current_class=klass,
        )
        fee_item = FeeItem.objects.create(school=school_a, session=session, name="Tuition")
        invoice = Invoice.objects.create(
            school=school_a, student=pupil, session=session, period=period,
            number="INV-0002", issue_date=date(2026, 9, 14), due_date=date(2026, 10, 14),
        )
        InvoiceItem.objects.create(school=school_a, invoice=invoice, fee_item=fee_item,
                                   description="Tuition", amount=Decimal("30000"))
        payment = Payment.objects.create(
            school=school_a, invoice=invoice, amount=Decimal("10000"), method=Payment.Method.CASH,
            reference="RCPT-002", paid_on=date(2026, 9, 16), received_by=bursar,
        )

        client.force_login(bursar.user)
        response = client.get(dashboard_url())
        context = response.context
        assert context["role_key"] == "bursar"
        assert context["fees"]["expected"] == Decimal("30000")
        assert [p.reference for p in context["payments"]] == [payment.reference]
        assert context["payments"][0].amount == Decimal("10000")
        # Bursar does not get the manager blocks
        assert "Active students" not in response.content.decode()

    def test_recent_payments_are_the_current_terms_only(
        self, client, school_a, session, period,
    ):
        bursar = membership(make_user("bursar-t2"), school_a, Role.BURSAR)
        pupil = Student.objects.create(
            school=school_a, first_name="Ada", last_name="Eze", sex="female",
            date_of_birth=date(2018, 2, 2), admission_number="FSS/2026/011",
        )
        fee_item = FeeItem.objects.create(school=school_a, session=session, name="Tuition 2")
        later = session.periods.create(
            school=school_a, name="Second Term", order=2,
            start_date=timezone.localdate() + timedelta(days=40),
            end_date=timezone.localdate() + timedelta(days=80),
        )
        old = Invoice.objects.create(
            school=school_a, student=pupil, session=session, period=later,
            number="INV-9000",
            issue_date=later.start_date, due_date=later.start_date + timedelta(days=30),
        )
        InvoiceItem.objects.create(school=school_a, invoice=old, fee_item=fee_item,
                                   description="Tuition", amount=Decimal("9000"))
        Payment.objects.create(school=school_a, invoice=old, amount=Decimal("9000"),
                               reference="RCPT-8000", paid_on=later.start_date,
                               received_by=bursar)

        client.force_login(bursar.user)
        response = client.get(dashboard_url())
        references = [p.reference for p in response.context["payments"]]
        assert references == []  # old term never shows


class TestTeacherDashboard:
    @pytest.fixture
    def teacher(self, school_a):
        return membership(make_user("teacher-dash"), school_a, Role.TEACHER)

    @pytest.fixture
    def maths(self, school_a, klass):
        subject = Subject.objects.create(school=school_a, name="Mathematics")
        ClassSubject.objects.create(school=school_a, school_class=klass, subject=subject)
        return subject

    def test_today_periods_and_draft_sheets(self, client, school_a, klass, section_a,
                                            session, period, teacher, maths):
        weekday = timezone.localdate().isoweekday()
        other_weekday = 7 if weekday != 7 else 1
        today_period = TimetableSlot.objects.create(
            school=school_a, session=session, school_class=klass, subject=maths,
            day=weekday, starts_at="09:00", ends_at="09:40",
        )
        TimetableSlot.objects.create(  # another day never shows as today
            school=school_a, session=session, school_class=klass, subject=maths,
            day=other_weekday, starts_at="10:00", ends_at="10:40",
        )
        TimetableSlot.objects.create(  # a break slot is not my period
            school=school_a, session=session, school_class=klass, subject=None,
            label="Assembly", day=weekday, starts_at="08:00", ends_at="08:20",
        )
        TeacherAssignment.objects.create(
            school=school_a, session=session, school_class=klass,
            subject=maths, teacher=teacher,
        )
        my_sheet = ResultSheet.objects.create(
            school=school_a, period=period, school_class=klass, subject=maths,
        )
        section_b = Section.objects.create(school=school_a, school_class=klass, name="B")
        ResultSheet.objects.create(  # already published: nothing left to fill
            school=school_a, period=period, school_class=klass, section=section_b,
            subject=maths, status=ResultSheet.Status.PUBLISHED, submitted_by=teacher,
        )
        english = Subject.objects.create(school=school_a, name="English Studies")
        ClassSubject.objects.create(school=school_a, school_class=klass, subject=english)
        ResultSheet.objects.create(  # not my subject
            school=school_a, period=period, school_class=klass, subject=english,
        )

        client.force_login(teacher.user)
        response = client.get(dashboard_url())
        context = response.context
        assert context["role_key"] == "teacher"
        assert [s.pk for s in context["periods_today"]] == [today_period.pk]
        assert [s.pk for s in context["draft_sheets"]] == [my_sheet.pk]

    def test_school_b_teacher_sees_nothing_from_school_a(
        self, client, school_a, school_b, klass, section_a, session, period,
    ):
        maths = Subject.objects.create(school=school_a, name="Mathematics")
        ClassSubject.objects.create(school=school_a, school_class=klass, subject=maths)
        TimetableSlot.objects.create(
            school=school_a, session=session, school_class=klass, subject=maths,
            day=timezone.localdate().isoweekday(), starts_at="09:00", ends_at="09:40",
        )
        ResultSheet.objects.create(
            school=school_a, period=period, school_class=klass, subject=maths,
        )
        teacher_b = membership(make_user("teacher-b"), school_b, Role.TEACHER)
        session_b = AcademicSession.objects.create(
            school=school_b, name="2026/2027", is_current=True,
            start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
        )
        period_b = session_b.periods.create(
            school=school_b, name="First Term", order=1,
            start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
        )
        class_b = SchoolClass.objects.create(
            school=school_b,
            level=Level.objects.create(school=school_b, name="Primary", order=1),
            name="Primary 1", order=1,
        )
        maths_b = Subject.objects.create(school=school_b, name="Mathematics")
        ClassSubject.objects.create(school=school_b, school_class=class_b, subject=maths_b)
        TeacherAssignment.objects.create(
            school=school_b, session=session_b, school_class=class_b,
            subject=maths_b, teacher=teacher_b,
        )
        ResultSheet.objects.create(
            school=school_b, period=period_b, school_class=class_b, subject=maths_b,
        )

        client.force_login(teacher_b.user)
        response = client.get(dashboard_url())
        context = response.context
        assert len(context["periods_today"]) == 0  # Alpha's slot is not Beta's
        assert len(context["draft_sheets"]) == 1    # own sheet only
        assert context["draft_sheets"][0].school_id == school_b.pk


class TestParentDashboard:
    def test_children_with_owed_fees_and_notices(self, client, school_a, session, period):
        parent = membership(make_user("parent-dash"), school_a, Role.PARENT)
        author = membership(make_user("owner-parent"), school_a, Role.OWNER)
        level = Level.objects.create(school=school_a, name="Primary", order=1)
        klass = SchoolClass.objects.create(school=school_a, level=level, name="Primary 2", order=2)
        child = Student.objects.create(
            school=school_a, first_name="Ngo", last_name="Bala", sex="female",
            date_of_birth=date(2019, 4, 4), admission_number="FSS/2026/020",
            current_class=klass,
        )
        withdrawn = Student.objects.create(  # linked, but withdrawn: parents still see it
            school=school_a, first_name="Sey", last_name="Bala", sex="male",
            date_of_birth=date(2015, 6, 6), admission_number="FSS/2024/030",
            current_class=klass, status=Student.Status.WITHDRAWN,
        )
        GuardianLink.objects.create(school=school_a, student=child, guardian=parent)
        GuardianLink.objects.create(school=school_a, student=withdrawn, guardian=parent)
        fee_item = FeeItem.objects.create(school=school_a, session=session, name="Tuition")
        invoice = Invoice.objects.create(
            school=school_a, student=child, session=session, period=period,
            number="INV-0003", issue_date=date(2026, 9, 14), due_date=date(2026, 10, 14),
        )
        InvoiceItem.objects.create(school=school_a, invoice=invoice, fee_item=fee_item,
                                   description="Tuition", amount=Decimal("25000"))
        bursar = membership(make_user("bursar-parent"), school_a, Role.BURSAR)
        Payment.objects.create(school=school_a, invoice=invoice, amount=Decimal("10000"),
                               reference="RCPT-003", paid_on=date(2026, 9, 20),
                               received_by=bursar)
        Announcement.objects.create(
            school=school_a, title="PTA day", body="Come one, come all.",
            audience=Announcement.Audience.PARENTS, published_by=author,
        )
        Announcement.objects.create(
            school=school_a, title="Staff only", body="You cannot see me.",
            audience=Announcement.Audience.STAFF, published_by=author,
        )

        client.force_login(parent.user)
        response = client.get(dashboard_url())
        context = response.context
        assert context["role_key"] == "parent"
        rows = context["children"]
        assert len(rows) == 2
        by_name = {row["pupil"].first_name: row for row in rows}
        assert by_name["Ngo"]["owed"] == Decimal("15000")  # 25000 - 10000
        assert bursar.school == school_a
        content = response.content.decode()
        assert "PTA day" in content
        assert "Staff only" not in content
        assert "Ngo" in content

    def test_not_linked_child_is_never_listed(self, client, school_a):
        """Tenant/id safety: a parent card never appears for another school's pupil."""
        parent = membership(make_user("parent-alone"), school_a, Role.PARENT)
        school_b = School.objects.create(name="Gamma School", slug="gamma")
        other = Student.objects.create(
            school=school_b, first_name="Kola", last_name="Notlinked", sex="male",
            date_of_birth=date(2019, 1, 1), admission_number="G/001",
        )
        client.force_login(parent.user)
        response = client.get(dashboard_url())
        assert other.first_name not in response.content.decode()
        assert response.context["children"] == []
