import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode

from apps.accounts import channels as channel_module
from apps.accounts.models import OneTimeCode

User = get_user_model()
NEW_PASSWORD = "N3w-Secure-pass!"


@pytest.fixture
def parent():
    return User.objects.create_user(
        "parent1", email="parent1@example.com", password="Old-Secure-pass1"
    )


@pytest.fixture
def phone_parent():
    return User.objects.create_user(
        "halima", phone="0803 555 0101", password="Old-Secure-pass1"
    )


def test_reset_page_loads(client):
    assert client.get(reverse("accounts:password_reset")).status_code == 200


@pytest.mark.django_db
def test_known_email_receives_one_reset_email(client, parent):
    response = client.post(
        reverse("accounts:password_reset"), {"identifier": "parent1@example.com"}
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 1
    assert "/accounts/reset/" in mail.outbox[0].body


@pytest.mark.django_db
def test_known_username_of_email_user_gets_the_link(client, parent):
    response = client.post(reverse("accounts:password_reset"), {"identifier": "parent1"})
    assert response.status_code == 302
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_unknown_identifier_gets_same_response_and_nothing(client, parent):
    response = client.post(
        reverse("accounts:password_reset"), {"identifier": "nobody@example.com"}
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 0
    assert OneTimeCode.objects.count() == 0


@pytest.mark.django_db
def test_phone_user_gets_a_code_not_an_email(client, phone_parent):
    response = client.post(
        reverse("accounts:password_reset"), {"identifier": "0803 555 0101"}
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 0
    assert OneTimeCode.objects.filter(
        user=phone_parent, purpose=OneTimeCode.Purpose.PASSWORD_RESET
    ).exists()


@pytest.mark.django_db
def test_full_email_reset_flow_changes_password(client, parent):
    client.post(
        reverse("accounts:password_reset"), {"identifier": "parent1@example.com"}
    )
    link = re.search(r"http://testserver(/accounts/reset/\S+)", mail.outbox[0].body).group(1)
    response = client.get(link)
    assert response.status_code == 302
    set_url = response.url
    response = client.post(
        set_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_complete")
    parent.refresh_from_db()
    assert parent.check_password(NEW_PASSWORD)
    response = client.post(
        reverse("accounts:login"), {"username": "parent1", "password": NEW_PASSWORD}
    )
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_full_sms_code_flow_changes_password(client, phone_parent, monkeypatch):
    sent = []
    monkeypatch.setattr(
        channel_module, "send_code_sms", lambda user, code: sent.append(code)
    )
    client.post(reverse("accounts:password_reset"), {"identifier": "halima"})
    code = sent[0]

    # A wrong code keeps the user on the code page with the friendly error.
    response = client.post(reverse("accounts:password_reset_code"), {"code": "000000"})
    assert response.status_code == 200
    assert b"not right" in response.content

    # The right code moves on to choosing a new password.
    response = client.post(reverse("accounts:password_reset_code"), {"code": code})
    assert response.status_code == 302
    response = client.post(
        reverse("accounts:password_reset_code"),
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_complete")
    phone_parent.refresh_from_db()
    assert phone_parent.check_password(NEW_PASSWORD)
    assert phone_parent.must_change_password is False

    # The code is single use: entering it again does nothing.
    client2 = Client()
    client2.post(reverse("accounts:password_reset_code"), {"code": code})
    assert "_auth_user_id" not in client2.session

    # And the user can now log in with the phone number in any format.
    response = client.post(
        reverse("accounts:login"), {"username": "0803-555-0101", "password": NEW_PASSWORD}
    )
    assert response.status_code == 302
    assert "_auth_user_id" in client.session


@pytest.mark.django_db
def test_code_page_without_a_started_flow_redirects(client):
    response = client.get(reverse("accounts:password_reset_code"))
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset")


@pytest.mark.django_db
def test_activation_link_sends_code_and_sets_first_password(
    client, monkeypatch, school_a
):
    from apps.schools.models import Membership

    user = User.objects.create_user("newbie", phone="0803 444 0123")  # unusable password
    Membership.objects.create(user=user, school=school_a, role=Membership.Role.PARENT)
    sent = []
    monkeypatch.setattr(
        channel_module, "send_code_sms", lambda u, code: sent.append(code)
    )
    link = reverse(
        "accounts:activate", args=[urlsafe_base64_encode(str(user.pk).encode())]
    )
    response = client.get(link)
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_code")
    assert len(sent) == 1

    client.post(reverse("accounts:password_reset_code"), {"code": sent[0]})
    response = client.post(
        reverse("accounts:password_reset_code"),
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


@pytest.mark.django_db
def test_activation_link_is_dead_once_a_password_exists(client, parent):
    link = reverse(
        "accounts:activate", args=[urlsafe_base64_encode(str(parent.pk).encode())]
    )
    response = client.get(link)
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_garbage_activation_link_redirects_to_login(client):
    response = client.get(reverse("accounts:activate", args=["not-a-number!!"]))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url
