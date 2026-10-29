from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from apps.academics.selectors import current_or_last_period, current_session, session_periods
from apps.fees.models import Invoice, InvoiceItem, Payment
from apps.results.services import published_subject_results
from apps.schools.models import Membership
from apps.schools.permissions import role_required
from apps.students.models import GuardianLink, Student

from .selectors import children_for

StatusChip = {
    "active": ("ok", "Active"),
    "graduated": ("neutral", "Graduated"),
    "withdrawn": ("bad", "Withdrawn"),
    "suspended": ("warn", "Suspended"),
    "transferred": ("info", "Transferred"),
}

InvoiceChip = {
    "unpaid": ("warn", "Unpaid"),
    "part_paid": ("warn", "Part paid"),
    "paid": ("ok", "Paid"),
}


@role_required(Membership.Role.PARENT)
def children(request):
    kids = children_for(request.membership)
    for kid in kids:
        kid.status_kind, kid.status_label = StatusChip.get(
            kid.status, ("neutral", kid.get_status_display())
        )
    return render(request, "portal/children.html", {"children": kids})


def _invoice_rows(school, pupil):
    """Term invoices of one pupil with the same reliable totals as the fees
    module (subqueries so items and payments never cross-multiply)."""
    zero = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
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
    return (
        Invoice.objects.for_school(school)
        .filter(student=pupil)
        .annotate(
            item_total=Coalesce(
                Subquery(items_sq, output_field=zero.output_field), zero
            ),
            paid_total=Coalesce(
                Subquery(paid_sq, output_field=zero.output_field), zero
            ),
            balance_due=F("item_total") - F("paid_total"),
        )
        .select_related("session", "period")
        .order_by("-session_id", "-period_id")
    )


@role_required(Membership.Role.PARENT)
def child_page(request, pk):
    pupil = get_object_or_404(
        Student.objects.for_school(request.school).select_related(
            "current_class", "current_class__level", "current_section",
        ),
        pk=pk,
    )
    if not GuardianLink.objects.filter(
        school=request.school, student=pupil, guardian=request.membership
    ).exists():
        raise PermissionDenied

    session = current_session(request.school)
    period = current_or_last_period(session) if session else None
    results = list(published_subject_results(request.school, pupil, period).all()) if period else []
    average = (
        (sum((r.percentage for r in results), Decimal("0")) / len(results)).quantize(Decimal("0.1"))
        if results else None
    )
    invoices = list(_invoice_rows(request.school, pupil))
    owed = sum((i.balance_due for i in invoices if i.balance_due > 0), Decimal("0"))
    for invoice in invoices:
        invoice.chip_kind, invoice.chip_label = InvoiceChip.get(
            invoice.status, ("neutral", invoice.get_status_display())
        )
    classline = (
        f"{pupil.current_class}"
        + (f" - {pupil.current_section}" if pupil.current_section_id else "")
        if pupil.current_class_id else "No class yet"
    )
    return render(
        request, "portal/child.html",
        {
            "pupil": pupil,
            "title": f"{pupil.first_name} {pupil.last_name}",
            "session": session,
            "period": period,
            "results": results,
            "average": average,
            "average_display": f"{average}%" if average is not None else "Waiting for published results",
            "invoices": invoices,
            "owed": owed,
            "owed_display": f"₦{owed:,.0f}",
            "owed_tone": "warn" if owed > 0 else None,
            "classline": classline,
        },
    )
