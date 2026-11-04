"""Read-only dashboard helpers for the role dashboards (T14c).

Every number comes from real rows of the ACTIVE school and is scoped to the
current (or last) period where one exists. An empty school shows zeros and
empty states, never sample data."""

from decimal import Decimal

from django.db.models import DecimalField, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.academics.selectors import current_or_last_period
from apps.admissions.models import Applicant
from apps.announcements.models import Announcement
from apps.attendance.models import AttendanceRecord, AttendanceSession
from apps.classes.models import SchoolClass
from apps.fees.models import Invoice, InvoiceItem, Payment
from apps.fees.selectors import fees_overview
from apps.portal.selectors import children_for
from apps.results.models import ResultSheet
from apps.results.services import published_subject_results
from apps.schools.models import Membership
from apps.students.models import Student
from apps.subjects.selectors import assignments_for, assignment_covers
from apps.timetable.selectors import covering_slots

MANAGER_ROLES = (Membership.Role.OWNER, Membership.Role.ADMIN)

_NOTICES_LIMIT = 3


def announcements_for(school, role, limit=_NOTICES_LIMIT):
    """The newest active notices this role may read, using the notice board's
    audience rule: managers see all audiences; everyone else sees 'everyone'
    plus their own audience row."""
    notices = (
        Announcement.objects.for_school(school)
        .filter(is_active=True)
        .order_by("-created_at", "-id")
    )
    if role in MANAGER_ROLES:
        return list(notices[:limit])
    audiences = ["everyone"]
    if role == Membership.Role.TEACHER:
        audiences.append("teachers")
    elif role == Membership.Role.BURSAR:
        audiences.append("staff")
    elif role == Membership.Role.PARENT:
        audiences.append("parents")
    return list(notices.filter(audience__in=audiences)[:limit])


def _no_fees_yet():
    return {
        "rows": [], "expected": Decimal("0"), "collected": Decimal("0"),
        "outstanding": Decimal("0"), "rate": None, "invoice_count": 0,
    }


def _fees(school, period):
    return fees_overview(school, period) if period else _no_fees_yet()


def _attendance_today(school):
    """Attendance for TODAY, using the same formula as the attendance page
    (present share of today's marked lines) plus how many registers the
    office has not taken yet. Read-only."""
    today = timezone.localdate()
    registers = AttendanceSession.objects.for_school(school).filter(date=today)
    records = AttendanceRecord.objects.filter(register__in=registers)
    total = records.count()
    present = records.filter(status=AttendanceRecord.Status.PRESENT).count()
    missing = 0
    for klass in SchoolClass.objects.for_school(school).filter(is_active=True):
        spots = list(klass.sections.filter(is_active=True)) or [None]
        for section in spots:
            if not AttendanceSession.objects.for_school(school).filter(
                school_class=klass, date=today, section=section,
            ).exists():
                missing += 1
    return {
        "pct": round(present * 100 / total) if total else None,
        "missing": missing,
    }


def manager_dashboard(school, period):
    """Owner/admin numbers: people, today's attendance, admissions waiting on
    the office, sheets waiting for approval, and the money position."""
    results_waiting = 0
    if period:
        results_waiting = ResultSheet.objects.for_school(school).filter(
            period=period,
            status__in=[ResultSheet.Status.SUBMITTED, ResultSheet.Status.REVIEWED],
        ).count()
    return {
        "students": Student.objects.for_school(school)
        .filter(status=Student.Status.ACTIVE).count(),
        "teachers": Membership.objects.filter(
            school=school, role=Membership.Role.TEACHER, is_active=True,
        ).count(),
        "admissions_waiting": Applicant.objects.for_school(school).filter(
            status__in=["applied", "reviewed"],
        ).count(),
        "results_waiting": results_waiting,
        "attendance": _attendance_today(school),
        "fees": _fees(school, period),
        "notices": announcements_for(school, Membership.Role.OWNER),
    }


def bursar_dashboard(school, period):
    """Bursar numbers: the money position plus the newest recorded payments
    for the term."""
    payments = []
    if period:
        payments = list(
            Payment.objects.for_school(school)
            .filter(invoice__period=period)
            .select_related("invoice")
            .order_by("-paid_on", "-id")[:5]
        )
    return {
        "fees": _fees(school, period),
        "payments": payments,
        "notices": announcements_for(school, Membership.Role.BURSAR),
    }


def teacher_dashboard(school, membership, period):
    """Teacher numbers: what I teach this term, my periods today, and draft
    sheets I can still fill in. The coverage rule is the same one that gates
    score entry and the My timetable page."""
    context = {"assignments": [], "periods_today": [], "draft_sheets": []}
    if period is None:
        context["notices"] = announcements_for(school, Membership.Role.TEACHER)
        return context

    assignments = assignments_for(school, membership, period.session)
    context["assignments"] = assignments
    context["periods_today"] = [
        slot for slot in covering_slots(
            school, period.session, membership,
            day=timezone.localdate().isoweekday(),
        )
    ]
    context["draft_sheets"] = [
        sheet
        for sheet in ResultSheet.objects.for_school(school)
        .filter(period=period, status=ResultSheet.Status.DRAFT)
        .select_related("school_class", "section", "subject")
        .order_by("school_class__order", "section__name", "subject__name")
        if assignment_covers(
            assignments,
            school_class_id=sheet.school_class_id,
            subject_id=sheet.subject_id,
            section_id=sheet.section_id,
        )
    ]
    context["notices"] = announcements_for(school, Membership.Role.TEACHER)
    return context


def _children_fees_owed(school, period, children):
    """Owed money per child for one term, from the same subquery totals the
    fees module trusts (item sums minus payment sums, never cross-multiplied)."""
    if period is None:
        return {}
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
    totals = (
        Invoice.objects.for_school(school)
        .filter(period=period, student__in=children)
        .annotate(
            item_total=Coalesce(Subquery(items_sq, output_field=zero.output_field), zero),
            paid_total=Coalesce(Subquery(paid_sq, output_field=zero.output_field), zero),
            balance_due=F("item_total") - F("paid_total"),
        )
        .values("student_id")
        .annotate(items=Sum("item_total"), paid=Sum("paid_total"))
    )
    return {
        row["student_id"]: (row["items"] or Decimal("0")) - (row["paid"] or Decimal("0"))
        for row in totals
    }


def parent_dashboard(school, membership, period):
    """Parent numbers: the children linked through GuardianLink with what they
    owe this term and how many published results each has."""
    children = children_for(membership)
    owed_by_child = _children_fees_owed(school, period, children)
    rows = []
    for child in children:
        published = (
            published_subject_results(school, child, period).count()
            if period else 0
        )
        rows.append({
            "pupil": child,
            "owed": owed_by_child.get(child.id, Decimal("0")),
            "published_results": published,
        })
    return {
        "children": rows,
        "notices": announcements_for(school, Membership.Role.PARENT),
    }
