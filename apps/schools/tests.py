import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from .models import Membership, School
# Create your tests here.

User = get_user_model()
def make_school(name="Alpha School", slug="alpha"):
    return School.objects.create(name=name, slug=slug)
def make_user(username="user1"):
    return User.objects.create_user(username=username, password="S3cure-pass!")

@pytest.mark.django_db
def test_user_can_have_two_roles_in_same_school():
    school, user = make_school(), make_user()
    Membership.objects.create(user=user, school=school, role=Membership.Role.TEACHER)
    Membership.objects.create(user=user, school=school, role=Membership.Role.PARENT)
    assert user.memberships.count() == 2

@pytest.mark.django_db
def test_same_role_cannot_be_duplicated_in_one_school():
    school, user = make_school(), make_user()
    Membership.objects.create(user=user, school=school, role=Membership.Role.TEACHER)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Membership.objects.create(user=user, school=school, role=Membership.Role.TEACHER)


@pytest.mark.django_db
def test_user_can_belong_to_two_schools():
    a, b = make_school(), make_school("Beta School", "beta")
    user = make_user()
    Membership.objects.create(user=user, school=a, role=Membership.Role.TEACHER)
    Membership.objects.create(user=user, school=b, role=Membership.Role.TEACHER)
    assert user.memberships.count() == 2


@pytest.mark.django_db
def test_school_with_members_cannot_be_deleted():
    school, user = make_school(), make_user()
    Membership.objects.create(user=user, school=school, role=Membership.Role.ADMIN)
    with pytest.raises(ProtectedError):
        school.delete()