from django import forms

from apps.classes.models import SchoolClass, Section

from .models import AttendanceRecord

OPEN_STATUSES = [
    (AttendanceRecord.Status.PRESENT, "Present"),
    (AttendanceRecord.Status.LATE, "Late"),
    (AttendanceRecord.Status.ABSENT, "Absent"),
    (AttendanceRecord.Status.EXCUSED, "Excused"),
]


class OpenRegisterForm(forms.Form):
    school_class = forms.ModelChoiceField(
        label="Class", queryset=SchoolClass.objects.none(), empty_label=None
    )
    section = forms.ModelChoiceField(
        label="Section", queryset=Section.objects.none(),
        required=False, empty_label="No section",
    )
    day = forms.DateField(
        input_formats=["%Y-%m-%d"], help_text="YYYY-MM-DD."
    )

    def __init__(self, *args, classes_queryset, sections_queryset, initial=None, **kwargs):
        super().__init__(*args, initial=initial, **kwargs)
        self.fields["school_class"].queryset = classes_queryset
        self.fields["section"].queryset = sections_queryset

    def clean(self):
        cleaned = super().clean()
        section = cleaned.get("section")
        if section and cleaned.get("school_class") != section.school_class:
            raise forms.ValidationError("The section does not belong to the chosen class.")
        return cleaned
