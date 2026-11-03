from django import forms

from .models import TimetableSlot


class SlotForm(forms.Form):
    """One period (or break) on a class's timetable.

    The school, session and class are fixed by the view; the form only
    collects what a slot needs. Leave the subject empty to place a break or
    assembly, which must carry a label."""
    subject = forms.ModelChoiceField(
        queryset=None, required=False, empty_label="Break / assembly (no subject)",
        help_text="Leave empty for a break or assembly.",
    )
    section = forms.ModelChoiceField(
        queryset=None, required=False, empty_label="Whole class",
        help_text="Choose a section to restrict the period to that section.",
    )
    label = forms.CharField(
        required=False, max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Long break"}),
        help_text="Needed only for a break or assembly.",
    )
    day = forms.TypedChoiceField(
        choices=TimetableSlot.WeekDay.choices, coerce=int,
    )
    starts_at = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    ends_at = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("subject"):
            cleaned["label"] = ""
        elif not (cleaned.get("label") or "").strip():
            self.add_error("label", "A break or assembly needs a label.")
        return cleaned

    def __init__(self, *, subjects, sections, **kwargs):
        super().__init__(**kwargs)
        self.fields["subject"].queryset = subjects
        self.fields["section"].queryset = sections
