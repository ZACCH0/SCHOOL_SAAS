from django import forms

from apps.fees.models import FeeItem, FeeItemPrice


class FeeItemForm(forms.ModelForm):
    class Meta:
        model = FeeItem
        fields = ["name", "charged"]


class FeeItemPriceForm(forms.ModelForm):
    class Meta:
        model = FeeItemPrice
        fields = ["school_class", "amount"]
