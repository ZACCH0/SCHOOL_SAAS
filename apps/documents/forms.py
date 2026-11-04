from django import forms

from .models import Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "category", "description", "audience", "file"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "w-full", "placeholder": "e.g. Behaviour policy"}
            ),
            "category": forms.TextInput(
                attrs={"class": "w-full", "placeholder": "e.g. Circular, policy, form"}
            ),
            "description": forms.Textarea(attrs={"class": "w-full", "rows": 3}),
        }
