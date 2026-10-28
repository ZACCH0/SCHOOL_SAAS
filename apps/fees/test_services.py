import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.academics.models import AcademicSession
from apps.classes.models import Level, SchoolClass
from apps.audit.models import AuditLog
from apps.fees.models import FeeItem, FeeItemPrice, Invoice, InvoiceItem, Payment
from apps.fees.services import create_fee_item, generate_invoices, record_payment, set_price
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
def pupils(school_a, primary_three):
    return [
        Student.objects.create(
            school=school_a, first_name=f"Pupil{i}", last_name="Test", sex="male",
            date_of_birth=date(2018, 1, 1), admission_number=f"FSS/2026/{i:03d}",
            current_class=primary_three,
        )
        for i in range(3)
    ]


@pytest.fixture
def manager(school_a, make_member):
    return make_member(school_a, role=Role.ADMIN)


@pytest.fixture
def bursar(school_a, make_member):
    return make_member(school_a, role=Role.BURSAR)


@pytest.fixture
def fees(school_a, session, primary_three, manager, make_request):
    tuition = create_fee_item(make_request(school_a, Role.ADMIN, member=manager), session, "Tuition", "per_term")
    set_price(make_request(school_a, Role.ADMIN, member=manager), tuition, primary_three, Decimal("90000"))
    return tuition


@pytest.mark.django_db
def test_only_managers_can_change_the_fee_structure(school_a, session, bursar, make_request):
    with pytest.raises(PermissionDenied):
        create_fee_item(make_request(school_a, Role.BURSAR, member=bursar), session, "Tuition", "per_term")
    assert not FeeItem.objects.exists()


@pytest.mark.django_db
def test_fee_item_name_must_be_unique_in_a_session(school_a, session, manager, make_request):
    create_fee_item(make_request(school_a, Role.ADMIN, member=manager), session, "Tuition", "per_term")
    with pytest.raises(ValidationError):
        create_fee_item(make_request(school_a, Role.ADMIN, member=manager), session, "tuition", "per_term")


@pytest.mark.django_db
def test_generate_invoices_charges_every_active_pupil_once(school_a, session, period, pupils, fees, manager, make_request):
    request = make_request(school_a, Role.ADMIN, member=manager)
    result = generate_invoices(request, period)
    assert result["created"] == 3
    assert result["skipped"] == 0
    again = generate_invoices(request, period)
    assert again["created"] == 0
    assert Invoice.objects.count() == 3
    inv = Invoice.objects.first()
    assert inv.number == "INV-0001" or inv.number.startswith("INV-")
    assert inv.items.count() == 1
    assert inv.total == Decimal("90000")
    assert inv.due_date == period.end_date
    assert AuditLog.objects.filter(action="fees.invoices_generated").exists()


@pytest.mark.django_db
def test_per_session_items_only_appear_in_the_first_term(school_a, session, period, pupils, manager, make_request):
    request = make_request(school_a, Role.ADMIN, member=manager)
    books = create_fee_item(request, session, "Books", "per_session")
    set_price(request, books, SchoolClass.objects.get(pk=_cls_id(pupils)), Decimal("10000"))
    period2 = session.periods.create(
        school=school_a, name="Second Term", order=2,
        start_date=date(2027, 1, 11), end_date=date(2027, 4, 2),
    )
    generate_invoices(request, period)
    generate_invoices(request, period2)
    first = Invoice.objects.filter(period=period).first()
    second = Invoice.objects.filter(period=period2).first()
    assert first is not None and second is None
    assert first.items.filter(description__startswith="Books").exists()


@pytest.mark.django_db
def test_optional_items_are_never_auto_invoiced(school_a, session, period, pupils, manager, make_request, primary_three):
    request = make_request(school_a, Role.ADMIN, member=manager)
    transport = create_fee_item(request, session, "Transport", "optional")
    set_price(request, transport, primary_three, Decimal("5000"))
    result = generate_invoices(request, period)
    assert result["created"] == 0
    assert result["skipped"] == 3
    assert not InvoiceItem.objects.filter(description__startswith="Transport").exists()


