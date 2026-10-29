from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from apps.classes.models import SchoolClass, Section
from apps.schools.models import Membership

from .models import GuardianLink, Student


class StudentForm(forms.Form):
    first_name = forms.CharField(max_length=100)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100)
    sex = forms.ChoiceField(choices=Student.sex.field.choices)
    date_of_birth = forms.DateField(
        label="Date of birth",
        input_formats=["%Y-%m-%d"],
        help_text="YYYY-MM-DD.",
    )
    address = forms.CharField(required=False, widget=forms.TextInput)
    admission_number = forms.CharField(
        max_length=30, label="Admission number",
        help_text="This school cannot use the same number twice.",
    )
    current_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(), required=False, label="Class", empty_label="No class yet"
    )
    current_section = forms.ModelChoiceField(
        queryset=Section.objects.none(), required=False, label="Section",
        empty_label="No section", help_text="Only used when the class is split.",
    )

    def __init__(self, *args, school, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["current_class"].queryset = (
            SchoolClass.objects.for_school(school).filter(is_active=True)
        )
        self.fields["current_section"].queryset = (
            Section.objects.for_school(school).filter(is_active=True)
        )

    def clean(self):
        cleaned = super().clean()
        section = cleaned.get("current_section")
        if section and cleaned.get("current_class") != section.school_class:
            raise ValidationError("The section does not belong to the chosen class.")
        return cleaned


class StudentDetailForm(StudentForm):
    """Editing a student: the admission number is never changed."""

    admission_number = None


class GuardianForm(forms.Form):
    guardian = forms.ModelChoiceField(
        label="Parent / guardian", queryset=Membership.objects.none()
    )
    relationship = forms.ChoiceField(choices=GuardianLink.Relationship.choices)
    is_primary = forms.BooleanField(
        required=False, label="Primary contact", help_text="The first person to contact.",
    )

    def __init__(self, *args, school, student, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["guardian"].queryset = (
            Membership.objects.filter(
                school=school, role=Membership.Role.PARENT, is_active=True
            )
            .select_related("user")
            .exclude(guardian_links__student=student)
        )


VALID_USERNAME_RE = r"^[\w.+-]+$"


class ParentForm(forms.Form):
    """The office creates a NEW parent account, then links children to it."""

    username = forms.CharField(
        max_length=150,
        validators=[RegexValidator(VALID_USERNAME_RE, "Letters, numbers and . _ + - only.")],
    )
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=100, label="First name")
    last_name = forms.CharField(max_length=100, label="Last name")
    email = forms.EmailField(
        required=False, help_text="Optional. Needed for password self-reset."
    )
    phone = forms.CharField(
        max_length=20, required=False, help_text="Optional."
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password)
        return password
