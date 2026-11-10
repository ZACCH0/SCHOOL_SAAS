import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()
GOOD = "S3cure-pass!"

def attempt(client, username, password):
    return client.post(reverse("accounts:login"), {"username": username, "password": password})

@pytest.fixture
def teacher():
    return User.objects.create_user("teacher1", password=GOOD)

@pytest.mark.django_db
def test_five_wrong_passwords_lock_the_account(client, teacher):
    for _ in range(5):
        attempt(client, "teacher1", "wrong")
    response = attempt(client, "teacher1", GOOD)
    assert response.status_code == 429
    assert "_auth_user_id" not in client.session

@pytest.mark.django_db
def test_locked_page_uses_our_template(client, teacher):
    for _ in range(5):
        attempt(client, "teacher1", "wrong")
    response = attempt(client, "teacher1", GOOD)
    assert b"Too many failed attempts" in response.content

@pytest.mark.django_db
def test_locking_one_user_does_not_block_another(client, teacher):
    User.objects.create_user("teacher2", password=GOOD)
    for _ in range(5):
        attempt(client, "teacher1", "wrong")
    response = attempt(client, "teacher2", GOOD)
    assert response.status_code == 302
    assert "_auth_user_id" in client.session

@pytest.mark.django_db
def test_successful_login_resets_the_failure_count(client, teacher):
    for _ in range(3):
        attempt(client, "teacher1", "wrong")
    assert attempt(client, "teacher1", GOOD).status_code == 302
    client.logout()
    for _ in range(3):
        attempt(client, "teacher1", "wrong")
    assert attempt(client, "teacher1", GOOD).status_code == 302

def test_lockout_time_is_actually_configured():
    from datetime import timedelta

    from django.conf import settings

    assert settings.AXES_COOLOFF_TIME == timedelta(minutes=15)

@pytest.mark.django_db
def test_lockout_covers_login_by_email(client, teacher):
    """T16: T7e resolved every identifier to the username before authenticating,
    so axes must lock an account no matter whether the attacker typed a username,
    email or phone."""
    User.objects.filter(pk=teacher.pk).update(email="teacher1@example.com")
    teacher.refresh_from_db()
    for _ in range(5):
        attempt(client, "teacher1@example.com", "wrong")
    response = attempt(client, "teacher1@example.com", GOOD)
    assert response.status_code == 429
    assert "_auth_user_id" not in client.session