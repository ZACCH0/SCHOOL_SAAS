from django import forms

from apps.classes.models import Section
from apps.schools.models import Membership

from .models import Subject


class SubjectForm(forms.Form):
    name = forms.CharField(max_length=100)
    code = forms.CharField(max_length=20, required=False)


class ClassSubjectForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.none())
    is_optional = forms.BooleanField(required=False, label="Optional subject")

    def __init__(self, *args, school, school_class, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].queryset = (
            Subject.objects.for_school(school)
            .filter(is_active=True)
            .exclude(class_subjects__school_class=school_class)
        )


class TeacherAssignmentForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.none())
    teacher = forms.ModelChoiceField(queryset=Membership.objects.none())
    section = forms.ModelChoiceField(queryset=Section.objects.none(), required=False)

    def __init__(self, *args, school, school_class, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].queryset = Subject.objects.for_school(school).filter(
            class_subjects__school_class=school_class
        )
        self.fields["teacher"].queryset = Membership.objects.filter(
            school=school, role=Membership.Role.TEACHER, is_active=True
        ).select_related("user")
        self.fields["section"].queryset = Section.objects.for_school(school).filter(
            school_class=school_class
        )
