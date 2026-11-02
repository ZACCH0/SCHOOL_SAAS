from django import forms

from .models import Announcement


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "audience"]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "w-full", "placeholder": "e.g. Mid-term break"}
            ),
            "body": forms.Textarea(attrs={"class": "w-full", "rows": 5}),
        }
