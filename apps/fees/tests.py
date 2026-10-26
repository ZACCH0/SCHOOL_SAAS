import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academics.models import AcademicSession
from apps.classes.models import Level, SchoolClass
from apps.fees.models import FeeItem, FeeItemPrice, Invoice, InvoiceItem, Payment
from apps.schools.models import Membership
from apps.students.models import Student

Role = Membership.Role
TODAY = date(2026, 10, 26)


@pytest.fixture
def school_level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_three(school_a, school_level):
    return SchoolClass.objects.create(school=school_a, level=school_level, name="Primary 3", order=3)


@pytest.fixture
def session(school_a):
    return AcademicSession.objects.create(
        school=school_a, name="2026/2027", is_current=True,
        start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )


@pytest.fixture
def period(school_a, session):
    return session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )


@pytest.fixture
def pupil(school_a, primary_three):
    return Student.objects.create(
        school=school_a, first_name="Ade", last_name="Ogunlesi", sex="male",
        date_of_birth=date(2018, 3, 5), admission_number="FSS/2026/001",
        current_class=primary_three,
    )


@pytest.fixture
def fee_item(school_a, session):
    return FeeItem.objects.create(school=school_a, session=session, name="Tuition")


@pytest.fixture
def bursar_a(school_a):
    user = get_user_model().objects.create_user(username="bursar-a", password="x")
    return Membership.objects.create(school=school_a, user=user, role=Role.BURSAR)


def make_invoice(school, student, session, period, number="INV-0001", due=None, issue=None):
    return Invoice.objects.create(
        school=school, student=student, session=session, period=period,
        number=number, issue_date=issue or date(2026, 9, 20),
        due_date=due or date(2026, 10, 1),
    )


@pytest.mark.django_db
def test_fee_item_price_cannot_mix_schools(school_a, school_b, fee_item):
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    price = FeeItemPrice(school=school_b, fee_item=fee_item, school_class=class_b, amount=Decimal("1000"))
    with pytest.raises(ValidationError):
        price.full_clean()


@pytest.mark.django_db
def test_price_amount_must_be_positive(school_a, primary_three, fee_item):
    price = FeeItemPrice(school=school_a, fee_item=fee_item, school_class=primary_three, amount=Decimal("0"))
    with pytest.raises(ValidationError):
        price.full_clean()


