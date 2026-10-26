import pytest
from datetime import date
from decimal import Decimal

from apps.classes.models import Level, SchoolClass
from apps.fees.models import FeeItem, FeeItemPrice, Invoice, InvoiceItem, Payment
from apps.fees.services import create_fee_item, generate_invoices, set_price
from apps.schools.models import Membership
from apps.students.models import Student

from django.urls import reverse

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
    return AcademicSession_create(school_a)


def AcademicSession_create(school):
    from apps.academics.models import AcademicSession

    return AcademicSession.objects.create(
        school=school, name="2026/2027", is_current=True,
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
def fee_structure(school_a, session, primary_three, manager, make_request):
    request = make_request(school_a, Role.ADMIN, member=manager)
    tuition = create_fee_item(request, session, "Tuition", "per_term")
    set_price(request, tuition, primary_three, Decimal("90000"))
    return tuition


@pytest.fixture
def manager(school_a, make_member):
    return make_member(school_a, role=Role.ADMIN)


@pytest.fixture
def bursar(school_a, make_member):
    return make_member(school_a, role=Role.BURSAR)


@pytest.fixture
def invoices(school_a, session, period, pupil, fee_structure, bursar, make_request):
    generate_invoices(make_request(school_a, Role.ADMIN, member=bursar), period)


@pytest.mark.django_db
def test_parent_cannot_see_any_fees_page(client, school_a, pupil, manager, invoices):
    parent_user = _user_with_role(school_a, Role.PARENT)
    client.force_login(parent_user)
    for url in ("fees:home", "fees:structure", "fees:invoice_list", "fees:payment_list"):
        response = client.get(reverse(url), SERVER_NAME="localhost")
        assert response.status_code == 403, url


@pytest.mark.django_db
def test_teacher_cannot_see_any_fees_page(client, school_a, invoices):
    teacher_user = _user_with_role(school_a, Role.TEACHER)
    client.force_login(teacher_user)
    response = client.get(reverse("fees:home"), SERVER_NAME="localhost")
    assert response.status_code == 403


@pytest.mark.django_db
def test_bursar_sees_overview_with_real_totals(client, school_a, period, invoices):
    client.force_login(_user_with_role(school_a, Role.BURSAR))
    response = client.get(reverse("fees:home"), SERVER_NAME="localhost")
    content = response.content.decode()
    assert response.status_code == 200
    assert "90,000" in content and "Primary 3" in content
    assert "0" in content  # collected so far


@pytest.mark.django_db
def test_structure_adds_item_and_price(client, school_a, session, primary_three, manager):
    client.force_login(_user_with_role(school_a, Role.ADMIN))
    response = client.post(
        reverse("fees:item_add"), {"name": "Books", "charged": "per_session"}, SERVER_NAME="localhost"
    )
    assert response.status_code == 302
    response = client.post(
        reverse("fees:price_set"),
        {"fee_item": FeeItem.objects.get(name="Books").pk, "school_class": primary_three.pk, "amount": "10000"},
        follow=True, SERVER_NAME="localhost",
    )
    assert FeeItemPrice.objects.filter(amount=Decimal("10000")).exists()


@pytest.mark.django_db
def test_generate_and_record_payment_through_the_ui(client, school_a, period, pupil, fee_structure, bursar, manager):
    bursar_user = _user_with_role(school_a, Role.BURSAR)
    client.force_login(bursar_user)
    response = client.post(reverse("fees:generate"), follow=True, SERVER_NAME="localhost")
    assert Invoice.objects.count() == 1
    invoice = Invoice.objects.first()

    response = client.post(
        reverse("fees:pay", args=[invoice.pk]),
        {"amount": "40000", "method": "cash", "reference": "RCP-100", "paid_on": TODAY.isoformat(), "note": ""},
        SERVER_NAME="localhost",
    )
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PART_PAID

    response = client.post(
        reverse("fees:pay", args=[invoice.pk]),
        {"amount": "40000", "method": "cash", "reference": "RCP-100", "paid_on": TODAY.isoformat(), "note": ""},
        follow=True, SERVER_NAME="localhost",
    )
    assert Payment.objects.count() == 1
    assert "already recorded" in response.content.decode()

    client.post(
        reverse("fees:pay", args=[invoice.pk]),
        {"amount": "50000", "method": "transfer", "reference": "RCP-101", "paid_on": TODAY.isoformat(), "note": ""},
        SERVER_NAME="localhost",
    )
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID


@pytest.mark.django_db
def test_invoice_of_another_school_returns_404(client, school_a, school_b, period, pupil, fee_structure, make_member, make_request):
    owner_b = make_member(school_b, role=Role.OWNER)
    admin_a = make_member(school_a, role=Role.ADMIN)
    generate_invoices(make_request(school_a, Role.ADMIN, member=admin_a), period)
    invoice = Invoice.objects.first()
    client.force_login(owner_b.user)
    response = client.get(reverse("fees:invoice_detail", args=[invoice.pk]), SERVER_NAME="localhost")
    assert response.status_code == 404


@pytest.mark.django_db
def test_receipt_shows_previous_and_remaining_balance(client, school_a, period, pupil, fee_structure, bursar):
    bursar_user = _user_with_role(school_a, Role.BURSAR)
    client.force_login(bursar_user)
    client.post(reverse("fees:generate"), follow=True, SERVER_NAME="localhost")
    invoice = Invoice.objects.first()
    client.post(
        reverse("fees:pay", args=[invoice.pk]),
        {"amount": "30000", "method": "cash", "reference": "RCP-7", "paid_on": TODAY.isoformat(), "note": ""},
        SERVER_NAME="localhost",
    )
    from apps.fees.models import Payment

    payment = Payment.objects.get(reference="RCP-7")
    response = client.get(reverse("fees:receipt", args=[payment.pk]), SERVER_NAME="localhost")
    content = response.content.decode()
    assert "90,000" in content and "60,000" in content and "30,000" in content


def _user_with_role(school, role):
    from django.contrib.auth import get_user_model

    from apps.schools.models import Membership as M

    user, _ = get_user_model().objects.get_or_create(username=f"u-{role.value}")
    M.objects.get_or_create(school=school, user=user, role=role)
    return user
