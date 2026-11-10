import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user("teacher1", password="S3cure-pass!")
def test_login_page_loads(client):
    assert client.get(reverse("accounts:login")).status_code == 200

@pytest.mark.django_db
def test_valid_login_redirects_to_dashboard(client, user):
    response = client.post(
        reverse("accounts:login"), {"username": "teacher1", "password": "S3cure-pass!"}
    )
    assert response.status_code == 302
    assert response.url == reverse("core:dashboard")

@pytest.mark.django_db
def test_wrong_password_does_not_log_in(client, user):
    response = client.post(
        reverse("accounts:login"), {"username": "teacher1", "password": "wrong"}
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session

@pytest.mark.django_db
def test_logout_rejects_get_requests(client, user):
    client.force_login(user)
    assert client.get(reverse("accounts:logout")).status_code == 405
    assert "_auth_user_id" in client.session

@pytest.mark.django_db
def test_logout_post_logs_user_out(client, user):
    client.force_login(user)
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_with_email_identifier(client):
    User.objects.create_user(
        "tayo", email="tayo@example.com", password="S3cure-pass!"
    )
    response = client.post(
        reverse("accounts:login"),
        {"username": "TAYO@example.com", "password": "S3cure-pass!"},
    )
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_login_with_phone_identifier_in_any_format(client):
    User.objects.create_user(
        "halima", phone="0803 123 4567", password="S3cure-pass!"
    )
    for typed in ("08031234567", "+234-803-123-4567"):
        response = client.post(
            reverse("accounts:login"),
            {"username": typed, "password": "S3cure-pass!"},
        )
        assert response.status_code == 302
        assert "_auth_user_id" in client.session
        client.logout()


@pytest.mark.django_db
def test_login_with_unknown_identifier_shows_generic_error(client, user):
    response = client.post(
        reverse("accounts:login"), {"username": "ghost", "password": "S3cure-pass!"}
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert b"Wrong username or password" in response.content


@pytest.mark.django_db
def test_login_with_correct_password_but_wrong_case_email_fails(client):
    User.objects.create_user(
        "tayo", email="tayo@example.com", password="S3cure-pass!"
    )
    response = client.post(
        reverse("accounts:login"),
        {"username": "tayo@other.com", "password": "S3cure-pass!"},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session