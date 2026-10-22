import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

User = get_user_model()
NEW_PASSWORD = "N3w-Secure-pass!"


@pytest.fixture
def parent():
    return User.objects.create_user(
        "parent1", email="parent1@example.com", password="Old-Secure-pass1"
    )


def test_reset_page_loads(client):
    assert client.get(reverse("accounts:password_reset")).status_code == 200


@pytest.mark.django_db
def test_known_email_receives_one_reset_email(client, parent):
    response = client.post(reverse("accounts:password_reset"), {"email": "parent1@example.com"})
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 1
    assert "/accounts/reset/" in mail.outbox[0].body


@pytest.mark.django_db
def test_unknown_email_gets_same_response_and_no_email(client, parent):
    response = client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_full_reset_flow_changes_password(client, parent):
    client.post(reverse("accounts:password_reset"), {"email": "parent1@example.com"})
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