import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token

pytestmark = pytest.mark.django_db

GOOD = "S3cure-pass!"
GENERIC = "Wrong username or password."


def post_token(client, identifier, password):
    return client.post(
        reverse("api:token"),
        {"identifier": identifier, "password": password},
        content_type="application/json",
    )


def test_token_issued_for_username(client, db):
    user = get_user_model().objects.create_user("ada1", password=GOOD)

    response = post_token(client, "ada1", GOOD)

    assert response.status_code == 200
    assert response.json()["username"] == "ada1"
    assert Token.objects.get(user=user).key == response.json()["token"]


def test_token_works_with_email_identifier(client, db):
    user = get_user_model().objects.create_user("ada2", password=GOOD)
    get_user_model().objects.filter(pk=user.pk).update(email="ada2@example.com")
    user.refresh_from_db()

    response = post_token(client, "ada2@example.com", GOOD)

    assert response.status_code == 200
    assert response.json()["token"] == Token.objects.get(user=user).key


def test_token_works_with_phone_identifier(client, db):
    user = get_user_model().objects.create_user("ada3", password=GOOD)
    user.phone = "08031234567"
    user.save()
    user.refresh_from_db()

    response = post_token(client, "08031234567", GOOD)

    assert response.status_code == 200
    assert response.json()["token"] == Token.objects.get(user=user).key


def test_same_credentials_return_the_same_token(client, db):
    get_user_model().objects.create_user("ada4", password=GOOD)

    first = post_token(client, "ada4", GOOD).json()["token"]
    second = post_token(client, "ada4", GOOD).json()["token"]

    assert first == second


def test_wrong_password_is_a_generic_400(client, db):
    get_user_model().objects.create_user("ada5", password=GOOD)

    response = post_token(client, "ada5", "wrong-password")

    assert response.status_code == 400
    assert response.json()["detail"] == GENERIC


def test_unknown_identifier_is_a_generic_400(client, db):
    response = post_token(client, "nobody-here", GOOD)

    assert response.status_code == 400
    assert response.json()["detail"] == GENERIC


def test_ambiguous_email_is_a_generic_400(client, db, monkeypatch):
    """The DB forbids duplicate emails, so the ambiguity guard is simulated."""
    from apps.accounts.identification import AmbiguousIdentifier

    def raise_ambiguous(identifier):
        raise AmbiguousIdentifier("email")

    monkeypatch.setattr("apps.api.views.resolve_user", raise_ambiguous)

    response = post_token(client, "twin@example.com", GOOD)

    assert response.status_code == 400
    assert response.json()["detail"] == GENERIC


def test_five_failures_lock_the_identifier_out(client, db):
    """T7e/T16 rule: axes locks the resolved username, whatever was typed.
    The lockout response comes from AxesMiddleware, same as the website."""
    get_user_model().objects.create_user("ada6", password=GOOD)

    for _ in range(5):
        post_token(client, "ada6", "wrong")
    response = post_token(client, "ada6", GOOD)

    assert response.status_code == 429
    assert b"Too many failed attempts" in response.content


def test_get_is_not_allowed(client, db):
    response = client.get(reverse("api:token"))

    assert response.status_code == 405


def test_token_header_grants_access_to_me(client, db, school_a, make_member):
    member = make_member(school_a)
    token = Token.objects.create(user=member.user)

    response = client.get(
        reverse("api:me"), HTTP_AUTHORIZATION=f"Token {token.key}"
    )

    assert response.status_code == 200
    assert response.json()["username"] == member.user.username
    assert response.json()["school"] == school_a.name
