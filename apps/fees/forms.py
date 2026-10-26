from django import forms

from apps.classes.models import SchoolClass
from apps.fees.models import FeeItem, FeeItemPrice, Invoice, Payment


class FeeItemForm(forms.ModelForm):
    class Meta:
        model = FeeItem
        fields = ["name", "charged"]


class FeeItemPriceForm(forms.ModelForm):
    class Meta:
        model = FeeItemPrice
        fields = ["school_class", "amount"]


class RecordPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "reference", "paid_on", "note"]
        widgets = {
            "paid_on": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "paid_on": "Payment date",
            "reference": "Bank / receipt reference",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "")


class GenerateInvoicesForm(forms.Form):
    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(), required=False, label="Class (optional)"
    )

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school")
        super().__init__(*args, **kwargs)
        self.fields["school_class"].queryset = SchoolClass.objects.for_school(
            school
        ).filter(is_active=True)


class InvoiceFilterForm(forms.Form):
    STATUS_CHOICES = [("", "All")] + [
        (value, label) for value, label in Invoice.Status.choices
    ] + [("overdue", "Overdue")]

    q = forms.CharField(required=False, label="Search")
    school_class = forms.ModelChoiceField(queryset=SchoolClass.objects.none(), required=False)
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school")
        super().__init__(*args, **kwargs)
        self.fields["school_class"].queryset = SchoolClass.objects.for_school(
            school
        ).filter(is_active=True)
