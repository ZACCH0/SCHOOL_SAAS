from django import forms

from apps.classes.models import SchoolClass, Section

from .models import Applicant


class ApplicantForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="First name")
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, label="Last name")
    sex = forms.ChoiceField(choices=Applicant._meta.get_field("sex").choices)
    date_of_birth = forms.DateField(
        required=False, label="Date of birth", input_formats=["%Y-%m-%d"],
        help_text="Optional now (needed before enrolment). YYYY-MM-DD.",
    )
    target_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(), required=False, label="Class applied for",
        empty_label="Not chosen yet",
    )
    guardian_name = forms.CharField(max_length=100, required=False, label="Guardian name")
    guardian_phone = forms.CharField(max_length=20, required=False)
    guardian_email = forms.EmailField(required=False)
    address = forms.CharField(required=False, widget=forms.TextInput)
    notes = forms.CharField(required=False, widget=forms.TextInput)

    def __init__(self, *args, school, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["target_class"].queryset = (
            SchoolClass.objects.for_school(school).filter(is_active=True)
        )


class ReviewForm(forms.Form):
    notes = forms.CharField(
        required=False, widget=forms.TextInput,
        help_text="Optional interview or screening note.",
    )


class DecideForm(ReviewForm):
    decision = forms.CharField(widget=forms.HiddenInput)


class ConvertForm(forms.Form):
    """Enrolment: the school keeps control of the student admission number."""

    admission_number = forms.CharField(
        max_length=30, label="Student admission number",
        help_text="Must be unused in this school. Cannot be changed later.",
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(), required=False, empty_label="No section",
        label="Section", help_text="Only used when the class is split.",
    )

    def __init__(self, *args, applicant, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = (
            Section.objects.for_school(applicant.school)
            .filter(is_active=True, school_class=applicant.target_class)
        )