@pytest.mark.django_db
def test_students_without_a_price_for_a_class_are_skipped(school_a, session, period, pupils, manager, make_request):
    request = make_request(school_a, Role.ADMIN, member=manager)
    create_fee_item(request, session, "Tuition", "per_term")  # no price set
    result = generate_invoices(request, period)
    assert result["created"] == 0
    assert result["skipped"] == 3


def _cls_id(pupils):
    return pupils[0].current_class_id


@pytest.mark.django_db
def test_record_payment_sets_part_paid_then_paid(school_a, session, period, pupils, fees, manager, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=manager), period)
    inv = Invoice.objects.first()
    request = make_request(school_a, Role.BURSAR, member=bursar)

    pay, created = record_payment(request, inv, "40000", "cash", "RCP-1", TODAY)
    assert created
    inv.refresh_from_db()
    assert inv.status == Invoice.Status.PART_PAID
    assert inv.balance == Decimal("50000")

    pay2, created2 = record_payment(request, inv, "50000", "transfer", "RCP-2", TODAY)
    inv.refresh_from_db()
    assert created2 and inv.status == Invoice.Status.PAID
    assert inv.balance == 0
    assert AuditLog.objects.filter(action="fees.payment_recorded").count() == 2


@pytest.mark.django_db
def test_same_reference_returns_the_same_payment(school_a, session, period, pupils, fees, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=bursar), period)
    inv = Invoice.objects.first()
    request = make_request(school_a, Role.BURSAR, member=bursar)
    first, created1 = record_payment(request, inv, "40000", "cash", "RCP-9", TODAY)
    second, created2 = record_payment(request, inv, "40000", "cash", "RCP-9", TODAY)
    assert created1 and not created2
    assert first == second
    assert Payment.objects.count() == 1
    assert inv.payments.count() == 1


@pytest.mark.django_db
def test_cannot_overpay_an_invoice(school_a, session, period, pupils, fees, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=bursar), period)
    inv = Invoice.objects.first()
    request = make_request(school_a, Role.BURSAR, member=bursar)
    with pytest.raises(ValidationError):
        record_payment(request, inv, "95000", "cash", "RCP-3", TODAY)
    assert not Payment.objects.exists()


@pytest.mark.django_db
def test_fully_paid_invoice_cannot_take_more_money(school_a, session, period, pupils, fees, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=bursar), period)
    inv = Invoice.objects.first()
    request = make_request(school_a, Role.BURSAR, member=bursar)
    record_payment(request, inv, "90000", "cash", "RCP-4", TODAY)
    with pytest.raises(ValidationError):
        record_payment(request, inv, "1000", "cash", "RCP-5", TODAY)


@pytest.mark.django_db
def test_payment_date_cannot_be_in_the_future(school_a, session, period, pupils, fees, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=bursar), period)
    inv = Invoice.objects.first()
    request = make_request(school_a, Role.BURSAR, member=bursar)
    with pytest.raises(ValidationError):
        record_payment(request, inv, "1000", "cash", "RCP-6", timezone.localdate() + timedelta(days=2))


@pytest.mark.django_db
def test_a_reference_is_required(school_a, session, period, pupils, fees, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=bursar), period)
    inv = Invoice.objects.first()
    request = make_request(school_a, Role.BURSAR, member=bursar)
    with pytest.raises(ValidationError):
        record_payment(request, inv, "1000", "cash", "  ", TODAY)


@pytest.mark.django_db
def test_bursar_of_another_school_is_refused(school_a, school_b, session, period, pupils, fees, make_member, make_request):
    bursar_b = make_member(school_b, role=Role.BURSAR)
    generate_invoices(make_request(school_a, Role.ADMIN, member=make_member(school_a, role=Role.ADMIN)), period)
    inv = Invoice.objects.first()
    with pytest.raises(PermissionDenied):
        record_payment(make_request(school_b, Role.BURSAR, member=bursar_b), inv, "1000", "cash", "RCP-7", TODAY)
    assert not Payment.objects.exists()
