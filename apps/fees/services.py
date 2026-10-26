from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academics.models import AcademicPeriod
from apps.audit.services import record
from apps.classes.models import SchoolClass
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain
from apps.students.models import Student

from .models import FeeItem, FeeItemPrice, Invoice, InvoiceItem, Payment

FINANCE_ROLES = (
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BURSAR,
)


def _text(exc):
    return " ".join(exc.messages)


def create_fee_item(request, session, name, charged):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, session)
    item = FeeItem(school=request.school, session=session, name=name.strip(), charged=charged)
    try:
        item.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    save_or_explain(item, "A fee item with that name already exists for this session.")
    record(request, "fees.fee_item_created", target=item, name=item.name, charged=item.charged)
    return item


def set_price(request, fee_item, school_class, amount):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, fee_item, school_class)
    try:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValidationError("Enter a valid amount.") from exc
    price, _created = FeeItemPrice.objects.update_or_create(
        fee_item=fee_item,
        school_class=school_class,
        defaults={"amount": amount, "school": request.school},
    )
    try:
        price.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    record(
        request, "fees.price_set", target=price,
        fee_item=fee_item.name, school_class=school_class.name, amount=str(amount),
    )
    return price


def _next_invoice_number(school):
    last = Invoice.objects.for_school(school).order_by("-id").first()
    if last is None:
        return "INV-0001"
    tail = last.number.rsplit("-", 1)[-1]
    return f"INV-{int(tail) + 1:04d}" if tail.isdigit() else f"INV-{Invoice.objects.for_school(school).count() + 1:04d}"


@transaction.atomic
def generate_invoices(request, period, school_class=None):
    """Create one invoice per active student for the term. Per-session fee items
    are only charged in the session's first term. Idempotent: students who
    already have an invoice for the term are skipped."""
    require_role(request, FINANCE_ROLES)
    ensure_owned(request, period)
    if school_class is not None:
        ensure_owned(request, school_class)

    session = period.session
    first_period = session.periods.order_by("start_date", "id").first()
    students = Student.objects.for_school(request.school).filter(
        status=Student.Status.ACTIVE
    )
    if school_class is not None:
        students = students.filter(current_class=school_class)
    students = students.select_related("current_class")

    fee_items = list(FeeItem.objects.for_school(request.school).filter(session=session))
    prices = {
        (p.fee_item_id, p.school_class_id): p.amount
        for p in FeeItemPrice.objects.for_school(request.school).filter(
            fee_item__in=fee_items
        )
    }

    existing = set(
        Invoice.objects.for_school(request.school).filter(period=period).values_list(
            "student_id", flat=True
        )
    )

    created = 0
    skipped_no_fees = 0
    for student in students:
        if student.id in existing:
            continue
        lines = []
        for item in fee_items:
            if item.charged == FeeItem.Charged.OPTIONAL:
                continue
            if item.charged == FeeItem.Charged.PER_SESSION and (
                first_period is None or period.id != first_period.id
            ):
                continue
            amount = prices.get((item.id, student.current_class_id))
            if amount is not None:
                lines.append((item, amount))
        if not lines:
            skipped_no_fees += 1
            continue
        invoice = Invoice(
            school=request.school, student=student, session=session, period=period,
            number=_next_invoice_number(request.school),
            issue_date=timezone.localdate(), due_date=period.end_date,
        )
        invoice.full_clean(exclude=["school"])
        invoice.save()
        for item, amount in lines:
            InvoiceItem.objects.create(
                school=request.school, invoice=invoice, fee_item=item,
                description=f"{item.name} - {student.current_class}",
                amount=amount,
            )
        created += 1

    record(
        request, "fees.invoices_generated", target=period,
        created=created, skipped=skipped_no_fees,
        school_class=school_class.name if school_class else "all",
    )
    return {"created": created, "skipped": skipped_no_fees}


@transaction.atomic
def record_payment(request, invoice, amount, method, reference, paid_on, note=""):
    """Record money received. Safe to retry: the same reference returns the
    same payment instead of charging twice."""
    require_role(request, FINANCE_ROLES)
    ensure_owned(request, invoice)
    try:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValidationError("Enter a valid amount.") from exc
    reference = (reference or "").strip()
    if not reference:
        raise ValidationError("A payment reference is required.")

    existing = Payment.objects.for_school(request.school).filter(
        reference__iexact=reference
    ).first()
    if existing is not None:
        return existing, False

    if paid_on > timezone.localdate():
        raise ValidationError("The payment date cannot be in the future.")

    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.balance <= 0:
        raise ValidationError("This invoice is already fully paid.")
    if amount > invoice.balance:
        raise ValidationError(
            f"The amount exceeds the balance of NGN {invoice.balance:,.2f}."
        )
    payment = Payment(
        school=request.school, invoice=invoice, amount=amount, method=method,
        reference=reference, paid_on=paid_on, received_by=request.membership,
        note=note or "",
    )
    try:
        payment.full_clean(exclude=["school"])
    except ValidationError as exc:
        raise ValidationError(_text(exc)) from exc
    payment.save()

    if invoice.balance == 0:
        invoice.status = Invoice.Status.PAID
    else:
        invoice.status = Invoice.Status.PART_PAID
    invoice.save(update_fields=["status"])

    record(
        request, "fees.payment_recorded", target=payment,
        invoice=invoice.number, amount=str(amount), method=method, reference=reference,
    )
    return payment, True
