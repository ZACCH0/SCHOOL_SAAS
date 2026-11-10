import pytest
from django.contrib.auth import get_user_model

from apps.accounts.identification import AmbiguousIdentifier, resolve_user
from apps.accounts.normalization import normalize_phone

User = get_user_model()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0803 123 4567", "+2348031234567"),
        ("08031234567", "+2348031234567"),
        ("+2348031234567", "+2348031234567"),
        ("0803-123-4567", "+2348031234567"),
        ("(0803) 123 4567", "+2348031234567"),
        ("234 803 123 4567", "2348031234567"),
        ("+44 (0)20 7183 8750", "+4402071838750"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_phone_normalization(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.django_db
def test_resolves_exact_username():
    user = User.objects.create_user("teacher1", password="x-S3cure-pass!")
    assert resolve_user("teacher1") == user


@pytest.mark.django_db
def test_resolves_email_case_insensitively():
    user = User.objects.create_user(
        "teacher1", email="TayO@Example.com", password="x-S3cure-pass!"
    )
    assert resolve_user("tayo@example.com") == user


@pytest.mark.django_db
def test_resolves_local_phone_format():
    user = User.objects.create_user(
        "teacher1", phone="0803 123 4567", password="x-S3cure-pass!"
    )
    assert resolve_user("08031234567") == user


@pytest.mark.django_db
def test_resolves_international_phone_format():
    user = User.objects.create_user(
        "teacher1", phone="08031234567", password="x-S3cure-pass!"
    )
    assert resolve_user("+234-803-123-4567") == user


@pytest.mark.django_db
def test_dwelling_on_unknown_identifier_returns_none():
    User.objects.create_user("teacher1", password="x-S3cure-pass!")
    assert resolve_user("ghost") is None
    assert resolve_user("") is None
    assert resolve_user(None) is None


@pytest.mark.django_db
def test_duplicate_email_is_refused_not_guessed():
    User.objects.create_user("a1", email="same@example.com", password="x-S3cure-pass!")
    with pytest.raises(Exception):
        User.objects.create_user("a2", email="same@example.com", password="x-S3cure-pass!")
    # Even a different letter case counts as the same email address.
    with pytest.raises(Exception):
        User.objects.create_user("a3", email="SAME@example.com", password="x-S3cure-pass!")


@pytest.mark.django_db
def test_duplicate_phone_is_refused_not_guessed():
    User.objects.create_user("p1", phone="08031234567", password="x-S3cure-pass!")
    with pytest.raises(Exception):
        User.objects.create_user("p2", phone="08031234567", password="x-S3cure-pass!")


@pytest.mark.django_db
def test_many_blank_emails_and_phones_are_fine():
    for i in range(3):
        User.objects.create_user(f"blank{i}", password="x-S3cure-pass!")
    assert User.objects.filter(email="").count() == 3
