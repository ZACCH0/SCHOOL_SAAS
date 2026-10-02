from django.test import TestCase

import pytest
from django.contrib.auth import get_user_model

#create your model here
def test_project_uses_custom_user_model():
    assert get_user_model()._meta.label == "accounts.User"


@pytest.mark.django_db
def test_user_can_be_created_without_email_or_phone():
    User = get_user_model()
    user = User.objects.create_user(username="parent1", password="S3cure-pass!")
    assert user.email == ""
    assert user.phone == ""


@pytest.mark.django_db
def test_password_is_hashed_not_stored_as_text():
    User = get_user_model()
    user = User.objects.create_user(username="parent2", password="S3cure-pass!")
    assert user.password != "S3cure-pass!"
    assert user.check_password("S3cure-pass!")