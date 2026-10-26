from django.db.models import Sum

from apps.fees.models import InvoiceItem, Payment


def fees_overview(school, period):
    """Real totals for one term, grouped by class. Read-only."""
    expected_rows = (
        InvoiceItem.objects.for_school(school)
        .filter(invoice__period=period)
        .values(
            "invoice__student__current_class_id",
            "invoice__student__current_class__name",
            "invoice__student__current_class__order",
        )
        .annotate(total=Sum("amount"))
    )
    collected_rows = (
        Payment.objects.for_school(school)
        .filter(invoice__period=period)
        .values("invoice__student__current_class_id")
        .annotate(total=Sum("amount"))
    )
    collected_by_class = {
        row["invoice__student__current_class_id"]: row["total"] for row in collected_rows
    }

    rows = []
    total_expected = total_collected = 0
    for row in expected_rows:
        class_id = row["invoice__student__current_class_id"]
        expected = row["total"] or 0
        collected = collected_by_class.get(class_id, 0)
        rows.append(
            {
                "class_id": class_id,
                "class_name": row["invoice__student__current_class__name"],
                "order": row["invoice__student__current_class__order"],
                "expected": expected,
                "collected": collected,
                "outstanding": expected - collected,
            }
        )
        total_expected += expected
        total_collected += collected
    rows.sort(key=lambda r: (r["order"], r["class_name"]))
    invoice_count = (
        InvoiceItem.objects.for_school(school)
        .filter(invoice__period=period)
        .values("invoice_id")
        .distinct()
        .count()
    )
    rate = round(total_collected * 100 / total_expected) if total_expected else None
    return {
        "rows": rows,
        "expected": total_expected,
        "collected": total_collected,
        "outstanding": total_expected - total_collected,
        "rate": rate,
        "invoice_count": invoice_count,
    }
