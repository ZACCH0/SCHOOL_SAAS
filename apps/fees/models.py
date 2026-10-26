from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from apps.academics.models import AcademicSession, AcademicPeriod
from apps.classes.models import SchoolClass
from apps.schools.models import ValidatedSchoolModel
from apps.students.models import Student


class FeeItem(ValidatedSchoolModel):
    """One fee a school charges (e.g. Tuition) for one session.

    The amount is set per class through FeeItemPrice, because classes can
    differ (e.g. Primary 1-3 vs Primary 4-6).
    """

    class Charged(models.TextChoices):
        PER_TERM = "per_term", "Per term"
        PER_SESSION = "per_session", "Per session"
        OPTIONAL = "optional", "Optional"

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.PROTECT,
        related_name="fee_items",
    )
    name = models.CharField(max_length=120)
    charged = models.CharField(
        max_length=12, choices=Charged.choices, default=Charged.PER_TERM
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "session",
                "school",
                name="unique_fee_item_name_per_session",
            )
        ]
        indexes = [models.Index(fields=["session"])]

    def __str__(self):
        return f"{self.name} ({self.session.name})"

    def clean(self):
        self.ensure_same_school("session")


class FeeItemPrice(ValidatedSchoolModel):
    """How much a fee item costs for one class in the item's session."""

    fee_item = models.ForeignKey(
        FeeItem, on_delete=models.PROTECT, related_name="prices"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="fee_prices"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["school_class__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["fee_item", "school_class"],
                name="unique_price_per_fee_item_and_class",
            )
        ]

    def __str__(self):
        return f"{self.fee_item.name} - {self.school_class}: NGN {self.amount}"

    def clean(self):
        self.ensure_same_school("fee_item", "school_class")
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("The amount must be greater than zero.")


class Invoice(ValidatedSchoolModel):
    """A term's bill for one student. Items snapshot what was charged."""

    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PART_PAID = "part_paid", "Part paid"
        PAID = "paid", "Paid"

    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, related_name="invoices"
    )
    session = models.ForeignKey(
        AcademicSession, on_delete=models.PROTECT, related_name="invoices"
    )
    period = models.ForeignKey(
        AcademicPeriod, on_delete=models.PROTECT, related_name="invoices"
    )
    number = models.CharField(max_length=30)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.UNPAID
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                Lower("number"),
                "school",
                name="unique_invoice_number_per_school",
            ),
            models.CheckConstraint(
                check=models.Q(due_date__gte=models.F("issue_date")),
                name="invoice_due_date_after_issue_date",
            ),
        ]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["student"])]

    def __str__(self):
        return f"{self.number} - {self.student}"

    def clean(self):
        self.ensure_same_school("student", "session", "period")
        if (
            self.session_id
            and self.period_id
            and self.period.session_id != self.session_id
        ):
            raise ValidationError("The term must belong to the invoice's session.")

    @property
    def total(self):
        return sum((item.amount for item in self.items.all()), Decimal("0"))

    @property
    def paid(self):
        return sum((p.amount for p in self.payments.all()), Decimal("0"))

    @property
    def balance(self):
        return self.total - self.paid

    @property
    def is_overdue(self):
        from django.utils import timezone

        return self.status != self.Status.PAID and timezone.localdate() > self.due_date


class InvoiceItem(ValidatedSchoolModel):
    """One line on an invoice. Keeps its own description and amount so later
    changes to the fee structure never change issued invoices."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="items"
    )
    fee_item = models.ForeignKey(
        FeeItem, on_delete=models.PROTECT, related_name="invoice_items"
    )
    description = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.invoice.number}: {self.description}"

    def clean(self):
        self.ensure_same_school("invoice", "fee_item")
        if self.amount is not None and self.amount <= 0:
            raise ValidationError("The amount must be greater than zero.")


class Payment(ValidatedSchoolModel):
    """Money received against one invoice. History is never edited or deleted."""

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        TRANSFER = "transfer", "Bank transfer"
        POS = "pos", "POS"
        CHEQUE = "cheque", "Cheque"

    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(
        max_length=10, choices=Method.choices, default=Method.CASH
    )
    reference = models.CharField(max_length=60)
    paid_on = models.DateField()
    received_by = models.ForeignKey(
        "schools.Membership", on_delete=models.PROTECT, related_name="payments_received"
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                Lower("reference"),
                "school",
                name="unique_payment_reference_per_school",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="payment_amount_positive",
            ),
        ]
        indexes = [models.Index(fields=["invoice"])]

    def __str__(self):
        return f"{self.reference}: NGN {self.amount} for {self.invoice.number}"

    def clean(self):
        self.ensure_same_school("invoice", "received_by")
