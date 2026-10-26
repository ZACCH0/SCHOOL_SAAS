from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.academics.selectors import current_session
from apps.classes.models import SchoolClass
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, Membership, role_required
from apps.schools.service_helpers import ensure_owned
from apps.students.models import Student

from .forms import FeeItemForm, GenerateInvoicesForm, InvoiceFilterForm, RecordPaymentForm
from .models import FeeItem, Invoice, InvoiceItem, Payment
from .selectors import fees_overview
from .services import create_fee_item, generate_invoices, record_payment, set_price

FINANCE_ROLES = (Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.BURSAR)

finance_only = role_required(*FINANCE_ROLES)
structure_only = role_required(*MANAGE_STRUCTURE_ROLES)


def _zero():
    return Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))


def invoice_queryset(school):
    """Invoices with reliable totals (subqueries, so items and payments never
    cross-multiply each other in one join)."""
    items_sq = (
        InvoiceItem.objects.filter(invoice=OuterRef("pk"))
        .values("invoice")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    paid_sq = (
        Payment.objects.filter(invoice=OuterRef("pk"))
        .values("invoice")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    return Invoice.objects.for_school(school).annotate(
        item_total=Coalesce(Subquery(items_sq, output_field=_zero().output_field), _zero()),
        paid_total=Coalesce(Subquery(paid_sq, output_field=_zero().output_field), _zero()),
        balance_due=F("item_total") - F("paid_total"),
    )


def _text(exc):
    return " ".join(exc.messages)


def _current_period(session):
    today = date.today()
    periods = list(session.periods.order_by("start_date", "id"))
    for period in periods:
        if period.start_date <= today <= period.end_date:
            return period
    return periods[-1] if periods else None


@finance_only
def fees_home(request):
    session = current_session(request.school)
    if session is None:
        return render(request, "fees/home.html", {"no_session": True})
    periods = list(session.periods.order_by("start_date", "id"))
    period_id = request.GET.get("period", "")
    period = next((p for p in periods if str(p.pk) == period_id), None) or _current_period(session)
    if period is None:
        return render(request, "fees/home.html", {"session": session, "no_period": True})
    overview = fees_overview(request.school, period)
    return render(
        request, "fees/home.html",
        {"session": session, "period": period, "periods": periods, "overview": overview},
    )


@structure_only
def fee_structure(request):
    session = current_session(request.school)
    if session is None:
        return render(request, "fees/structure.html", {"no_session": True})
    classes = list(SchoolClass.objects.for_school(request.school).filter(is_active=True).order_by("order"))
    items = FeeItem.objects.for_school(request.school).filter(session=session).prefetch_related("prices__school_class")
    prices = {(p.fee_item_id, p.school_class_id): p for item in items for p in item.prices.all()}
    return render(
        request, "fees/structure.html",
        {
            "session": session, "classes": classes, "items": items,
            "prices": prices, "add_form": FeeItemForm(),
        },
    )


@require_POST
@structure_only
def fee_item_add(request):
    session = current_session(request.school)
    form = FeeItemForm(request.POST)
    if form.is_valid():
        try:
            create_fee_item(
                request, session, form.cleaned_data["name"], form.cleaned_data["charged"]
            )
            messages.success(request, "Fee item added.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, _text(exc) if isinstance(exc, ValidationError) else str(exc))
    else:
        messages.error(request, "Enter a fee item name.")
    return redirect("fees:structure")


@require_POST
@structure_only
def fee_price_set(request):
    fee_item = get_object_or_404(
        FeeItem.objects.for_school(request.school),
        pk=request.POST.get("fee_item", "0"),
    )
    class_id = request.POST.get("school_class", "")
    amount = request.POST.get("amount", "")
    if not class_id.isdigit() or not amount:
        messages.error(request, "Choose a class and enter an amount.")
        return redirect("fees:structure")
    school_class = get_object_or_404(SchoolClass.objects.for_school(request.school), pk=int(class_id))
    try:
        set_price(request, fee_item, school_class, amount)
        messages.success(request, f"Price saved for {fee_item.name}.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, _text(exc) if isinstance(exc, ValidationError) else str(exc))
    return redirect("fees:structure")


@finance_only
def invoice_list(request):
    session = current_session(request.school)
    if session is None:
        return render(request, "fees/invoice_list.html", {"no_session": True})
    period = _current_period(session)
    form = InvoiceFilterForm(school=request.school, data=request.GET or None)
    invoices = (
        invoice_queryset(request.school)
        .filter(period=period)
        .select_related("student__current_class")
        .order_by("-number")
    )
    if form.is_valid():
        q = (form.cleaned_data.get("q") or "").strip()
        if q:
            invoices = invoices.filter(
                Q(number__icontains=q)
                | Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
                | Q(student__admission_number__icontains=q)
            )
        chosen_class = form.cleaned_data.get("school_class")
        if chosen_class:
            invoices = invoices.filter(student__current_class=chosen_class)
        status = form.cleaned_data.get("status") or ""
        if status == "overdue":
            invoices = (inv for inv in invoices if inv.is_overdue)
        elif status:
            invoices = invoices.filter(status=status)
    page = Paginator(list(invoices), 25).get_page(request.GET.get("page"))
    return render(
        request, "fees/invoice_list.html",
        {
            "session": session, "period": period, "page_obj": page,
            "form": form, "generate_form": GenerateInvoicesForm(school=request.school),
        },
    )


@require_POST
@finance_only
def invoice_generate(request):
    session = current_session(request.school)
    period = _current_period(session) if session else None
    if period is None:
        messages.error(request, "There is no term to bill. Set up sessions and terms first.")
        return redirect("fees:invoice_list")
    form = GenerateInvoicesForm(school=request.school, data=request.POST)
    school_class = form["school_class"].value()
    chosen = None
    if school_class:
        chosen = get_object_or_404(SchoolClass.objects.for_school(request.school), pk=int(school_class))
    try:
        result = generate_invoices(request, period, chosen)
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, _text(exc) if isinstance(exc, ValidationError) else str(exc))
        return redirect("fees:invoice_list")
    messages.success(
        request,
        f"Generated {result['created']} invoice(s)"
        + (f"; {result['skipped']} pupil(s) had no fee prices." if result["skipped"] else "."),
    )
    return redirect("fees:invoice_list")


@finance_only
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.for_school(request.school).select_related(
            "student__current_class", "period", "session"
        ),
        pk=pk,
    )
    return render(
        request, "fees/invoice_detail.html",
        {
            "invoice": invoice, "items": invoice.items.select_related("fee_item"),
            "payments": invoice.payments.select_related("received_by__user").order_by("-created_at"),
            "pay_form": RecordPaymentForm(initial={"paid_on": date.today()}),
        },
    )


@require_POST
@finance_only
def payment_record(request, invoice_pk):
    invoice = get_object_or_404(Invoice.objects.for_school(request.school), pk=invoice_pk)
    form = RecordPaymentForm(request.POST)
    if form.is_valid():
        try:
            payment, created = record_payment(
                request, invoice,
                amount=form.cleaned_data["amount"],
                method=form.cleaned_data["method"],
                reference=form.cleaned_data["reference"],
                paid_on=form.cleaned_data["paid_on"],
                note=form.cleaned_data["note"],
            )
            if created:
                messages.success(request, f"Payment {payment.reference} recorded.")
            else:
                messages.warning(request, f"Payment {payment.reference} was already recorded earlier.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, _text(exc) if isinstance(exc, ValidationError) else str(exc))
    else:
        messages.error(request, "Check the payment details: amount, method, reference and date are required.")
    return redirect("fees:invoice_detail", pk=invoice.pk)


@finance_only
def payment_list(request):
    payments = Payment.objects.for_school(request.school).select_related(
        "invoice__student__current_class", "invoice__period", "received_by__user"
    ).order_by("-created_at")
    page = Paginator(payments, 25).get_page(request.GET.get("page"))
    return render(request, "fees/payment_list.html", {"page_obj": page})


@finance_only
def receipt(request, pk):
    payment = get_object_or_404(
        Payment.objects.for_school(request.school).select_related(
            "invoice__student__current_class", "invoice__period__session",
            "invoice__session", "received_by__user",
        ),
        pk=pk,
    )
    invoice = payment.invoice
    previous = invoice.balance + payment.amount
    return render(
        request, "fees/receipt.html",
        {"payment": payment, "invoice": invoice, "previous_balance": previous},
    )
