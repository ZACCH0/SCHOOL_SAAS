from django import forms

from apps.schools.models import Membership

from .models import Level


class ClassForm(forms.Form):
    level = forms.ModelChoiceField(queryset=Level.objects.none())
    name = forms.CharField(max_length=100)
    order = forms.IntegerField(
        min_value=1,
        label="Position",
        help_text="Promotion order across the school. For example Primary 1 is 1.",
    )

    def __init__(self, *args, school, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["level"].queryset = Level.objects.for_school(school)


class SectionForm(forms.Form):
    name = forms.CharField(max_length=50, label="Section name")


class ClassTeacherForm(forms.Form):
    teacher = forms.ModelChoiceField(queryset=Membership.objects.none())

    def __init__(self, *args, school, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teacher"].queryset = Membership.objects.filter(
            school=school, role=Membership.Role.TEACHER, is_active=True
        ).select_related("user")