@pytest.mark.django_db
def test_invoice_cannot_mix_school_records(school_a, school_b, period, primary_three):
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 3", order=3)
    pupil_b = Student.objects.create(
        school=school_b, first_name="Ada", last_name="Bello", sex="female",
        date_of_birth=date(2018, 1, 1), admission_number="BB/2026/001", current_class=class_b,
    )
    session_b = AcademicSession.objects.create(
        school=school_b, name="2026/2027", start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    period_b = session_b.periods.create(
        school=school_b, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )
    inv = Invoice(
        school=school_a, student=pupil_b, session=session_b, period=period_b,
        number="INV-X", issue_date=TODAY, due_date=TODAY,
    )
    with pytest.raises(ValidationError):
        inv.full_clean()


@pytest.mark.django_db
def test_period_must_belong_to_the_invoices_session(school_a, pupil, session):
    other_session = AcademicSession.objects.create(
        school=school_a, name="2025/2026", start_date=date(2025, 9, 1), end_date=date(2026, 7, 31),
    )
    other_period = other_session.periods.create(
        school=school_a, name="First Term", order=1,
        start_date=date(2025, 9, 8), end_date=date(2025, 12, 12),
    )
    inv = Invoice(
        school=school_a, student=pupil, session=session, period=other_period,
        number="INV-X", issue_date=TODAY, due_date=TODAY,
    )
    with pytest.raises(ValidationError):
        inv.full_clean()


@pytest.mark.django_db
def test_totals_balance_and_overdue(school_a, pupil, session, period, fee_item, bursar_a):
    inv = make_invoice(school_a, pupil, session, period)
    InvoiceItem.objects.create(school=school_a, invoice=inv, fee_item=fee_item, description="Tuition", amount=Decimal("90000"))
    InvoiceItem.objects.create(school=school_a, invoice=inv, fee_item=fee_item, description="Books", amount=Decimal("10000"))
    assert inv.total == Decimal("100000")
    assert inv.balance == Decimal("100000")
    assert inv.is_overdue

    Payment.objects.create(
        school=school_a, invoice=inv, amount=Decimal("40000"), method=Payment.Method.TRANSFER,
        reference="TRF-001", paid_on=TODAY, received_by=bursar_a,
    )
    assert inv.paid == Decimal("40000")
    assert inv.balance == Decimal("60000")
    assert inv.is_overdue


@pytest.mark.django_db
def test_paid_status_invoice_is_not_overdue(school_a, pupil, session, period, fee_item, bursar_a):
    inv = make_invoice(school_a, pupil, session, period)
    InvoiceItem.objects.create(school=school_a, invoice=inv, fee_item=fee_item, description="Tuition", amount=Decimal("90000"))
    Payment.objects.create(
        school=school_a, invoice=inv, amount=Decimal("90000"), paid_on=TODAY,
        reference="TRF-002", received_by=bursar_a,
    )
    inv.status = Invoice.Status.PAID
    inv.save(update_fields=["status"])
    assert not inv.is_overdue


@pytest.mark.django_db
def test_payment_reference_must_be_unique_per_school(school_a, pupil, session, period, bursar_a):
    inv = make_invoice(school_a, pupil, session, period)
    Payment.objects.create(
        school=school_a, invoice=inv, amount=Decimal("100"), paid_on=TODAY,
        reference="TRF-1", received_by=bursar_a,
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Payment.objects.create(
                school=school_a, invoice=inv, amount=Decimal("100"), paid_on=TODAY,
                reference="trf-1", received_by=bursar_a,
            )


@pytest.mark.django_db
def test_payment_reference_can_repeat_across_schools(school_a, school_b, pupil, session, period, bursar_a):
    inv_a = make_invoice(school_a, pupil, session, period)
    Payment.objects.create(
        school=school_a, invoice=inv_a, amount=Decimal("100"), paid_on=TODAY,
        reference="TRF-9", received_by=bursar_a,
    )
    level_b = Level.objects.create(school=school_b, name="Primary", order=1)
    class_b = SchoolClass.objects.create(school=school_b, level=level_b, name="Primary 1", order=1)
    pupil_b = Student.objects.create(
        school=school_b, first_name="Ada", last_name="Bello", sex="female",
        date_of_birth=date(2018, 1, 1), admission_number="BB/2026/001", current_class=class_b,
    )
    session_b = AcademicSession.objects.create(
        school=school_b, name="2026/2027", start_date=date(2026, 9, 1), end_date=date(2027, 7, 31),
    )
    period_b = session_b.periods.create(
        school=school_b, name="First Term", order=1,
        start_date=date(2026, 9, 14), end_date=date(2026, 12, 18),
    )
    inv_b = make_invoice(school_b, pupil_b, session_b, period_b)
    bursar_b_user = get_user_model().objects.create_user(username="bursar-b", password="x")
    bursar_b = Membership.objects.create(school=school_b, user=bursar_b_user, role=Role.BURSAR)
    Payment.objects.create(
        school=school_b, invoice=inv_b, amount=Decimal("100"), paid_on=TODAY,
        reference="TRF-9", received_by=bursar_b,
    )
    assert inv_b.payments.count() == 1


@pytest.mark.django_db
def test_payment_amount_must_be_positive(school_a, pupil, session, period, bursar_a):
    inv = make_invoice(school_a, pupil, session, period)
    pay = Payment(school=school_a, invoice=inv, amount=Decimal("0"), paid_on=TODAY, reference="TRF-3", received_by=bursar_a)
    with pytest.raises(ValidationError):
        pay.full_clean()
